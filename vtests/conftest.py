"""
Shared fixtures for validation tests.
"""

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## third-party
import pytest

## local
from vtests.helpers import GIT_USER, git, make_commit

##
## === FIXTURES
##


@pytest.fixture
def make_repo_(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """A minimal local git repo on main with one commit, no remote."""
    repo_dir = tmp_path / "tmp_repo"
    repo_dir.mkdir()
    git(["init", "-b", "main"], cwd=repo_dir)
    for key, val in GIT_USER.items():
        git(["config", key, val], cwd=repo_dir)
    make_commit(repo_dir, "init")
    monkeypatch.chdir(repo_dir)
    return repo_dir


@pytest.fixture
def make_repo_with_remote(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path]:
    """A local repo with a bare remote (origin), one commit pushed to main."""
    ## bare remote — simulates a shared server-side repo
    remote_dir = tmp_path / "remote.git"
    remote_dir.mkdir()
    git(["init", "--bare", "-b", "main"], cwd=remote_dir)
    ## local repo wired to the bare remote
    repo_dir = tmp_path / "tmp_repo"
    repo_dir.mkdir()
    git(["init", "-b", "main"], cwd=repo_dir)
    for key, val in GIT_USER.items():
        git(["config", key, val], cwd=repo_dir)
    git(["remote", "add", "origin", str(remote_dir)], cwd=repo_dir)
    make_commit(repo_dir, "init")
    git(["push", "-u", "origin", "main"], cwd=repo_dir)
    monkeypatch.chdir(repo_dir)
    return repo_dir, remote_dir
