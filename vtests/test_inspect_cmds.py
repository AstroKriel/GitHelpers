"""
Validation tests for read-only inspection commands.
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
from git_helpers import git_utils
from git_helpers.shell_utils import Config
from vtests.helpers import git, make_commits


##
## === show-recent-commits
##


def test_show_recent_commits_runs_without_error(
    repo: Path,
) -> None:
    make_commits(repo, 5)
    git_utils.show_recent_commits(Config(), max_entries=3)


def test_show_recent_commits_default_max_entries(
    repo: Path,
) -> None:
    make_commits(repo, 5)
    git_utils.show_recent_commits(Config())


##
## === ahead-behind
##


def test_ahead_behind_shows_correct_counts(
    repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture,
) -> None:
    repo, _ = repo_with_remote
    make_commits(repo, 2, prefix="local")
    git_utils.show_ahead_behind(Config())
    out = capsys.readouterr().out
    assert "ahead: 2" in out
    assert "behind: 0" in out


def test_ahead_behind_behind_counts(
    repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture,
) -> None:
    repo, remote = repo_with_remote
    ## push commits from a second clone to simulate another user's work
    second = repo.parent / "second"
    second.mkdir()
    git(["clone", str(remote), str(second)], cwd=repo.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        git(["config", key, val], cwd=second)
    make_commits(second, 3, prefix="remote")
    git(["push"], cwd=second)
    ## fetch to update tracking refs without pulling
    git(["fetch"], cwd=repo)
    git_utils.show_ahead_behind(Config())
    out = capsys.readouterr().out
    assert "ahead: 0" in out
    assert "behind: 3" in out


##
## === local-remotes
##


def test_local_remotes_lists_origin(
    repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture,
) -> None:
    git_utils.show_local_remotes(Config())
    out = capsys.readouterr().out
    assert "origin" in out


def test_local_remotes_lists_multiple_remotes(
    repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture,
) -> None:
    repo, remote = repo_with_remote
    git(["remote", "add", "upstream", str(remote)], cwd=repo)
    git_utils.show_local_remotes(Config())
    out = capsys.readouterr().out
    assert "origin" in out
    assert "upstream" in out


##
## === unpulled-commits
##


def test_unpulled_commits_shows_remote_commits(
    repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture,
) -> None:
    repo, remote = repo_with_remote
    ## push commits from a second clone
    second = repo.parent / "second"
    second.mkdir()
    git(["clone", str(remote), str(second)], cwd=repo.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        git(["config", key, val], cwd=second)
    make_commits(second, 2, prefix="upstream commit")
    git(["push"], cwd=second)
    git_utils.show_unpulled_commits(Config())
    ## the run_cmd output goes to the terminal (subprocess), but the function
    ## should complete without error; verify the remote commits exist
    result = git(["log", "--oneline", "HEAD..origin/main"], cwd=repo)
    assert "upstream commit" in result.stdout


##
## === is-detached
##


def test_is_detached_exits_1_on_branch(
    repo: Path,
) -> None:
    with pytest.raises(SystemExit) as exc:
        git_utils.check_is_detached(Config())
    assert exc.value.code == 1


def test_is_detached_exits_0_when_detached(
    repo: Path,
) -> None:
    sha = git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()
    ## detach HEAD by checking out a commit directly
    subprocess.run(["git", "checkout", sha], cwd=repo, capture_output=True, check=True)
    with pytest.raises(SystemExit) as exc:
        git_utils.check_is_detached(Config())
    assert exc.value.code == 0
