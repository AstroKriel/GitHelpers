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


## } SCRIPT
