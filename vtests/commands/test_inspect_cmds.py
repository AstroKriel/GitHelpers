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
from git_helpers.commands import git_inspection
from vtests import helpers as vtest_helpers

##
## === show-recent-commits
##


def test_show_recent_commits_runs_without_error(
    make_repo_: Path,
) -> None:
    vtest_helpers.make_commits(make_repo_, num_commits=5)
    git_inspection.show_recent_commits(max_entries=3)


def test_show_recent_commits_default_max_entries(
    make_repo_: Path,
) -> None:
    vtest_helpers.make_commits(make_repo_, num_commits=5)
    git_inspection.show_recent_commits()


def test_show_recent_commits_stat_includes_stat_flag(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vtest_helpers.make_commits(make_repo_, num_commits=2)
    git_inspection.show_recent_commits(show_files_changed=True)
    out = capsys.readouterr().err
    assert "--stat" in out


##
## === ahead-behind
##


def test_ahead_behind_shows_correct_counts(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.make_commits(
        repo_dir,
        num_commits=2,
        prefix="local",
    )
    git_inspection.count_ahead_behind()
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
    vtest_helpers.make_commits(
        second_dir,
        num_commits=3,
        prefix="remote",
    )
    vtest_helpers.git(["push"], cwd=second_dir)
    ## fetch to update tracking refs without pulling
    vtest_helpers.git(["fetch"], cwd=repo_dir)
    git_inspection.count_ahead_behind()
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
    git_inspection.show_local_remotes()
    out = capsys.readouterr().out
    assert "origin" in out


def test_local_remotes_lists_multiple_remotes(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    vtest_helpers.git(["remote", "add", "upstream", str(remote_dir)], cwd=repo_dir)
    git_inspection.show_local_remotes()
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
    vtest_helpers.make_commits(
        second_dir,
        num_commits=2,
        prefix="upstream commit",
    )
    vtest_helpers.git(["push"], cwd=second_dir)
    git_inspection.show_unpulled_commits()
    ## the run_cmd output goes to the terminal (subprocess), but the function
    ## should complete without error; verify the remote commits exist
    result = vtest_helpers.git(["log", "--oneline", "HEAD..origin/main"], cwd=repo_dir)
    assert "upstream commit" in result.stdout


##
## === show-diff-uncommitted
##


def test_show_diff_runs_without_error(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (make_repo_ / "dirty.txt").write_text("change")
    vtest_helpers.git(["add", "dirty.txt"], cwd=make_repo_)
    git_inspection.show_diff()
    out = capsys.readouterr().err
    assert "git diff --color=always HEAD" in out


def test_show_diff_with_path_scopes_command(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (make_repo_ / "dirty.txt").write_text("change")
    vtest_helpers.git(["add", "dirty.txt"], cwd=make_repo_)
    git_inspection.show_diff(path="dirty.txt")
    out = capsys.readouterr().err
    assert "dirty.txt" in out


def test_show_diff_word_diff_includes_flag(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    git_inspection.show_diff(word_diff=True)
    out = capsys.readouterr().err
    assert "--color-words" in out


def test_show_diff_omits_word_diff_flag_by_default(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    git_inspection.show_diff()
    out = capsys.readouterr().err
    assert "--color-words" not in out


##
## === show-diff-untracked
##


def test_show_diff_untracked_runs_without_error(
    make_repo_: Path,
) -> None:
    (make_repo_ / "new_file.txt").write_text("new content\n")
    ## real run: git diff --no-index exits 1 when a difference is found (the
    ## normal case here), so this must not raise despite the non-zero exit code
    git_inspection.show_diff_untracked(path="new_file.txt")


def test_show_diff_untracked_diffs_against_dev_null(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (make_repo_ / "new_file.txt").write_text("new content\n")
    git_inspection.show_diff_untracked(path="new_file.txt")
    out = capsys.readouterr().err
    assert "git diff --color=always --no-index /dev/null new_file.txt" in out


def test_show_diff_untracked_word_diff_includes_flag(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (make_repo_ / "new_file.txt").write_text("new content\n")
    git_inspection.show_diff_untracked(
        path="new_file.txt",
        word_diff=True,
    )
    out = capsys.readouterr().err
    assert "--color-words" in out


##
## === show-diff-committed
##


def test_show_diff_committed_with_explicit_base(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, num_commits=2)
    git_inspection.show_diff_committed(
        base="origin/main",
        no_fetch=True,
    )
    out = capsys.readouterr().err
    assert "origin/main...HEAD" in out


def test_show_diff_committed_with_path(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, num_commits=1)
    git_inspection.show_diff_committed(
        base="origin/main",
        no_fetch=True,
        path=".commit_counter",
    )
    out = capsys.readouterr().err
    assert "origin/main...HEAD" in out
    assert ".commit_counter" in out


def test_show_diff_committed_infers_default_branch(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["remote", "set-head", "origin", "main"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, num_commits=1)
    git_inspection.show_diff_committed(no_fetch=True)
    out = capsys.readouterr().err
    assert "origin/main...HEAD" in out


def test_show_diff_committed_fetches_by_default(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, num_commits=1)
    git_inspection.show_diff_committed(base="origin/main")
    out = capsys.readouterr().err
    assert "git fetch" in out


def test_show_diff_committed_exits_when_base_not_remote_qualified(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=make_repo_with_remote[0])
    with pytest.raises(SystemExit):
        git_inspection.show_diff_committed(
            base="main",
            no_fetch=True,
        )


def test_show_diff_committed_name_only_includes_flag(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, num_commits=1)
    git_inspection.show_diff_committed(
        base="origin/main",
        name_only=True,
        no_fetch=True,
    )
    out = capsys.readouterr().err
    assert "--name-only" in out


def test_show_diff_committed_exits_when_on_base_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    with pytest.raises(SystemExit):
        git_inspection.show_diff_committed(
            base="origin/main",
            no_fetch=True,
        )


def test_show_diff_committed_word_diff_includes_flag(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, num_commits=1)
    git_inspection.show_diff_committed(
        base="origin/main",
        no_fetch=True,
        word_diff=True,
    )
    out = capsys.readouterr().err
    assert "--color-words" in out


##
## === show-commits-on-branch
##


def test_show_commits_on_branch_uses_two_dot_range(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, num_commits=2)
    git_inspection.show_commits_on_branch(
        base="origin/main",
        no_fetch=True,
    )
    out = capsys.readouterr().err
    assert "origin/main..HEAD" in out


def test_show_commits_on_branch_infers_default_branch(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["remote", "set-head", "origin", "main"], cwd=repo_dir)
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, num_commits=1)
    git_inspection.show_commits_on_branch(no_fetch=True)
    out = capsys.readouterr().err
    assert "origin/main..HEAD" in out


def test_show_commits_on_branch_show_files_changed_includes_stat(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, num_commits=1)
    git_inspection.show_commits_on_branch(
        base="origin/main",
        show_files_changed=True,
        no_fetch=True,
    )
    out = capsys.readouterr().err
    assert "--stat" in out


def test_show_commits_on_branch_fetches_by_default(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=repo_dir)
    vtest_helpers.make_commits(repo_dir, num_commits=1)
    git_inspection.show_commits_on_branch(base="origin/main")
    out = capsys.readouterr().err
    assert "git fetch" in out


def test_show_commits_on_branch_exits_when_on_base_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    with pytest.raises(SystemExit):
        git_inspection.show_commits_on_branch(
            base="origin/main",
            no_fetch=True,
        )


def test_show_commits_on_branch_exits_when_base_not_remote_qualified(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    vtest_helpers.git(["checkout", "-b", "feature"], cwd=make_repo_with_remote[0])
    with pytest.raises(SystemExit):
        git_inspection.show_commits_on_branch(
            base="main",
            no_fetch=True,
        )


##
## === show-diff-n-commits
##


def test_show_diff_last_committed_uses_correct_refs(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vtest_helpers.make_commits(make_repo_, num_commits=3)
    git_inspection.show_diff_last(num_commits=3)
    out = capsys.readouterr().err
    assert "'HEAD~3' HEAD" in out


def test_show_diff_last_include_uncommitted_omits_head_arg(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vtest_helpers.make_commits(make_repo_, num_commits=2)
    git_inspection.show_diff_last(
        num_commits=2,
        include_uncommitted=True,
    )
    out = capsys.readouterr().err
    assert "'HEAD~2'" in out
    assert "'HEAD~2' HEAD" not in out


def test_show_diff_last_with_path_scopes_command(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vtest_helpers.make_commits(make_repo_, num_commits=2)
    git_inspection.show_diff_last(
        num_commits=2,
        path=".commit_counter",
    )
    out = capsys.readouterr().err
    assert "HEAD~2" in out
    assert ".commit_counter" in out


def test_show_diff_last_exits_on_zero_commits(
    make_repo_: Path,
) -> None:
    with pytest.raises(SystemExit):
        git_inspection.show_diff_last(num_commits=0)


def test_show_diff_last_word_diff_includes_flag(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vtest_helpers.make_commits(make_repo_, num_commits=2)
    git_inspection.show_diff_last(
        num_commits=2,
        word_diff=True,
    )
    out = capsys.readouterr().err
    assert "--color-words" in out


##
## === show-commit
##


def test_show_commit_word_diff_includes_flag(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vtest_helpers.make_commits(make_repo_, num_commits=1)
    commit_hash = vtest_helpers.git(["rev-parse", "HEAD"], cwd=make_repo_).stdout.strip()
    git_inspection.show_commit(
        commit=commit_hash,
        word_diff=True,
    )
    out = capsys.readouterr().err
    assert "--color-words" in out


def test_show_commit_omits_word_diff_flag_by_default(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vtest_helpers.make_commits(make_repo_, num_commits=1)
    commit_hash = vtest_helpers.git(["rev-parse", "HEAD"], cwd=make_repo_).stdout.strip()
    git_inspection.show_commit(commit=commit_hash)
    out = capsys.readouterr().err
    assert "--color-words" not in out


##
## === show-current-commit-hash
##


def test_show_current_commit_hash_prints_correct_hash(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commit_hash = vtest_helpers.git(["rev-parse", "HEAD"], cwd=make_repo_).stdout.strip()
    git_inspection.show_current_commit_hash()
    out = capsys.readouterr().out
    assert commit_hash in out


##
## === show-commit-info
##


def test_show_commit_info_omits_fetch_when_already_local(
    make_repo_: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commit_hash = vtest_helpers.git(["rev-parse", "HEAD"], cwd=make_repo_).stdout.strip()
    git_inspection.show_commit_info(commit=commit_hash)
    out = capsys.readouterr().err
    assert "git fetch" not in out
    assert commit_hash in out


def test_show_commit_info_fetches_when_not_local(
    make_repo_with_remote: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    second_dir = repo_dir.parent / "second"
    second_dir.mkdir()
    vtest_helpers.git(["clone", str(remote_dir), str(second_dir)], cwd=repo_dir.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        vtest_helpers.git(["config", key, val], cwd=second_dir)
    vtest_helpers.make_commits(
        second_dir,
        num_commits=1,
        prefix="remote-only",
    )
    vtest_helpers.git(["push"], cwd=second_dir)
    commit_hash = vtest_helpers.git(["rev-parse", "HEAD"], cwd=second_dir).stdout.strip()
    git_inspection.show_commit_info(commit=commit_hash)
    out = capsys.readouterr().err
    assert "git fetch" in out


def test_show_commit_info_real_fetch_makes_commit_available_locally(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, remote_dir = make_repo_with_remote
    second_dir = repo_dir.parent / "second"
    second_dir.mkdir()
    vtest_helpers.git(["clone", str(remote_dir), str(second_dir)], cwd=repo_dir.parent)
    for key, val in [("user.name", "Test Dummy"), ("user.email", "TestDummy@bla.com")]:
        vtest_helpers.git(["config", key, val], cwd=second_dir)
    vtest_helpers.make_commits(
        second_dir,
        num_commits=1,
        prefix="remote-only",
    )
    vtest_helpers.git(["push"], cwd=second_dir)
    commit_hash = vtest_helpers.git(["rev-parse", "HEAD"], cwd=second_dir).stdout.strip()
    ## real (non-dry) run: must actually fetch the commit into repo_dir
    git_inspection.show_commit_info(commit=commit_hash)
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit_hash}^{{commit}}"],
        cwd=repo_dir,
        capture_output=True,
    )
    assert result.returncode == 0


## } SCRIPT
