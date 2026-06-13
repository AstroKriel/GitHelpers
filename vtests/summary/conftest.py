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


## } V-TEST CONFTEST
