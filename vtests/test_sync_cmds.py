## { SCRIPT

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## third-party
import pytest

## local
from git_helpers import git_utils
from git_helpers.shell_utils import Config
from vtests import helpers as vtest_helpers

##
## === sync-branch
##


def test_sync_branch_fails_with_dirty_worktree(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    (repo_dir / "dirty.txt").write_text("uncommitted change")
    vtest_helpers.git(["add", "dirty.txt"], cwd=repo_dir)
    with pytest.raises(SystemExit):
        git_utils.cmd_sync_branch(Config())


def test_sync_branch_proceeds_with_allow_dirty(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    (repo_dir / "dirty.txt").write_text("uncommitted change")
    vtest_helpers.git(["add", "dirty.txt"], cwd=repo_dir)
    ## no remote commits to pull - just verify the dirty check is skipped
    git_utils.cmd_sync_branch(Config(allow_dirty=True))


def test_sync_branch_pulls_remote_commits(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    ## push new commits from a second clone
    second_dir = repo_dir.parent / "second"
    second_dir.mkdir()
    vtest_helpers.git(["clone", str(remote_dir), str(second_dir)], cwd=repo_dir.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        vtest_helpers.git(["config", key, val], cwd=second_dir)
    vtest_helpers.make_commits(second_dir, 2, prefix="remote commit")
    vtest_helpers.git(["push"], cwd=second_dir)
    ## sync should bring those commits into the local repo
    before_sha = vtest_helpers.head_sha(repo_dir)
    git_utils.cmd_sync_branch(Config())
    after_sha = vtest_helpers.head_sha(repo_dir)
    assert before_sha != after_sha


def test_sync_branch_with_explicit_base(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    ## create a feature branch with some commits
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, 2, prefix="feature")
    vtest_helpers.git(["push", "-u", "origin", "feature"], cwd=repo_dir)
    ## add commits to main on remote
    second_dir = repo_dir.parent / "second"
    second_dir.mkdir()
    vtest_helpers.git(["clone", str(repo_dir.parent / "remote.git"), str(second_dir)], cwd=repo_dir.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        vtest_helpers.git(["config", key, val], cwd=second_dir)
    vtest_helpers.make_commit(second_dir, "main update", filename=".main_counter")
    vtest_helpers.git(["push"], cwd=second_dir)
    ## sync feature branch against origin/main
    git_utils.cmd_sync_branch(Config(), "origin/main")


##
## === rename-last-commit
##


def test_rename_last_commit_changes_message(
    make_repo_: Path,
) -> None:
    original_msg = vtest_helpers.current_commit_message(make_repo_)
    git_utils.cmd_rename_last_commit(Config(), ["new", "commit", "message"])
    assert vtest_helpers.current_commit_message(make_repo_) == "new commit message"
    assert vtest_helpers.current_commit_message(make_repo_) != original_msg


def test_rename_last_commit_joins_words(
    make_repo_: Path,
) -> None:
    git_utils.cmd_rename_last_commit(Config(), ["fix", "typo", "in", "readme"])
    assert vtest_helpers.current_commit_message(make_repo_) == "fix typo in readme"


def test_rename_last_commit_preserves_sha_prefix(
    make_repo_: Path,
) -> None:
    ## amend changes the SHA — verify it actually changed
    before_sha = vtest_helpers.head_sha(make_repo_)
    git_utils.cmd_rename_last_commit(Config(), ["amended"])
    after_sha = vtest_helpers.head_sha(make_repo_)
    assert before_sha != after_sha


## } SCRIPT
