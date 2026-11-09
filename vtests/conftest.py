## { SCRIPT

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## third-party
import pytest

## personal
from huginn import _manage_output

## local
from git_helpers import repo_state
from vtests import helpers as vtest_helpers

##
## === FIXTURES
##


@pytest.fixture(autouse=True)
def reset_huginn_state() -> None:
    """Start each test with no log file and every built-in flag off, so no test writes to the real log or inherits a dry run."""
    _manage_output.reset_active_state()


@pytest.fixture(autouse=True)
def reset_repo_state() -> None:
    """Start each test with no cached repo facts, so no test reuses another test's repo."""
    repo_state.reset_state()


@pytest.fixture
def make_repo_(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """A minimal local git repo on main with one commit, no remote."""
    repo_dir = tmp_path / "tmp_repo"
    repo_dir.mkdir()
    vtest_helpers.git(["init", "-b", "main"], cwd=repo_dir)
    for key, val in vtest_helpers.GIT_USER.items():
        vtest_helpers.git(["config", key, val], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, msg="init")
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
    vtest_helpers.git(["init", "--bare", "-b", "main"], cwd=remote_dir)
    ## local repo wired to the bare remote
    repo_dir = tmp_path / "tmp_repo"
    repo_dir.mkdir()
    vtest_helpers.git(["init", "-b", "main"], cwd=repo_dir)
    for key, val in vtest_helpers.GIT_USER.items():
        vtest_helpers.git(["config", key, val], cwd=repo_dir)
    vtest_helpers.git(["remote", "add", "origin", str(remote_dir)], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, msg="init")
    vtest_helpers.git(["push", "-u", "origin", "main"], cwd=repo_dir)
    monkeypatch.chdir(repo_dir)
    return repo_dir, remote_dir


## } SCRIPT
