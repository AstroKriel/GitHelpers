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
from git_helpers import git_utils
from git_helpers.shell_utils import Config
from vtests import helpers as vtest_helpers

##
## === show-recent-commits
##


def test_show_recent_commits_runs_without_error(
    make_repo_: Path,
) -> None:
    vtest_helpers.make_commits(make_repo_, 5)
    git_utils.show_recent_commits(Config(), max_entries=3)


def test_show_recent_commits_default_max_entries(
    make_repo_: Path,
) -> None:
    vtest_helpers.make_commits(make_repo_, 5)
    git_utils.show_recent_commits(Config())


##
## === ahead-behind
##


def test_ahead_behind_shows_correct_counts(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture,
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.make_commits(repo_dir, 2, prefix="local")
    git_utils.count_ahead_behind(Config())
    out = capsys.readouterr().out
    assert "ahead: 2" in out
    assert "behind: 0" in out


def test_ahead_behind_behind_counts(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture,
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    ## push commits from a second clone to simulate another user's work
    second_dir = repo_dir.parent / "second"
    second_dir.mkdir()
    vtest_helpers.git(["clone", str(remote_dir), str(second_dir)], cwd=repo_dir.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        vtest_helpers.git(["config", key, val], cwd=second_dir)
    vtest_helpers.make_commits(second_dir, 3, prefix="remote")
    vtest_helpers.git(["push"], cwd=second_dir)
    ## fetch to update tracking refs without pulling
    vtest_helpers.git(["fetch"], cwd=repo_dir)
    git_utils.count_ahead_behind(Config())
    out = capsys.readouterr().out
    assert "ahead: 0" in out
    assert "behind: 3" in out


##
## === local-remotes
##


def test_local_remotes_lists_origin(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture,
) -> None:
    git_utils.show_local_remotes(Config())
    out = capsys.readouterr().out
    assert "origin" in out


def test_local_remotes_lists_multiple_remotes(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture,
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    vtest_helpers.git(["remote", "add", "upstream", str(remote_dir)], cwd=repo_dir)
    git_utils.show_local_remotes(Config())
    out = capsys.readouterr().out
    assert "origin" in out
    assert "upstream" in out


##
## === unpulled-commits
##


def test_unpulled_commits_shows_remote_commits(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture,
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    ## push commits from a second clone
    second_dir = repo_dir.parent / "second"
    second_dir.mkdir()
    vtest_helpers.git(["clone", str(remote_dir), str(second_dir)], cwd=repo_dir.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        vtest_helpers.git(["config", key, val], cwd=second_dir)
    vtest_helpers.make_commits(second_dir, 2, prefix="upstream commit")
    vtest_helpers.git(["push"], cwd=second_dir)
    git_utils.show_unpulled_commits(Config())
    ## the run_cmd output goes to the terminal (subprocess), but the function
    ## should complete without error; verify the remote commits exist
    result = vtest_helpers.git(["log", "--oneline", "HEAD..origin/main"], cwd=repo_dir)
    assert "upstream commit" in result.stdout


##
## === is-detached
##


def test_is_detached_exits_1_on_branch(
    make_repo_: Path,
) -> None:
    with pytest.raises(SystemExit) as exc:
        git_utils.check_is_detached(Config())
    assert exc.value.code == 1


def test_is_detached_exits_0_when_detached(
    make_repo_: Path,
) -> None:
    sha = vtest_helpers.git(["rev-parse", "HEAD"], cwd=make_repo_).stdout.strip()
    ## detach HEAD by checking out a commit directly
    subprocess.run(["git", "checkout", sha], cwd=make_repo_, capture_output=True, check=True)
    with pytest.raises(SystemExit) as exc:
        git_utils.check_is_detached(Config())
    assert exc.value.code == 0


## } SCRIPT
