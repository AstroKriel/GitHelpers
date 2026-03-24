## { SCRIPT

##
## === DEPENDENCIES
##

## stdlib
import subprocess
from pathlib import Path

## third-party
import pytest

## local
from git_helpers import git_branches
from git_helpers.shell_interface import Config
from vtests import helpers as vtest_helpers

##
## === delete-local-branch
##


def test_delete_local_branch_removes_branch(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["checkout", "-b", "to-delete"], cwd=make_repo_)
    vtest_helpers.git(["checkout", "main"], cwd=make_repo_)
    vtest_helpers.git(["merge", "to-delete"], cwd=make_repo_)
    git_branches.cmd_delete_local_branch(Config(), "to-delete")
    assert "to-delete" not in vtest_helpers.local_branches(make_repo_)


def test_delete_local_branch_refuses_current_branch(
    make_repo_: Path,
) -> None:
    with pytest.raises(SystemExit):
        git_branches.cmd_delete_local_branch(Config(), "main")


def test_delete_local_branch_refuses_unmerged_branch(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["checkout", "-b", "unmerged"], cwd=make_repo_)
    vtest_helpers.make_commit(make_repo_, "unmerged commit")
    vtest_helpers.git(["checkout", "main"], cwd=make_repo_)
    ## git refuses -d on unmerged branches — raises CalledProcessError
    with pytest.raises(subprocess.CalledProcessError):
        git_branches.cmd_delete_local_branch(Config(), "unmerged")
    ## branch should still be there
    assert "unmerged" in vtest_helpers.local_branches(make_repo_)


##
## === prune-gone-locals
##


def test_prune_gone_locals_removes_branch_with_deleted_remote(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    ## create a branch, push it with upstream tracking, then delete the remote branch
    vtest_helpers.git(["checkout", "-b", "gone-branch"], cwd=repo_dir)
    vtest_helpers.git(["push", "-u", "origin", "gone-branch"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    vtest_helpers.git(["push", "origin", "--delete", "gone-branch"], cwd=repo_dir)
    ## prune should clean it up
    git_branches.cmd_prune_gone_locals(Config())
    assert "gone-branch" not in vtest_helpers.local_branches(repo_dir)


def test_prune_gone_locals_leaves_active_branches(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "active-branch"], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, "active commit")
    vtest_helpers.git(["push", "-u", "origin", "active-branch"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    git_branches.cmd_prune_gone_locals(Config())
    assert "active-branch" in vtest_helpers.local_branches(repo_dir)


##
## === prune-merged-locals
##


def test_prune_merged_locals_removes_merged_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "merged-feature"], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, "feature commit")
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    vtest_helpers.git(["merge", "merged-feature", "--no-ff", "-m", "merge feature"], cwd=repo_dir)
    vtest_helpers.git(["push"], cwd=repo_dir)
    git_branches.cmd_prune_merged_locals(Config(), "origin/main")
    assert "merged-feature" not in vtest_helpers.local_branches(repo_dir)


def test_prune_merged_locals_never_deletes_main(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    git_branches.cmd_prune_merged_locals(Config(), "origin/main")
    assert "main" in vtest_helpers.local_branches(repo_dir)


def test_prune_merged_locals_never_deletes_current_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "current"], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, "current commit")
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    vtest_helpers.git(["merge", "current", "--no-ff", "-m", "merge current"], cwd=repo_dir)
    vtest_helpers.git(["push"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "current"], cwd=repo_dir)
    git_branches.cmd_prune_merged_locals(Config(), "origin/main")
    assert "current" in vtest_helpers.local_branches(repo_dir)


##
## === track-remote-branch
##


def test_track_remote_branch_creates_and_checks_out_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    git_branches.cmd_track_remote_branch(Config(), "origin/main", "local-main")
    current = vtest_helpers.git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir).stdout.strip()
    assert current == "local-main"
    upstream = vtest_helpers.git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=repo_dir,
    ).stdout.strip()
    assert upstream == "origin/main"


def test_track_remote_branch_defaults_local_name_from_remote(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    ## push a fresh remote branch so there's a distinct ref to track without
    ## conflicting with the existing local 'main'
    vtest_helpers.git(["checkout", "-b", "feature-x"], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, "feature commit")
    vtest_helpers.git(["push", "origin", "feature-x"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    vtest_helpers.git(["branch", "-D", "feature-x"], cwd=repo_dir)
    ## no local_branch arg — should derive "feature-x" from "origin/feature-x"
    git_branches.cmd_track_remote_branch(Config(), "origin/feature-x")
    current = vtest_helpers.git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir).stdout.strip()
    assert current == "feature-x"


##
## === create-branch-from-remote
##


def test_create_branch_from_remote_creates_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    git_branches.cmd_create_branch_from_remote(Config(), "new-feature", "origin/main")
    assert "new-feature" in vtest_helpers.local_branches(repo_dir)


def test_create_branch_from_remote_sets_upstream(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    git_branches.cmd_create_branch_from_remote(Config(), "new-feature", "origin/main")
    upstream = vtest_helpers.git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=repo_dir,
    ).stdout.strip()
    assert upstream == "origin/new-feature"


##
## === create-branch-from-default
##


def test_create_branch_from_default_creates_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["remote", "set-head", "origin", "main"], cwd=repo_dir)
    git_branches.cmd_create_branch_from_default(Config(), "new-feature")
    assert "new-feature" in vtest_helpers.local_branches(repo_dir)


def test_create_branch_from_default_sets_upstream(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["remote", "set-head", "origin", "main"], cwd=repo_dir)
    git_branches.cmd_create_branch_from_default(Config(), "new-feature")
    upstream = vtest_helpers.git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=repo_dir,
    ).stdout.strip()
    assert upstream == "origin/new-feature"


##
## === cleanup-local-branches
##


def test_cleanup_local_branches_runs_both_passes(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    ## set up a gone branch
    vtest_helpers.git(["checkout", "-b", "gone"], cwd=repo_dir)
    vtest_helpers.git(["push", "-u", "origin", "gone"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    vtest_helpers.git(["push", "origin", "--delete", "gone"], cwd=repo_dir)
    ## set up a merged branch
    vtest_helpers.git(["checkout", "-b", "merged"], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, "merged commit")
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    vtest_helpers.git(["merge", "merged", "--no-ff", "-m", "merge merged"], cwd=repo_dir)
    vtest_helpers.git(["push"], cwd=repo_dir)
    git_branches.cmd_cleanup_local_branches(Config(), "origin/main")
    branches = vtest_helpers.local_branches(repo_dir)
    assert "gone" not in branches
    assert "merged" not in branches
    assert "main" in branches


## } SCRIPT
