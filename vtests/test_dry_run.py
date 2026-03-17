"""
Validation tests for --dry-run: verifies no mutations occur.
"""

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## local
from git_helpers import git_cmds
from git_helpers.shell_utils import Config
from vtests.helpers import current_commit_message, git, head_sha, local_branches, make_commit


##
## === TESTS
##


def test_dry_run_delete_branch_leaves_branch_intact(
    repo: Path,
) -> None:
    git(["checkout", "-b", "dry-target"], cwd=repo)
    make_commit(repo, "dry commit")
    git(["checkout", "main"], cwd=repo)
    git(["merge", "dry-target"], cwd=repo)
    git_cmds.cmd_delete_local_branch(Config(dry_run=True), "dry-target")
    assert "dry-target" in local_branches(repo)


def test_dry_run_rename_last_commit_leaves_message_unchanged(
    repo: Path,
) -> None:
    original = current_commit_message(repo)
    git_cmds.cmd_rename_last_commit(Config(dry_run=True), ["completely", "different", "message"])
    assert current_commit_message(repo) == original


def test_dry_run_rename_last_commit_leaves_sha_unchanged(
    repo: Path,
) -> None:
    before = head_sha(repo)
    git_cmds.cmd_rename_last_commit(Config(dry_run=True), ["new", "message"])
    assert head_sha(repo) == before


def test_dry_run_sync_branch_leaves_head_unchanged(
    repo_with_remote: tuple[Path, Path],
) -> None:
    repo, remote = repo_with_remote
    ## push a new commit from a second clone
    second = repo.parent / "second"
    second.mkdir()
    git(["clone", str(remote), str(second)], cwd=repo.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        git(["config", key, val], cwd=second)
    make_commit(second, "remote commit")
    git(["push"], cwd=second)
    ## dry-run sync should leave HEAD where it is
    before = head_sha(repo)
    git_cmds.cmd_sync_branch(Config(dry_run=True))
    assert head_sha(repo) == before
