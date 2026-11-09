## { SCRIPT

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## personal
from huginn import manage_cli

## local
from git_helpers import user_interface
from vtests import helpers as vtest_helpers

##
## === HELPERS
##


def _run_dry(
    cmd_argv: list[str],
) -> None:
    argv = ["--dry-run", *cmd_argv]
    manage_cli.run_cli(
        command_line_tool=user_interface.COMMAND_LINE_TOOL,
        argv=argv,
    )


##
## === TESTS
##


def test_dry_run_delete_branch_leaves_branch_intact(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["checkout", "-b", "dry-target"], cwd=make_repo_)
    vtest_helpers.make_commit(make_repo_, msg="dry commit")
    vtest_helpers.git(["checkout", "main"], cwd=make_repo_)
    vtest_helpers.git(["merge", "dry-target"], cwd=make_repo_)
    _run_dry(["delete-local-branch", "dry-target"])
    assert "dry-target" in vtest_helpers.local_branches(make_repo_)


def test_dry_run_rename_last_commit_leaves_msg_unchanged(
    make_repo_: Path,
) -> None:
    original_msg = vtest_helpers.current_commit_msg(make_repo_)
    _run_dry(["rename-last-commit", "completely", "different", "message"])
    assert vtest_helpers.current_commit_msg(make_repo_) == original_msg


def test_dry_run_rename_last_commit_leaves_hash_unchanged(
    make_repo_: Path,
) -> None:
    commit_hash_before = vtest_helpers.head_commit_hash(make_repo_)
    _run_dry(["rename-last-commit", "new", "message"])
    assert vtest_helpers.head_commit_hash(make_repo_) == commit_hash_before


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
    vtest_helpers.make_commit(second_dir, msg="remote commit")
    vtest_helpers.git(["push"], cwd=second_dir)
    ## dry-run sync should leave HEAD where it is
    commit_hash_before = vtest_helpers.head_commit_hash(repo_dir)
    _run_dry(["sync-branch"])
    assert vtest_helpers.head_commit_hash(repo_dir) == commit_hash_before


##
## === push
##


def test_dry_run_push_does_not_push(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    remote_commit_hash_before = vtest_helpers.git(["rev-parse", "HEAD"], cwd=remote_dir).stdout.strip()
    vtest_helpers.make_commit(repo_dir, msg="local only")
    _run_dry(["push"])
    remote_commit_hash_after = vtest_helpers.git(["rev-parse", "HEAD"], cwd=remote_dir).stdout.strip()
    assert remote_commit_hash_before == remote_commit_hash_after


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
    _run_dry(["create-branch-from-remote", "new-feature", "origin/main"])
    assert vtest_helpers.local_branches(repo_dir) == before


def test_dry_run_track_remote_branch_creates_no_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    _run_dry(["track-remote-branch", "origin/main", "tracked-main"])
    assert "tracked-main" not in vtest_helpers.local_branches(repo_dir)


def test_dry_run_create_branch_from_default_creates_no_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    ## set-head tells git which branch is the remote default (normally set by clone)
    vtest_helpers.git(["remote", "set-head", "origin", "main"], cwd=repo_dir)
    _run_dry(["create-branch-from-default", "new-feature"])
    assert "new-feature" not in vtest_helpers.local_branches(repo_dir)


##
## === create-worktree
##


def test_dry_run_create_worktree_with_base_creates_no_worktree(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    _run_dry(["create-worktree", "feature", "--base", "origin/main"])
    worktree_path = repo_dir.parent / f"{repo_dir.name}-worktrees" / "feature"
    assert not worktree_path.exists()
    assert "feature" not in vtest_helpers.local_branches(repo_dir)


## } SCRIPT
