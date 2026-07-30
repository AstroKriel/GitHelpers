## { SCRIPT

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## local
from git_helpers import repo_state
from vtests import helpers as vtest_helpers

##
## === get_default_remote_name
##


def test_get_default_remote_name_prefers_origin(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    vtest_helpers.git(["remote", "add", "upstream", str(remote_dir)], cwd=repo_dir)
    assert repo_state.get_default_remote_name() == "origin"


def test_get_default_remote_name_falls_back_to_first_remote(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["remote", "rename", "origin", "upstream"], cwd=repo_dir)
    assert repo_state.get_default_remote_name() == "upstream"



##
## === get_upstream_branch_name
##


def test_get_upstream_branch_name_returns_branch_portion(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    ## fixture starts on main with upstream origin/main
    assert repo_state.get_upstream_branch_name() == "main"


def test_get_upstream_branch_name_handles_slash_in_branch_name(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "fix/my-feature"], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, msg="branch commit")
    vtest_helpers.git(["push", "-u", "origin", "fix/my-feature"], cwd=repo_dir)
    assert repo_state.get_upstream_branch_name() == "fix/my-feature"


##
## === list_worktrees / branches_with_worktrees
##


def test_list_worktrees_includes_main_at_index_zero(
    make_repo_: Path,
) -> None:
    worktrees = repo_state.list_worktrees()
    assert len(worktrees) == 1
    assert worktrees[0]["branch"] == "main"


def test_list_worktrees_includes_linked_worktree(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["branch", "feature"], cwd=make_repo_)
    worktree_dir = make_repo_.parent / "feature-worktree"
    vtest_helpers.git(["worktree", "add", str(worktree_dir), "feature"], cwd=make_repo_)
    worktrees = repo_state.list_worktrees()
    branches = [worktree["branch"] for worktree in worktrees]
    assert branches == ["main", "feature"]


def test_branches_with_worktrees_includes_main_and_linked(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["branch", "feature"], cwd=make_repo_)
    worktree_dir = make_repo_.parent / "feature-worktree"
    vtest_helpers.git(["worktree", "add", str(worktree_dir), "feature"], cwd=make_repo_)
    assert repo_state.branches_with_worktrees() == {"main", "feature"}


def test_branches_with_worktrees_excludes_plain_local_branch(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["branch", "no-worktree"], cwd=make_repo_)
    assert "no-worktree" not in repo_state.branches_with_worktrees()


## } SCRIPT
