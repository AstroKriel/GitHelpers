## { SCRIPT

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


##
## === create-branch-from-remote / track-remote-branch / create-branch-from-default
##
## These commands read remote state then create branches.  In dry-run mode the
## read-only queries still execute (so the command validates that the remote ref
## exists and resolves the names correctly), but no branch is created.  Run these
## with --dry-run manually to confirm the bound values look right before committing.
##


def test_dry_run_create_branch_from_remote_creates_no_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    before = vtest_helpers.local_branches(repo_dir)
    git_utils.cmd_create_branch_from_remote(Config(dry_run=True), "new-feature", "origin/main")
    assert vtest_helpers.local_branches(repo_dir) == before


def test_dry_run_track_remote_branch_creates_no_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    git_utils.cmd_track_remote_branch(Config(dry_run=True), "origin/main", "tracked-main")
    assert "tracked-main" not in vtest_helpers.local_branches(repo_dir)


def test_dry_run_create_branch_from_default_creates_no_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    ## set-head tells git which branch is the remote default (normally set by clone)
    vtest_helpers.git(["remote", "set-head", "origin", "main"], cwd=repo_dir)
    git_utils.cmd_create_branch_from_default(Config(dry_run=True), "new-feature")
    assert "new-feature" not in vtest_helpers.local_branches(repo_dir)


## } SCRIPT
