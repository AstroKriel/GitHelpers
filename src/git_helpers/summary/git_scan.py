## { MODULE

##
## === DEPENDENCIES
##

## stdlib
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


def _walk(
    *,
    path: Path,
    max_depth: int,
    depth: int,
    results: list[Path],
) -> None:
    if (path / ".git").is_dir():
        results.append(path)
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
        ["git", "for-each-ref", "--format=%(refname:short) %(upstream:track)", "refs/heads/"],
        path,
    )
    diverged: list[_BranchStatus] = []
    for line in ref_output.splitlines():
        parts = line.split(" ", 1)
        branch_name = parts[0]
        track = parts[1] if len(parts) > 1 else ""
        ahead_match = re.search(r"ahead (\d+)", track)
        behind_match = re.search(r"behind (\d+)", track)
        commits_ahead = int(ahead_match.group(1)) if ahead_match else 0
        commits_behind = int(behind_match.group(1)) if behind_match else 0
        if commits_ahead or commits_behind:
            diverged.append(_BranchStatus(
                name=branch_name,
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
    root: Path,
) -> None:
    try:
        label = str(status.path.relative_to(root))
    except ValueError:
        label = str(status.path)
    shell_interface.log_step(label)
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
## === COMMAND
##


def scan_repos(
    config: shell_interface.Config,
    depth: int,
    since: int | None = None,
    is_fetch_skipped: bool = False,
) -> None:
    """Scan for git repos from CWD and report dirty, unpushed, and recently active ones; count commits per repo when --since is given."""
    root = Path.cwd()
    shell_interface.log_step(f"scanning from {root} (depth {depth})")
    repos = _find_repos(root=root, max_depth=depth)
    shell_interface.bind_var(var_name="repos_found", var_value=str(len(repos)))
    if not repos:
        shell_interface.log_outcome("no git repos found")
        return
    is_fetching = not is_fetch_skipped
    statuses = [_get_repo_status(path=repo, is_fetching=is_fetching, since=since) for repo in repos]
    if since is not None:
        statuses = [status for status in statuses if status.last_commit_age_days <= since]
        shell_interface.bind_var(var_name="since_days", var_value=str(since))
    to_show = statuses if since is not None else [status for status in statuses if status.dirty_files or status.diverged]
    if not to_show:
        shell_interface.log_outcome("all repos are clean and synced")
        return
    for status in to_show:
        _print_repo_status(status=status, root=root)
    dirty_count = sum(1 for status in statuses if status.dirty_files)
    unpushed_count = sum(1 for status in statuses if any(branch.commits_ahead for branch in status.diverged))
    unpulled_count = sum(1 for status in statuses if any(branch.commits_behind for branch in status.diverged))
    summary_parts = [f"{len(repos)} repos scanned", f"{dirty_count} dirty"]
    if unpushed_count:
        summary_parts.append(f"{unpushed_count} with unpushed commits")
    if unpulled_count:
        summary_parts.append(f"{unpulled_count} with unpulled commits")
    shell_interface.log_outcome("; ".join(summary_parts))


## } MODULE
