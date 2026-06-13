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


@dataclass
class _BranchStatus:
    name: str
    commits_ahead: int


@dataclass
class _RepoStatus:
    path: Path
    dirty_files: int
    unpushed: list[_BranchStatus] = field(default_factory=list)
    last_commit_rel: str = "(no commits)"
    last_commit_age_days: float = float("inf")


##
## === DISCOVERY
##


def _find_repos(
    root: Path,
    max_depth: int,
) -> list[Path]:
    results: list[Path] = []
    _walk(root, max_depth, 0, results)
    return sorted(results)


def _walk(
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
                _walk(child, max_depth, depth + 1, results)
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


def _get_repo_status(
    path: Path,
) -> _RepoStatus:
    dirty_output = _query(["git", "status", "--porcelain"], path)
    dirty_files = len([ln for ln in dirty_output.splitlines() if ln.strip()])

    ref_output = _query(
        ["git", "for-each-ref", "--format=%(refname:short) %(upstream:track)", "refs/heads/"],
        path,
    )
    unpushed: list[_BranchStatus] = []
    for line in ref_output.splitlines():
        parts = line.split(" ", 1)
        branch = parts[0]
        track = parts[1] if len(parts) > 1 else ""
        match = re.search(r"ahead (\d+)", track)
        if match:
            unpushed.append(_BranchStatus(name=branch, commits_ahead=int(match.group(1))))

    log_output = _query(["git", "log", "-1", "--format=%cr\n%ct"], path)
    lines = log_output.splitlines()
    if len(lines) >= 2:
        last_commit_rel = lines[0]
        last_commit_age_days = (time.time() - float(lines[1])) / 86400
    else:
        last_commit_rel = "(no commits)"
        last_commit_age_days = float("inf")

    return _RepoStatus(
        path=path,
        dirty_files=dirty_files,
        unpushed=unpushed,
        last_commit_rel=last_commit_rel,
        last_commit_age_days=last_commit_age_days,
    )


##
## === DISPLAY
##


def _print_repo_status(
    status: _RepoStatus,
    root: Path,
) -> None:
    try:
        label = str(status.path.relative_to(root))
    except ValueError:
        label = str(status.path)
    shell_interface.log_step(label)
    shell_interface.bind_var(var_name="last commit", var_value=status.last_commit_rel)
    if status.dirty_files:
        shell_interface.bind_var(var_name="dirty", var_value=f"{status.dirty_files} file(s)")
    for branch in status.unpushed:
        shell_interface.bind_var(
            var_name="unpushed",
            var_value=f"{branch.name} ({branch.commits_ahead} commit(s) ahead)",
        )


##
## === COMMAND
##


def scan_repos(
    config: shell_interface.Config,
    depth: int,
    since: int | None = None,
) -> None:
    """Scan for git repos from CWD and report dirty, unpushed, and recently active ones."""
    root = Path.cwd()
    shell_interface.log_step(f"scanning from {root} (depth {depth})")
    repos = _find_repos(root, depth)
    shell_interface.bind_var(var_name="repos_found", var_value=str(len(repos)))
    if not repos:
        shell_interface.log_outcome("no git repos found")
        return
    statuses = [_get_repo_status(r) for r in repos]
    if since is not None:
        statuses = [s for s in statuses if s.last_commit_age_days <= since]
        shell_interface.bind_var(var_name="since_days", var_value=str(since))
    to_show = statuses if since is not None else [s for s in statuses if s.dirty_files or s.unpushed]
    if not to_show:
        shell_interface.log_outcome("all repos are clean and pushed")
        return
    for status in to_show:
        _print_repo_status(status, root)
    dirty_count = sum(1 for s in statuses if s.dirty_files)
    unpushed_count = sum(1 for s in statuses if s.unpushed)
    shell_interface.log_outcome(
        f"{len(repos)} repos scanned; {dirty_count} dirty; {unpushed_count} with unpushed commits",
    )


## } MODULE
