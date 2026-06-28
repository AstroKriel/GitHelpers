## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import configparser
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

## local
from git_helpers import shell_interface

##
## === DATA
##


@dataclass(frozen=True)
class _BranchStatus:
    name: str
    upstream_remote: str = ""
    commits_ahead: int = 0
    commits_behind: int = 0


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
    results: list[Path] = []
    _walk(path=root, max_depth=max_depth, depth=0, results=results)
    return sorted(results)


def _should_scan_submodules(repo_path: Path) -> bool:
    result = subprocess.run(
        ["git", "config", "--local", "git-helpers.scan-submodules"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "true"


def _active_submodule_paths(repo_path: Path) -> list[Path]:
    gitmodules = repo_path / ".gitmodules"
    if not gitmodules.exists():
        return []
    config = configparser.ConfigParser()
    config.read(gitmodules)
    paths = []
    for section in config.sections():
        if config.get(section, "ignore", fallback="") == "all":
            continue
        rel_path = config.get(section, "path", fallback=None)
        if rel_path:
            paths.append(repo_path / rel_path)
    return paths


def _walk(
    *,
    path: Path,
    max_depth: int,
    depth: int,
    results: list[Path],
) -> None:
    if (path / ".git").exists():
        results.append(path)
        if _should_scan_submodules(path):
            for sub_path in _active_submodule_paths(path):
                if sub_path.is_dir():
                    _walk(path=sub_path, max_depth=max_depth, depth=depth, results=results)
        return
    if depth >= max_depth:
        return
    try:
        for child in sorted(path.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                _walk(path=child, max_depth=max_depth, depth=depth + 1, results=results)
    except PermissionError:
        pass


##
## === REPO STATUS
##


def _query(
    cmd: list[str],
    cwd: Path,
) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip()


def _fetch(
    path: Path,
) -> None:
    subprocess.run(
        ["git", "fetch", "--quiet"],
        cwd=path,
        capture_output=True,
    )


def _get_repo_status(
    *,
    path: Path,
    is_fetching: bool = True,
    since: int | None = None,
) -> _RepoStatus:
    if is_fetching:
        _fetch(path)

    dirty_output = _query(["git", "status", "--porcelain"], path)
    dirty_files = len([line for line in dirty_output.splitlines() if line.strip()])

    ref_output = _query(
        ["git", "for-each-ref", "--format=%(refname:short) %(upstream:track) %(upstream:remotename)", "refs/heads/"],
        path,
    )
    diverged: list[_BranchStatus] = []
    for line in ref_output.splitlines():
        ## split on whitespace; for-each-ref uses this format:
        ##   "branchname [ahead N] remotename"   (branch with upstream)
        ##   "branchname"                         (branch without upstream)
        ## %(upstream:remotename) is always a single token (e.g. "origin") with no spaces.
        ## %(upstream:track) may contain spaces (e.g. "[ahead 1, behind 2]").
        tokens = line.split()
        if not tokens:
            continue
        branch_name = tokens[0]
        remote_name = tokens[-1] if len(tokens) > 1 else ""
        track = " ".join(tokens[1:-1]) if len(tokens) > 2 else (tokens[1] if len(tokens) == 2 else "")
        ahead_match = re.search(r"ahead (\d+)", track)
        behind_match = re.search(r"behind (\d+)", track)
        commits_ahead = int(ahead_match.group(1)) if ahead_match else 0
        commits_behind = int(behind_match.group(1)) if behind_match else 0
        if commits_ahead or commits_behind:
            diverged.append(_BranchStatus(
                name=branch_name,
                upstream_remote=remote_name,
                commits_ahead=commits_ahead,
                commits_behind=commits_behind,
            ))

    log_output = _query(["git", "log", "-1", "--format=%cr\n%ct"], path)
    lines = log_output.splitlines()
    if len(lines) >= 2:
        last_commit_rel = lines[0]
        last_commit_age_days = (time.time() - float(lines[1])) / 86400
    else:
        last_commit_rel = "(no commits)"
        last_commit_age_days = float("inf")

    commits_in_window = 0
    if since is not None:
        count_output = _query(["git", "log", "--oneline", f"--after={since} days ago"], path)
        commits_in_window = len(count_output.splitlines()) if count_output else 0

    return _RepoStatus(
        path=path,
        dirty_files=dirty_files,
        diverged=diverged,
        last_commit_rel=last_commit_rel,
        last_commit_age_days=last_commit_age_days,
        commits_in_window=commits_in_window,
    )


##
## === DISPLAY
##


def _print_repo_status(
    *,
    status: _RepoStatus,
) -> None:
    shell_interface.log_step(str(status.path))
    shell_interface.bind_var(var_name="last commit", var_value=status.last_commit_rel)
    if status.commits_in_window:
        shell_interface.bind_var(var_name="commits", var_value=str(status.commits_in_window))
    if status.dirty_files:
        shell_interface.bind_var(var_name="dirty", var_value=f"{status.dirty_files} file(s)")
    for branch in status.diverged:
        if branch.commits_ahead:
            shell_interface.bind_var(
                var_name="unpushed",
                var_value=f"{branch.name} ({branch.commits_ahead} commit(s) ahead)",
            )
        if branch.commits_behind:
            shell_interface.bind_var(
                var_name="unpulled",
                var_value=f"{branch.name} ({branch.commits_behind} commit(s) behind)",
            )


##
## === ACTIONS
##


def _get_current_branch(
    path: Path,
) -> str:
    name = _query(["git", "rev-parse", "--abbrev-ref", "HEAD"], path)
    return "" if name == "HEAD" else name


def _do_pull(
    *,
    config: shell_interface.Config,
    path: Path,
    status: _RepoStatus,
    current_branch: str,
) -> bool:
    if not current_branch:
        return False
    for branch in status.diverged:
        if branch.name != current_branch:
            continue
        if branch.commits_behind == 0 or branch.commits_ahead > 0:
            return False
        if status.dirty_files > 0:
            shell_interface.bind_var(
                var_name="pull skipped",
                var_value=f"{branch.name} (dirty worktree)",
            )
            return False
        success = shell_interface.try_run_cmd(
            config=config,
            cmd=["git", "pull", "--ff-only"],
            cwd=path,
        )
        if not success:
            shell_interface.bind_var(
                var_name="pull failed",
                var_value=f"{branch.name} (cannot fast-forward; manual intervention needed)",
            )
        return success
    return False


def _do_push(
    *,
    config: shell_interface.Config,
    path: Path,
    status: _RepoStatus,
) -> int:
    pushed = 0
    for branch in status.diverged:
        if branch.commits_ahead > 0 and branch.commits_behind == 0 and branch.upstream_remote:
            success = shell_interface.try_run_cmd(
                config=config,
                cmd=["git", "push", branch.upstream_remote, branch.name],
                cwd=path,
            )
            if success:
                pushed += 1
            else:
                shell_interface.bind_var(
                    var_name="push failed",
                    var_value=branch.name,
                )
    return pushed


##
## === COMMAND
##


def scan_repos(
    config: shell_interface.Config,
    depth: int,
    since: int | None = None,
    is_fetch_skipped: bool = False,
    is_pulling: bool = False,
    is_pushing: bool = False,
) -> None:
    """Scan for git repos from CWD and report dirty, unpushed, and recently active ones; count commits per repo when --since is given."""
    if is_fetch_skipped and (is_pulling or is_pushing):
        shell_interface.kill("--pull and --push require a fetch; remove --no-fetch")
    root = Path.cwd()
    shell_interface.log_step(f"scanning from {root} (depth {depth})")
    repos = _find_repos(root=root, max_depth=depth)
    shell_interface.bind_var(var_name="repos_found", var_value=str(len(repos)))
    if not repos:
        shell_interface.log_outcome("no git repos found")
        return
    if since is not None:
        shell_interface.bind_var(var_name="since_days", var_value=str(since))
    is_fetching = not is_fetch_skipped
    dirty_count = 0
    unpushed_count = 0
    unpulled_count = 0
    anything_shown = False
    for repo in repos:
        status = _get_repo_status(path=repo, is_fetching=is_fetching, since=since)
        if status.dirty_files:
            dirty_count += 1
        if any(b.commits_ahead for b in status.diverged):
            unpushed_count += 1
        if any(b.commits_behind for b in status.diverged):
            unpulled_count += 1
        should_show = (
            status.last_commit_age_days <= since
            if since is not None
            else bool(status.dirty_files or status.diverged)
        )
        if should_show:
            _print_repo_status(status=status)
            anything_shown = True
            if is_pulling:
                current_branch = _get_current_branch(repo)
                _do_pull(config=config, path=repo, status=status, current_branch=current_branch)
            if is_pushing:
                _do_push(config=config, path=repo, status=status)
    if not anything_shown:
        shell_interface.log_outcome("all repos are clean and synced")
        return
    summary_parts = [f"{len(repos)} repos scanned", f"{dirty_count} dirty repos"]
    if unpushed_count:
        summary_parts.append(f"{unpushed_count} with unpushed commits")
    if unpulled_count:
        summary_parts.append(f"{unpulled_count} with unpulled commits")
    shell_interface.log_outcome("; ".join(summary_parts))


## } MODULE
