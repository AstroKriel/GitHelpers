"""
Shared git helpers for validation tests.
"""

##
## === DEPENDENCIES
##

## stdlib
import subprocess
from pathlib import Path

##
## === CONSTANTS
##

GIT_USER = {
    "user.name": "Test Dummy",
    "user.email": "TestDummy@bla.com",
}

##
## === HELPERS
##


def git(
    args: list[str],
    cwd: Path,
) -> subprocess.CompletedProcess:
    """Run a git command in the given directory; raises on non-zero exit."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def make_commit(
    repo_dir: Path,
    msg: str = "test commit",
    filename: str = ".commit_counter",
) -> str:
    """Make a real (non-empty) commit by incrementing a counter file; returns short SHA."""
    counter = repo_dir / filename
    count = int(counter.read_text()) + 1 if counter.exists() else 1
    counter.write_text(str(count))
    git(["add", str(counter)], cwd=repo_dir)
    git(["commit", "-m", msg], cwd=repo_dir)
    return git(["rev-parse", "--short", "HEAD"], cwd=repo_dir).stdout.strip()


def make_commits(
    repo_dir: Path,
    num_commits: int,
    prefix: str = "commit",
) -> list[str]:
    """Make num_commits commits and return their short SHAs."""
    return [make_commit(repo_dir, f"{prefix} {commit_index + 1}") for commit_index in range(num_commits)]


def local_branches(
    repo_dir: Path,
) -> list[str]:
    """Return a list of local branch names."""
    result = git(["branch", "--format=%(refname:short)"], cwd=repo_dir)
    return result.stdout.strip().splitlines()


def current_commit_message(
    repo_dir: Path,
) -> str:
    """Return the subject line of the most recent commit."""
    return git(["log", "-1", "--format=%s"], cwd=repo_dir).stdout.strip()


def head_sha(
    repo_dir: Path,
) -> str:
    """Return the short SHA of HEAD."""
    return git(["rev-parse", "--short", "HEAD"], cwd=repo_dir).stdout.strip()
