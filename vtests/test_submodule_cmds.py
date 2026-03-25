## { SCRIPT

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## third-party
import pytest

## local
from git_helpers import git_submodules
from git_helpers.shell_interface import Config
from vtests.helpers import GIT_USER, git, make_commit

##
## === FIXTURES
##


@pytest.fixture
def sub_remote(
    tmp_path: Path,
) -> Path:
    """A bare sub-repo remote with one commit on main; suitable as a submodule URL."""
    remote_dir = tmp_path / "sub.git"
    remote_dir.mkdir()
    git(["init", "--bare", "-b", "main"], cwd=remote_dir)
    ## seed it with a commit via a temp working clone so the remote is non-empty
    work_dir = tmp_path / "sub_seed"
    git(["clone", str(remote_dir), str(work_dir)], cwd=tmp_path)
    for key, val in GIT_USER.items():
        git(["config", key, val], cwd=work_dir)
    make_commit(work_dir, "sub init")
    git(["push", "-u", "origin", "main"], cwd=work_dir)
    return remote_dir


@pytest.fixture
def make_repo_with_submodule(
    sub_remote: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path]:
    """Parent repo on main with 'sub' registered as a submodule in detached HEAD.

    origin/HEAD is explicitly set inside the submodule so auto-detection works.
    Returns (parent_dir, sub_dir).
    """
    parent = tmp_path / "parent"
    parent.mkdir()
    git(["init", "-b", "main"], cwd=parent)
    for key, val in GIT_USER.items():
        git(["config", key, val], cwd=parent)
    make_commit(parent, "parent init")
    ## allow local-path submodule clones — git 2.38+ restricts the file protocol by default.
    ## env vars are inherited by all subprocess calls (including git clone inside submodule add).
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")
    git(["submodule", "add", str(sub_remote), "sub"], cwd=parent)
    git(["commit", "-m", "add sub submodule"], cwd=parent)
    ## explicitly set origin/HEAD inside the submodule so symbolic-ref detection works
    git(["remote", "set-head", "origin", "main"], cwd=parent / "sub")
    ## push a new commit to sub_remote so the submodule is behind origin/main after detaching;
    ## this ensures `git pull` inside cmd_fix_submodule actually advances the pointer
    sub_seed2 = tmp_path / "sub_seed2"
    git(["clone", str(sub_remote), str(sub_seed2)], cwd=tmp_path)
    for key, val in GIT_USER.items():
        git(["config", key, val], cwd=sub_seed2)
    make_commit(sub_seed2, "sub update")
    git(["push"], cwd=sub_seed2)
    ## detach HEAD in the submodule at the old commit — simulates a fresh `git submodule update`
    git(["-C", "sub", "checkout", "--detach", "HEAD"], cwd=parent)
    monkeypatch.chdir(parent)
    return parent, parent / "sub"


##
## === _detect_default_branch_from_local
##


def test_detect_from_local_returns_branch_when_origin_head_is_set(
    make_repo_with_submodule: tuple[Path, Path],
) -> None:
    _, sub_dir = make_repo_with_submodule
    result = git_submodules._detect_default_branch_from_local(str(sub_dir))
    assert result == "main"


def test_detect_from_local_returns_none_when_origin_head_not_set(
    make_repo_with_submodule: tuple[Path, Path],
) -> None:
    _, sub_dir = make_repo_with_submodule
    git(["remote", "set-head", "origin", "--delete"], cwd=sub_dir)
    result = git_submodules._detect_default_branch_from_local(str(sub_dir))
    assert result is None


##
## === _detect_default_branch_from_url
##


def test_detect_from_url_returns_branch_for_bare_remote(
    sub_remote: Path,
) -> None:
    result = git_submodules._detect_default_branch_from_url(str(sub_remote))
    assert result == "main"


def test_detect_from_url_returns_none_for_nonexistent_remote(
    tmp_path: Path,
) -> None:
    result = git_submodules._detect_default_branch_from_url(str(tmp_path / "does_not_exist"))
    assert result is None


##
## === cmd_fix_submodule
##


def test_fix_submodule_with_explicit_branch_restores_tracked_branch(
    make_repo_with_submodule: tuple[Path, Path],
) -> None:
    _, sub_dir = make_repo_with_submodule
    git_submodules.cmd_fix_submodule(Config(), "sub", "main")
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=sub_dir).stdout.strip()
    assert branch == "main"


def test_fix_submodule_with_explicit_branch_commits_pointer_in_parent(
    make_repo_with_submodule: tuple[Path, Path],
) -> None:
    parent, _ = make_repo_with_submodule
    git_submodules.cmd_fix_submodule(Config(), "sub", "main")
    msg = git(["log", "-1", "--format=%s"], cwd=parent).stdout.strip()
    assert msg == "fix: update sub pointer after repair"


def test_fix_submodule_auto_detects_branch(
    make_repo_with_submodule: tuple[Path, Path],
) -> None:
    _, sub_dir = make_repo_with_submodule
    git_submodules.cmd_fix_submodule(Config(), "sub", None)
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=sub_dir).stdout.strip()
    assert branch == "main"


def test_fix_submodule_kills_when_branch_not_detectable(
    make_repo_with_submodule: tuple[Path, Path],
) -> None:
    _, sub_dir = make_repo_with_submodule
    git(["remote", "set-head", "origin", "--delete"], cwd=sub_dir)
    with pytest.raises(SystemExit):
        git_submodules.cmd_fix_submodule(Config(), "sub", None)


##
## === cmd_add_submodule
##


def test_add_submodule_with_explicit_branch_creates_directory(
    make_repo_: Path,
    sub_remote: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")
    git_submodules.cmd_add_submodule(Config(), str(sub_remote), "sub", "main")
    assert (make_repo_ / "sub").is_dir()


def test_add_submodule_with_explicit_branch_writes_gitmodules(
    make_repo_: Path,
    sub_remote: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")
    git_submodules.cmd_add_submodule(Config(), str(sub_remote), "sub", "main")
    gitmodules = (make_repo_ / ".gitmodules").read_text()
    assert "branch = main" in gitmodules


def test_add_submodule_with_explicit_branch_creates_commit(
    make_repo_: Path,
    sub_remote: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")
    git_submodules.cmd_add_submodule(Config(), str(sub_remote), "sub", "main")
    msg = git(["log", "-1", "--format=%s"], cwd=make_repo_).stdout.strip()
    assert msg == "add sub submodule"


def test_add_submodule_auto_detects_branch_from_remote(
    make_repo_: Path,
    sub_remote: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")
    git_submodules.cmd_add_submodule(Config(), str(sub_remote), "sub", None)
    gitmodules = (make_repo_ / ".gitmodules").read_text()
    assert "branch = main" in gitmodules


def test_add_submodule_kills_before_cloning_when_branch_not_detectable(
    make_repo_: Path,
    tmp_path: Path,
) -> None:
    with pytest.raises(SystemExit):
        git_submodules.cmd_add_submodule(Config(), str(tmp_path / "does_not_exist"), "sub", None)
    ## submodule directory must not have been created — kill happened before any git mutations
    assert not (make_repo_ / "sub").exists()


## } SCRIPT
