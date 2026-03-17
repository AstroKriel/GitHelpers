"""
Validation tests for --dry-run: verifies no mutations occur.
"""

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## local
from git_helpers import git_utils
from git_helpers.shell_utils import Config
from vtests import helpers as vtest_helpers

##
## === TESTS
##


def test_dry_run_delete_branch_leaves_branch_intact(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["checkout", "-b", "dry-target"], cwd=make_repo_)
    vtest_helpers.make_commit(make_repo_, "dry commit")
    vtest_helpers.git(["checkout", "main"], cwd=make_repo_)
    vtest_helpers.git(["merge", "dry-target"], cwd=make_repo_)
    git_utils.cmd_delete_local_branch(Config(dry_run=True), "dry-target")
    assert "dry-target" in vtest_helpers.local_branches(make_repo_)


def test_dry_run_rename_last_commit_leaves_message_unchanged(
    make_repo_: Path,
) -> None:
    original_msg = vtest_helpers.current_commit_message(make_repo_)
    git_utils.cmd_rename_last_commit(Config(dry_run=True), ["completely", "different", "message"])
    assert vtest_helpers.current_commit_message(make_repo_) == original_msg


def test_dry_run_rename_last_commit_leaves_sha_unchanged(
    make_repo_: Path,
) -> None:
    before_sha = vtest_helpers.head_sha(make_repo_)
    git_utils.cmd_rename_last_commit(Config(dry_run=True), ["new", "message"])
    assert vtest_helpers.head_sha(make_repo_) == before_sha


def test_dry_run_sync_branch_leaves_head_unchanged(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    ## push a new commit from a second clone
    second_dir = repo_dir.parent / "second"
    second_dir.mkdir()
    vtest_helpers.git(["clone", str(remote_dir), str(second_dir)], cwd=repo_dir.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        vtest_helpers.git(["config", key, val], cwd=second_dir)
    vtest_helpers.make_commit(second_dir, "remote commit")
    vtest_helpers.git(["push"], cwd=second_dir)
    ## dry-run sync should leave HEAD where it is
    before_sha = vtest_helpers.head_sha(repo_dir)
    git_utils.cmd_sync_branch(Config(dry_run=True))
    assert vtest_helpers.head_sha(repo_dir) == before_sha
