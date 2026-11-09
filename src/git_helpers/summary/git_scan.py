## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import configparser
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

## personal
from huginn import manage_log, manage_shell

##
## === DATA
##


@dataclass(frozen=True)
class _BranchStatus:
    name: str
    upstream_remote: str = ""
    commits_ahead: int = 0
    commits_behind: int = 0
    upstream_is_gone: bool = False


@dataclass(frozen=True)
class _RepoStatus:
    path: Path
    dirty_files: int
    diverged: list[_BranchStatus] = field(default_factory=list)
    last_commit_rel: str = "(no commits)"
    last_commit_age_days: float = float("inf")
    commits_in_window: int = 0


##
## === DISCOVERY
##


def _find_repos(
    *,
    root: Path,
    max_depth: int,
) -> list[Path]:
    repo_paths: list[Path] = []
    _walk(
        path=root,
        max_depth=max_depth,
        depth=0,
        repo_paths=repo_paths,
    )
    return sorted(repo_paths)


def _should_scan_submodules(
    repo_path: Path,
) -> bool:
    cmd_read_scan_setting = [
        "git",
        "config",
        "--local",
        "git-helpers.scan-submodules",
    ]
    output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_read_scan_setting,
        working_directory=repo_path,
        raise_error=False,
    )
    return output == "true"


def _active_submodule_paths(
    repo_path: Path,
) -> list[Path]:
    gitmodules = repo_path / ".gitmodules"
    if not gitmodules.exists():
        return []
    config = configparser.ConfigParser()
    config.read(gitmodules)
    submodule_paths: list[Path] = []
    for section in config.sections():
        if config.get(section, "ignore", fallback="") == "all":
            continue
        rel_path = config.get(section, "path", fallback=None)
        if rel_path:
            submodule_paths.append(repo_path / rel_path)
    return submodule_paths


def _walk(
    *,
    path: Path,
    max_depth: int,
    depth: int,
    repo_paths: list[Path],
) -> None:
    if (path / ".git").exists():
        repo_paths.append(path)
        if _should_scan_submodules(path):
            for submodule_path in _active_submodule_paths(path):
                if submodule_path.is_dir():
                    _walk(
                        path=submodule_path,
                        max_depth=max_depth,
                        depth=depth,
                        repo_paths=repo_paths,
                    )
        return
    if depth >= max_depth:
        return
    try:
        for child_path in sorted(path.iterdir()):
            if child_path.is_dir() and (not child_path.name.startswith(".")):
                _walk(
                    path=child_path,
                    max_depth=max_depth,
                    depth=depth + 1,
                    repo_paths=repo_paths,
                )
    except PermissionError:
        pass


##
## === REPO STATUS
##


def _read_track_count(
    *,
    track: str,
    label: str,
) -> int:
    """Return N from `<label> N` in an upstream tracking value such as '[ahead 1, behind 2]', or 0 if absent."""
    count_match = re.search(rf"{label} (\d+)", track)
    if count_match is None:
        return 0
    return int(count_match.group(1))


def _get_repo_status(
    *,
    repo_path: Path,
    is_fetching: bool = True,
    since: int | None = None,
) -> _RepoStatus:
    if is_fetching:
        ## a failed fetch (offline, or no remote) still leaves the local state worth reporting.
        ## `--prune` drops tracking refs for deleted remote branches, so their local branches show as gone.
        cmd_fetch = [
            "git",
            "fetch",
            "--prune",
            "--quiet",
        ]
        manage_shell.run_cmd_and_show_output(
            cmd_parts=cmd_fetch,
            working_directory=repo_path,
            raise_error=False,
        )
    cmd_list_changes = [
        "git",
        "status",
        "--porcelain",
    ]
    status_output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_list_changes,
        working_directory=repo_path,
        raise_error=False,
    )
    dirty_files = len(status_output.splitlines())
    ## `%00` separates the fields, since the tracking value itself contains spaces (e.g. '[ahead 1, behind 2]').
    cmd_list_branch_tracking = [
        "git",
        "for-each-ref",
        "--format=%(refname:short)%00%(upstream:track)%00%(upstream:remotename)",
        "refs/heads/",
    ]
    branch_tracking_output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_list_branch_tracking,
        working_directory=repo_path,
        raise_error=False,
    )
    diverged: list[_BranchStatus] = []
    for line in branch_tracking_output.splitlines():
        branch_name, track, remote_name = line.split("\0")
        commits_ahead = _read_track_count(
            track=track,
            label="ahead",
        )
        commits_behind = _read_track_count(
            track=track,
            label="behind",
        )
        ## git marks a branch whose upstream was deleted on the remote with the tracking value '[gone]'.
        upstream_is_gone = track == "[gone]"
        if (commits_ahead > 0) or (commits_behind > 0) or upstream_is_gone:
            branch_status = _BranchStatus(
                name=branch_name,
                upstream_remote=remote_name,
                commits_ahead=commits_ahead,
                commits_behind=commits_behind,
                upstream_is_gone=upstream_is_gone,
            )
            diverged.append(branch_status)
    ## `%cr` is the relative commit date (e.g. '2 days ago'); `%ct` is the same date in seconds.
    cmd_read_last_commit = [
        "git",
        "log",
        "-1",
        "--format=%cr%n%ct",
    ]
    last_commit_output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_read_last_commit,
        working_directory=repo_path,
        raise_error=False,
    )
    last_commit_lines = last_commit_output.splitlines()
    if len(last_commit_lines) >= 2:
        last_commit_rel = last_commit_lines[0]
        last_commit_age_days = (time.time() - float(last_commit_lines[1])) / 86400
    else:
        last_commit_rel = "(no commits)"
        last_commit_age_days = float("inf")
    if since is None:
        commits_in_window = 0
    else:
        cmd_list_window_commits = [
            "git",
            "log",
            "--oneline",
            f"--after={since} days ago",
        ]
        window_commits_output = manage_shell.query_cmd_and_capture_output(
            cmd_parts=cmd_list_window_commits,
            working_directory=repo_path,
            raise_error=False,
        )
        commits_in_window = len(window_commits_output.splitlines())
    return _RepoStatus(
        path=repo_path,
        dirty_files=dirty_files,
        diverged=diverged,
        last_commit_rel=last_commit_rel,
        last_commit_age_days=last_commit_age_days,
        commits_in_window=commits_in_window,
    )


##
## === DISPLAY
##


def _report_repo_status(
    *,
    repo_status: _RepoStatus,
) -> None:
    items: dict[str, str] = {"last commit": repo_status.last_commit_rel}
    if repo_status.commits_in_window:
        items["commits"] = str(repo_status.commits_in_window)
    if repo_status.dirty_files:
        items["dirty"] = f"{repo_status.dirty_files} file(s)"
    unpushed_branches: list[str] = []
    unpulled_branches: list[str] = []
    gone_upstream_branches: list[str] = []
    for branch_status in repo_status.diverged:
        if branch_status.commits_ahead:
            unpushed_branches.append(f"{branch_status.name} ({branch_status.commits_ahead} commit(s) ahead)")
        if branch_status.commits_behind:
            unpulled_branches.append(f"{branch_status.name} ({branch_status.commits_behind} commit(s) behind)")
        if branch_status.upstream_is_gone:
            gone_upstream_branches.append(branch_status.name)
    if unpushed_branches:
        items["unpushed"] = ", ".join(unpushed_branches)
    if unpulled_branches:
        items["unpulled"] = ", ".join(unpulled_branches)
    if gone_upstream_branches:
        items["gone upstream"] = ", ".join(gone_upstream_branches)
    if repo_status.dirty_files or repo_status.diverged:
        manage_log.log_outcome(
            "needs attention",
            status=manage_log.OutcomeStatus.WARNING,
            items=items,
        )
    else:
        manage_log.log_outcome(
            "recently active; clean and synced",
            status=manage_log.OutcomeStatus.SUCCESS,
            items=items,
        )


##
## === ACTIONS
##


def _find_current_branch_name(
    repo_path: Path,
) -> str | None:
    """Return the branch checked out in a repo, or None if its HEAD is detached."""
    cmd_get_head_ref = [
        "git",
        "symbolic-ref",
        "-q",
        "--short",
        "HEAD",
    ]
    output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_get_head_ref,
        working_directory=repo_path,
        raise_error=False,
    )
    if not output:
        return None
    return output


def _pull_current_branch(
    *,
    repo_path: Path,
    repo_status: _RepoStatus,
) -> bool:
    """Fast-forward the checked-out branch if it is only behind its upstream; return True if it was pulled."""
    current_branch_name = _find_current_branch_name(repo_path)
    for branch_status in repo_status.diverged:
        if branch_status.name != current_branch_name:
            continue
        if (branch_status.commits_behind == 0) or (branch_status.commits_ahead > 0):
            return False
        if repo_status.dirty_files > 0:
            manage_log.log_outcome(
                "did not pull: dirty worktree",
                status=manage_log.OutcomeStatus.SKIPPED,
                items={"branch": branch_status.name},
            )
            return False
        cmd_pull_ff_only = [
            "git",
            "pull",
            "--ff-only",
        ]
        branch_was_pulled = manage_shell.run_cmd_and_show_output(
            cmd_parts=cmd_pull_ff_only,
            working_directory=repo_path,
            raise_error=False,
        )
        if not branch_was_pulled:
            manage_log.log_outcome(
                "cannot fast-forward pull; manual intervention needed",
                status=manage_log.OutcomeStatus.FAILURE,
                items={"branch": branch_status.name},
            )
        return branch_was_pulled
    return False


def _push_ahead_branches(
    *,
    repo_path: Path,
    repo_status: _RepoStatus,
) -> int:
    """Push every branch that is only ahead of its upstream; return how many were pushed."""
    pushed_branch_count = 0
    for branch_status in repo_status.diverged:
        branch_is_only_ahead = (branch_status.commits_ahead > 0) and (branch_status.commits_behind == 0)
        if branch_is_only_ahead and branch_status.upstream_remote:
            cmd_push_branch = [
                "git",
                "push",
                branch_status.upstream_remote,
                branch_status.name,
            ]
            branch_was_pushed = manage_shell.run_cmd_and_show_output(
                cmd_parts=cmd_push_branch,
                working_directory=repo_path,
                raise_error=False,
            )
            if branch_was_pushed:
                pushed_branch_count += 1
            else:
                manage_log.log_outcome(
                    "could not push branch",
                    status=manage_log.OutcomeStatus.FAILURE,
                    items={"branch": branch_status.name},
                )
    return pushed_branch_count


##
## === COMMAND
##


def scan_repos(
    *,
    depth: int,
    since: int | None = None,
    no_fetch: bool = False,
    pull: bool = False,
    push: bool = False,
) -> None:
    """Scan for git repos from CWD and report dirty, unpushed, and recently active ones; count commits per repo when --since is given."""
    if no_fetch and (pull or push):
        manage_log.exit_with_error("--pull and --push require a fetch; remove --no-fetch")
    root = Path.cwd()
    manage_log.log_task(f"scanning from {root} (depth {depth})")
    repos = _find_repos(
        root=root,
        max_depth=depth,
    )
    if not repos:
        manage_log.log_outcome(
            "no git repos found",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
        return
    scan_items: dict[str, str] = {"repos": str(len(repos))}
    if since is not None:
        scan_items["since"] = f"{since} days"
    manage_log.log_note(
        "found git repos",
        items=scan_items,
    )
    is_fetching = not no_fetch
    dirty_count = 0
    unpushed_count = 0
    unpulled_count = 0
    gone_upstream_count = 0
    pulled_repo_count = 0
    pushed_branch_count = 0
    anything_shown = False
    for repo_path in repos:
        manage_log.log_task(f"checking {repo_path}")
        repo_status = _get_repo_status(
            repo_path=repo_path,
            is_fetching=is_fetching,
            since=since,
        )
        if repo_status.dirty_files:
            dirty_count += 1
        if any(_branch_status.commits_ahead for _branch_status in repo_status.diverged):
            unpushed_count += 1
        if any(_branch_status.commits_behind for _branch_status in repo_status.diverged):
            unpulled_count += 1
        if any(_branch_status.upstream_is_gone for _branch_status in repo_status.diverged):
            gone_upstream_count += 1
        ## with --since, show the recently active repos; otherwise show the ones that need attention.
        if since is None:
            repo_is_shown = bool(repo_status.dirty_files or repo_status.diverged)
        else:
            repo_is_shown = repo_status.last_commit_age_days <= since
        if not repo_is_shown:
            manage_log.log_outcome(
                "nothing to report",
                status=manage_log.OutcomeStatus.SUCCESS,
            )
        else:
            _report_repo_status(repo_status=repo_status)
            anything_shown = True
            if pull:
                repo_was_pulled = _pull_current_branch(
                    repo_path=repo_path,
                    repo_status=repo_status,
                )
                if repo_was_pulled:
                    pulled_repo_count += 1
            if push:
                pushed_branch_count += _push_ahead_branches(
                    repo_path=repo_path,
                    repo_status=repo_status,
                )
    if not anything_shown:
        manage_log.log_outcome(
            "all repos are clean and synced",
            status=manage_log.OutcomeStatus.SUCCESS,
        )
        return
    summary_parts = [f"{len(repos)} repos scanned", f"{dirty_count} dirty repos"]
    if unpushed_count:
        summary_parts.append(f"{unpushed_count} with unpushed commits")
    if unpulled_count:
        summary_parts.append(f"{unpulled_count} with unpulled commits")
    if gone_upstream_count:
        summary_parts.append(f"{gone_upstream_count} with gone upstreams")
    if pull:
        summary_parts.append(f"{pulled_repo_count} repos pulled")
    if push:
        summary_parts.append(f"{pushed_branch_count} branches pushed")
    if (dirty_count > 0) or (unpushed_count > 0) or (unpulled_count > 0) or (gone_upstream_count > 0):
        summary_status = manage_log.OutcomeStatus.WARNING
    else:
        summary_status = manage_log.OutcomeStatus.SUCCESS
    manage_log.log_outcome(
        "; ".join(summary_parts),
        status=summary_status,
    )


## } MODULE
