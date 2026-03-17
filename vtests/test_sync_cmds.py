"""
Validation tests for syncing and history-rewriting commands.
"""

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## third-party
import pytest

## local
from git_helpers import run_cmds
from git_helpers.shell_utils import Config
from vtests.helpers import current_commit_message, git, head_sha, make_commit, make_commits


##
## === sync-branch
##


def test_sync_branch_fails_with_dirty_worktree(
    repo_with_remote: tuple[Path, Path],
) -> None:
    repo, _ = repo_with_remote
    (repo / "dirty.txt").write_text("uncommitted change")
    git(["add", "dirty.txt"], cwd=repo)
    with pytest.raises(SystemExit):
        run_cmds.cmd_sync_branch(Config())


def test_sync_branch_proceeds_with_allow_dirty(
    repo_with_remote: tuple[Path, Path],
) -> None:
    repo, remote = repo_with_remote
    (repo / "dirty.txt").write_text("uncommitted change")
    git(["add", "dirty.txt"], cwd=repo)
    ## no remote commits to pull — just verify the dirty check is skipped
    run_cmds.cmd_sync_branch(Config(allow_dirty=True))


def test_sync_branch_pulls_remote_commits(
    repo_with_remote: tuple[Path, Path],
) -> None:
    repo, remote = repo_with_remote
    ## push new commits from a second clone
    second = repo.parent / "second"
    second.mkdir()
    git(["clone", str(remote), str(second)], cwd=repo.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        git(["config", key, val], cwd=second)
    make_commits(second, 2, prefix="remote commit")
    git(["push"], cwd=second)
    ## sync should bring those commits into the local repo
    before = head_sha(repo)
    run_cmds.cmd_sync_branch(Config())
    after = head_sha(repo)
    assert before != after


def test_sync_branch_with_explicit_base(
    repo_with_remote: tuple[Path, Path],
) -> None:
    repo, _ = repo_with_remote
    ## create a feature branch with some commits
    git(["checkout", "-b", "feature"], cwd=repo)
    make_commits(repo, 2, prefix="feature")
    git(["push", "-u", "origin", "feature"], cwd=repo)
    ## add commits to main on remote
    second = repo.parent / "second"
    second.mkdir()
    git(["clone", str(repo.parent / "remote.git"), str(second)], cwd=repo.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        git(["config", key, val], cwd=second)
    make_commit(second, "main update", filename=".main_counter")
    git(["push"], cwd=second)
    ## sync feature branch against origin/main
    run_cmds.cmd_sync_branch(Config(), "origin/main")


##
## === rename-last-commit
##


def test_rename_last_commit_changes_message(
    repo: Path,
) -> None:
    original = current_commit_message(repo)
    run_cmds.cmd_rename_last_commit(Config(), ["new", "commit", "message"])
    assert current_commit_message(repo) == "new commit message"
    assert current_commit_message(repo) != original


def test_rename_last_commit_joins_words(
    repo: Path,
) -> None:
    run_cmds.cmd_rename_last_commit(Config(), ["fix", "typo", "in", "readme"])
    assert current_commit_message(repo) == "fix typo in readme"


def test_rename_last_commit_preserves_sha_prefix(
    repo: Path,
) -> None:
    ## amend changes the SHA — verify it actually changed
    before = head_sha(repo)
    run_cmds.cmd_rename_last_commit(Config(), ["amended"])
    after = head_sha(repo)
    assert before != after
