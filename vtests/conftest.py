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
def repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """A minimal local git repo on main with one commit, no remote."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    git(["init", "-b", "main"], cwd=repo_path)
    for key, val in GIT_USER:
        git(["config", key, val], cwd=repo_path)
    make_commit(repo_path, "init")
    monkeypatch.chdir(repo_path)
    return repo_path


@pytest.fixture
def repo_with_remote(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path]:
    """A local repo with a bare remote (origin), one commit pushed to main."""
    ## bare remote — simulates a shared server-side repo
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(["init", "--bare", "-b", "main"], cwd=remote)

    ## local repo wired to the bare remote
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    git(["init", "-b", "main"], cwd=repo_path)
    for key, val in GIT_USER:
        git(["config", key, val], cwd=repo_path)
    git(["remote", "add", "origin", str(remote)], cwd=repo_path)
    make_commit(repo_path, "init")
    git(["push", "-u", "origin", "main"], cwd=repo_path)

    monkeypatch.chdir(repo_path)
    return repo_path, remote
