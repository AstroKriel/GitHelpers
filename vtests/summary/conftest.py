## { V-TEST CONFTEST

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
def scan_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A temp directory with no .git; cwd is set here so scan-repos starts from a clean root."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def make_repo_at(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(["init", "-b", "main"], cwd=path)
    for key, val in GIT_USER.items():
        git(["config", key, val], cwd=path)
    make_commit(path, msg="init")
    return path


def make_bare_remote(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(["init", "--bare", "-b", "main"], cwd=path)
    return path


def add_submodule(
    parent_repo: Path,
    sub_source: Path,
    sub_name: str,
) -> Path:
    """Add sub_source as a submodule of parent_repo; returns the submodule worktree path."""
    git(["-c", "protocol.file.allow=always", "submodule", "add", str(sub_source), sub_name], cwd=parent_repo)
    git(["commit", "-m", f"add {sub_name} submodule"], cwd=parent_repo)
    return parent_repo / sub_name


def set_submodule_ignore_all(
    repo: Path,
    sub_name: str,
) -> None:
    """Set ignore = all on a submodule entry in .gitmodules and commit."""
    git(["config", "-f", ".gitmodules", f"submodule.{sub_name}.ignore", "all"], cwd=repo)
    git(["add", ".gitmodules"], cwd=repo)
    git(["commit", "-m", f"set {sub_name} ignore = all"], cwd=repo)


def enable_submodule_scanning(repo: Path) -> None:
    """Opt a repo into submodule scanning via the git-helpers.scan-submodules local config."""
    git(["config", "--local", "git-helpers.scan-submodules", "true"], cwd=repo)


## } V-TEST CONFTEST
