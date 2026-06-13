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
from git_helpers import git_inspection
from git_helpers.shell_interface import Config
from vtests import helpers as vtest_helpers

##
## === show-recent-commits
##


def test_show_recent_commits_runs_without_error(
    make_repo_: Path,
) -> None:
    vtest_helpers.make_commits(make_repo_, 5)
    git_inspection.show_recent_commits(Config(), max_entries=3)


def test_show_recent_commits_default_max_entries(
    make_repo_: Path,
) -> None:
    vtest_helpers.make_commits(make_repo_, 5)
    git_inspection.show_recent_commits(Config())


##
## === ahead-behind
##


def test_ahead_behind_shows_correct_counts(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.make_commits(repo_dir, 2, prefix="local")
    git_inspection.count_ahead_behind(Config())
    out = capsys.readouterr().out
    assert "ahead: 2" in out
    assert "behind: 0" in out


def test_ahead_behind_behind_counts(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
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
    git_inspection.count_ahead_behind(Config())
    out = capsys.readouterr().out
    assert "ahead: 0" in out
    assert "behind: 3" in out


##
## === local-remotes
##


def test_local_remotes_lists_origin(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    git_inspection.show_local_remotes(Config())
    out = capsys.readouterr().out
    assert "origin" in out


def test_local_remotes_lists_multiple_remotes(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    vtest_helpers.git(["remote", "add", "upstream", str(remote_dir)], cwd=repo_dir)
    git_inspection.show_local_remotes(Config())
    out = capsys.readouterr().out
    assert "origin" in out
    assert "upstream" in out


##
## === unpulled-commits
##


def test_unpulled_commits_shows_remote_commits(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
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
    git_inspection.show_unpulled_commits(Config())
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
        git_inspection.check_is_detached(Config())
    assert exc.value.code == 1


def test_is_detached_exits_0_when_detached(
    make_repo_: Path,
) -> None:
    sha = vtest_helpers.git(["rev-parse", "HEAD"], cwd=make_repo_).stdout.strip()
    ## detach HEAD by checking out a commit directly
    subprocess.run(["git", "checkout", sha], cwd=make_repo_, capture_output=True, check=True)
    with pytest.raises(SystemExit) as exc:
        git_inspection.check_is_detached(Config())
    assert exc.value.code == 0


##
## === show-diff
##


def test_show_diff_runs_without_error(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (make_repo_ / "dirty.txt").write_text("change")
    vtest_helpers.git(["add", "dirty.txt"], cwd=make_repo_)
    git_inspection.show_diff(Config(dry_run=True))
    out = capsys.readouterr().err
    assert "git diff HEAD" in out


def test_show_diff_with_path_scopes_command(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (make_repo_ / "dirty.txt").write_text("change")
    vtest_helpers.git(["add", "dirty.txt"], cwd=make_repo_)
    git_inspection.show_diff(Config(dry_run=True), path="dirty.txt")
    out = capsys.readouterr().err
    assert "dirty.txt" in out


##
## === show-diff-committed
##


def test_show_diff_committed_with_explicit_base(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, 2)
    git_inspection.show_diff_committed(Config(dry_run=True), base="main")
    out = capsys.readouterr().err
    assert "main...HEAD" in out


def test_show_diff_committed_with_path(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, 1)
    git_inspection.show_diff_committed(Config(dry_run=True), base="main", path=".commit_counter")
    out = capsys.readouterr().err
    assert "main...HEAD" in out
    assert ".commit_counter" in out


def test_show_diff_committed_infers_default_branch(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["remote", "set-head", "origin", "main"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, 1)
    git_inspection.show_diff_committed(Config(dry_run=True))
    out = capsys.readouterr().err
    assert "main...HEAD" in out


def test_show_diff_committed_kills_when_on_base_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    ## still on main; passing base explicitly so the guard fires regardless of remote HEAD config
    with pytest.raises(SystemExit):
        git_inspection.show_diff_committed(Config(), base="main")


##
## === show-diff-last
##


def test_show_diff_last_committed_uses_correct_refs(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vtest_helpers.make_commits(make_repo_, 3)
    git_inspection.show_diff_last(Config(dry_run=True), num_commits=3)
    out = capsys.readouterr().err
    assert "HEAD~3 HEAD" in out


def test_show_diff_last_include_uncommitted_omits_head_arg(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vtest_helpers.make_commits(make_repo_, 2)
    git_inspection.show_diff_last(Config(dry_run=True), num_commits=2, include_uncommitted=True)
    out = capsys.readouterr().err
    assert "HEAD~2" in out
    assert "HEAD~2 HEAD" not in out


def test_show_diff_last_with_path_scopes_command(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vtest_helpers.make_commits(make_repo_, 2)
    git_inspection.show_diff_last(Config(dry_run=True), num_commits=2, path=".commit_counter")
    out = capsys.readouterr().err
    assert "HEAD~2" in out
    assert ".commit_counter" in out


def test_show_diff_last_kills_on_zero_commits(
    make_repo_: Path,
) -> None:
    with pytest.raises(SystemExit):
        git_inspection.show_diff_last(Config(), num_commits=0)


## } SCRIPT
