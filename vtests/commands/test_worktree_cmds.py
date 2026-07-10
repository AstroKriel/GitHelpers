## { SCRIPT

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## third-party
import pytest

## local
from git_helpers.commands import git_worktrees
from git_helpers.shell_interface import Config
from vtests import helpers as vtest_helpers

##
## === HELPERS
##


def worktree_path_for(repo_dir: Path, branch_name: str) -> Path:
    """Return the expected default worktree path for a branch (sibling of repo_dir)."""
    branch_slug = branch_name.replace("/", "-")
    return repo_dir.parent / f"{repo_dir.name}-worktrees" / branch_slug


##
## === create-worktree
##


def test_create_worktree_creates_directory(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=make_repo_)
    vtest_helpers.git(["checkout", "main"], cwd=make_repo_)
    git_worktrees.cmd_create_worktree(Config(), "feature")
    assert worktree_path_for(make_repo_, "feature").is_dir()


def test_create_worktree_sets_upstream_when_remote_branch_exists(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    ## push without -u so the local branch has no upstream yet
    vtest_helpers.git(["push", "origin", "feature"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    assert vtest_helpers.upstream_of(repo_dir, "feature") == ""
    git_worktrees.cmd_create_worktree(Config(), "feature")
    assert vtest_helpers.upstream_of(repo_dir, "feature") == "origin/feature"


def test_create_worktree_no_upstream_when_remote_branch_missing(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    git_worktrees.cmd_create_worktree(Config(), "feature")
    assert vtest_helpers.upstream_of(repo_dir, "feature") == ""


def test_create_worktree_no_upstream_when_no_remote(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=make_repo_)
    vtest_helpers.git(["checkout", "main"], cwd=make_repo_)
    git_worktrees.cmd_create_worktree(Config(), "feature")
    assert vtest_helpers.upstream_of(make_repo_, "feature") == ""


##
## === remove-worktree
##


def test_remove_worktree_removes_directory(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    git_worktrees.cmd_create_worktree(Config(), "feature")
    worktree_path = worktree_path_for(repo_dir, "feature")
    assert worktree_path.is_dir()
    git_worktrees.cmd_remove_worktree(Config(), "feature")
    assert not worktree_path.exists()


def test_remove_worktree_deletes_branch_when_merged(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    ## branch has no commits beyond main, so -d succeeds
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    git_worktrees.cmd_create_worktree(Config(), "feature")
    git_worktrees.cmd_remove_worktree(Config(), "feature")
    assert "feature" not in vtest_helpers.local_branches(repo_dir)


def test_remove_worktree_force_deletes_when_remote_branch_gone(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    ## create a branch with commits, push it, then simulate post-squash-merge
    ## cleanup by deleting the remote branch without merging into local main
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, msg="feature work")
    vtest_helpers.git(["push", "-u", "origin", "feature"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    git_worktrees.cmd_create_worktree(Config(), "feature")
    ## delete the remote branch (as GitHub does after a squash merge)
    vtest_helpers.git(["push", "origin", "--delete", "feature"], cwd=repo_dir)
    git_worktrees.cmd_remove_worktree(Config(), "feature")
    assert "feature" not in vtest_helpers.local_branches(repo_dir)


def test_remove_worktree_keeps_branch_when_remote_still_exists(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    ## push an initial commit so the remote branch exists, then make a second
    ## commit that is NOT pushed — git's -d refuses because the local branch is
    ## ahead of its upstream, so the branch must be kept while the remote is live
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, msg="pushed work")
    vtest_helpers.git(["push", "-u", "origin", "feature"], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, msg="unpushed work")
    vtest_helpers.git(["checkout", "main"], cwd=repo_dir)
    git_worktrees.cmd_create_worktree(Config(), "feature")
    git_worktrees.cmd_remove_worktree(Config(), "feature")
    worktree_path = worktree_path_for(repo_dir, "feature")
    assert not worktree_path.exists()
    assert "feature" in vtest_helpers.local_branches(repo_dir)


def test_remove_worktree_fails_when_no_worktree_found(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    with pytest.raises(SystemExit):
        git_worktrees.cmd_remove_worktree(Config(), "nonexistent-branch")


##
## === rename-branch
##


def test_rename_branch_renames_branch(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["checkout", "-b", "old-name"], cwd=make_repo_)
    git_worktrees.cmd_rename_branch(Config(), "new-name")
    assert "new-name" in vtest_helpers.local_branches(make_repo_)
    assert "old-name" not in vtest_helpers.local_branches(make_repo_)


def test_rename_branch_moves_worktree_directory(
    make_repo_: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vtest_helpers.git(["checkout", "-b", "old/name"], cwd=make_repo_)
    vtest_helpers.git(["checkout", "main"], cwd=make_repo_)
    git_worktrees.cmd_create_worktree(Config(), "old/name")
    old_worktree_path = worktree_path_for(make_repo_, "old/name")
    assert old_worktree_path.is_dir()
    ## rename-branch operates on the current branch; switch cwd into the linked
    ## worktree (old/name is already checked out there, so checkout from main fails)
    monkeypatch.chdir(old_worktree_path)
    git_worktrees.cmd_rename_branch(Config(), "new/name")
    new_worktree_path = worktree_path_for(make_repo_, "new/name")
    assert not old_worktree_path.exists()
    assert new_worktree_path.is_dir()


def test_rename_branch_relinks_worktree(
    make_repo_: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vtest_helpers.git(["checkout", "-b", "old/name"], cwd=make_repo_)
    vtest_helpers.git(["checkout", "main"], cwd=make_repo_)
    git_worktrees.cmd_create_worktree(Config(), "old/name")
    old_worktree_path = worktree_path_for(make_repo_, "old/name")
    monkeypatch.chdir(old_worktree_path)
    git_worktrees.cmd_rename_branch(Config(), "new/name")
    new_worktree_path = worktree_path_for(make_repo_, "new/name")
    ## verify git sees the worktree correctly after repair
    result = vtest_helpers.git(["worktree", "list", "--porcelain"], cwd=make_repo_)
    assert str(new_worktree_path) in result.stdout


def test_rename_branch_aborts_when_target_path_exists(
    make_repo_: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vtest_helpers.git(["checkout", "-b", "old/name"], cwd=make_repo_)
    vtest_helpers.git(["checkout", "main"], cwd=make_repo_)
    git_worktrees.cmd_create_worktree(Config(), "old/name")
    old_worktree_path = worktree_path_for(make_repo_, "old/name")
    ## pre-create the target path to trigger the pre-flight check
    target = worktree_path_for(make_repo_, "new/name")
    target.mkdir(parents=True)
    monkeypatch.chdir(old_worktree_path)
    with pytest.raises(SystemExit):
        git_worktrees.cmd_rename_branch(Config(), "new/name")
    ## branch must be unchanged
    assert "old/name" in vtest_helpers.local_branches(make_repo_)


## } SCRIPT
