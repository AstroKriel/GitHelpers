"""
Validation tests for branch management commands.
"""

##
## === DEPENDENCIES
##

## stdlib
import subprocess
from pathlib import Path

## third-party
import pytest

## local
from git_helpers import git_cmds
from git_helpers.shell_utils import Config
from vtests.helpers import git, local_branches, make_commit, make_commits


##
## === delete-local-branch
##


def test_delete_local_branch_removes_branch(
    repo: Path,
) -> None:
    git(["checkout", "-b", "to-delete"], cwd=repo)
    git(["checkout", "main"], cwd=repo)
    git(["merge", "to-delete"], cwd=repo)
    git_cmds.cmd_delete_local_branch(Config(), "to-delete")
    assert "to-delete" not in local_branches(repo)


def test_delete_local_branch_refuses_current_branch(
    repo: Path,
) -> None:
    with pytest.raises(SystemExit):
        git_cmds.cmd_delete_local_branch(Config(), "main")


def test_delete_local_branch_refuses_unmerged_branch(
    repo: Path,
) -> None:
    git(["checkout", "-b", "unmerged"], cwd=repo)
    make_commit(repo, "unmerged commit")
    git(["checkout", "main"], cwd=repo)
    ## git refuses -d on unmerged branches — raises CalledProcessError
    with pytest.raises(subprocess.CalledProcessError):
        git_cmds.cmd_delete_local_branch(Config(), "unmerged")
    ## branch should still be there
    assert "unmerged" in local_branches(repo)


##
## === prune-gone-locals
##


def test_prune_gone_locals_removes_branch_with_deleted_remote(
    repo_with_remote: tuple[Path, Path],
) -> None:
    repo, _ = repo_with_remote
    ## create a branch, push it with upstream tracking, then delete the remote branch
    git(["checkout", "-b", "gone-branch"], cwd=repo)
    git(["push", "-u", "origin", "gone-branch"], cwd=repo)
    git(["checkout", "main"], cwd=repo)
    git(["push", "origin", "--delete", "gone-branch"], cwd=repo)
    ## prune should clean it up
    git_cmds.cmd_prune_gone_locals(Config())
    assert "gone-branch" not in local_branches(repo)


def test_prune_gone_locals_leaves_active_branches(
    repo_with_remote: tuple[Path, Path],
) -> None:
    repo, _ = repo_with_remote
    git(["checkout", "-b", "active-branch"], cwd=repo)
    make_commit(repo, "active commit")
    git(["push", "-u", "origin", "active-branch"], cwd=repo)
    git(["checkout", "main"], cwd=repo)
    git_cmds.cmd_prune_gone_locals(Config())
    assert "active-branch" in local_branches(repo)


##
## === prune-merged-locals
##


def test_prune_merged_locals_removes_merged_branch(
    repo_with_remote: tuple[Path, Path],
) -> None:
    repo, _ = repo_with_remote
    git(["checkout", "-b", "merged-feature"], cwd=repo)
    make_commit(repo, "feature commit")
    git(["checkout", "main"], cwd=repo)
    git(["merge", "merged-feature", "--no-ff", "-m", "merge feature"], cwd=repo)
    git(["push"], cwd=repo)
    git_cmds.cmd_prune_merged_locals(Config(), "origin/main")
    assert "merged-feature" not in local_branches(repo)


def test_prune_merged_locals_never_deletes_main(
    repo_with_remote: tuple[Path, Path],
) -> None:
    repo, _ = repo_with_remote
    git_cmds.cmd_prune_merged_locals(Config(), "origin/main")
    assert "main" in local_branches(repo)


def test_prune_merged_locals_never_deletes_current_branch(
    repo_with_remote: tuple[Path, Path],
) -> None:
    repo, _ = repo_with_remote
    git(["checkout", "-b", "current"], cwd=repo)
    make_commit(repo, "current commit")
    git(["checkout", "main"], cwd=repo)
    git(["merge", "current", "--no-ff", "-m", "merge current"], cwd=repo)
    git(["push"], cwd=repo)
    git(["checkout", "current"], cwd=repo)
    git_cmds.cmd_prune_merged_locals(Config(), "origin/main")
    assert "current" in local_branches(repo)


##
## === cleanup-local-branches
##


def test_cleanup_local_branches_runs_both_passes(
    repo_with_remote: tuple[Path, Path],
) -> None:
    repo, _ = repo_with_remote
    ## set up a gone branch
    git(["checkout", "-b", "gone"], cwd=repo)
    git(["push", "-u", "origin", "gone"], cwd=repo)
    git(["checkout", "main"], cwd=repo)
    git(["push", "origin", "--delete", "gone"], cwd=repo)
    ## set up a merged branch
    git(["checkout", "-b", "merged"], cwd=repo)
    make_commit(repo, "merged commit")
    git(["checkout", "main"], cwd=repo)
    git(["merge", "merged", "--no-ff", "-m", "merge merged"], cwd=repo)
    git(["push"], cwd=repo)
    git_cmds.cmd_cleanup_local_branches(Config(), "origin/main")
    branches = local_branches(repo)
    assert "gone" not in branches
    assert "merged" not in branches
    assert "main" in branches
