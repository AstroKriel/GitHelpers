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


def test_find_default_remote_name_is_none_without_remotes(
    make_repo_: Path,
) -> None:
    assert repo_state.find_default_remote_name() is None


def test_get_default_remote_name_exits_without_remotes(
    make_repo_: Path,
) -> None:
    with pytest.raises(SystemExit):
        repo_state.get_default_remote_name()


##
## === find_upstream
##


def test_find_upstream_returns_remote_and_branch(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    ## fixture starts on main with upstream origin/main
    upstream = repo_state.find_upstream(branch_name="main")
    assert upstream is not None
    assert upstream == repo_state.Upstream(
        remote_name="origin",
        branch_name="main",
    )
    assert upstream.ref_name == "origin/main"


def test_find_upstream_keeps_slash_in_branch_name(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "-b", "fix/my-feature"], cwd=repo_dir)
    vtest_helpers.make_commit(repo_dir, msg="branch commit")
    vtest_helpers.git(["push", "-u", "origin", "fix/my-feature"], cwd=repo_dir)
    upstream = repo_state.find_upstream(branch_name="fix/my-feature")
    assert upstream is not None
    assert upstream.branch_name == "fix/my-feature"


def test_find_upstream_reads_a_local_upstream(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["branch", "--track", "feature", "main"], cwd=make_repo_)
    upstream = repo_state.find_upstream(branch_name="feature")
    assert upstream is not None
    assert upstream.is_local
    assert upstream.ref_name == "main"


def test_find_upstream_is_none_without_upstream(
    make_repo_: Path,
) -> None:
    assert repo_state.find_upstream(branch_name="main") is None


##
## === cached facts
##


def test_cached_facts_follow_a_change_of_directory(
    make_repo_: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_repo_root = repo_state.collect_repo_state().repo_root
    other_repo_dir = tmp_path / "other_repo"
    other_repo_dir.mkdir()
    vtest_helpers.git(["init", "-b", "main"], cwd=other_repo_dir)
    monkeypatch.chdir(other_repo_dir)
    other_repo_root = repo_state.collect_repo_state().repo_root
    assert other_repo_root != first_repo_root
    assert other_repo_root == other_repo_dir.resolve()


def test_outside_a_repo_exits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        repo_state.find_current_branch_name()


##
## === collect_repo_state
##


def test_collect_repo_state_reports_without_exiting_when_detached(
    make_repo_with_remote: tuple[Path, Path],
) -> None:
    repo_dir, _ = make_repo_with_remote
    vtest_helpers.git(["checkout", "--detach", "HEAD"], cwd=repo_dir)
    repo_state_snapshot = repo_state.collect_repo_state()
    assert repo_state_snapshot.current_branch_name is None
    assert repo_state_snapshot.upstream is None
    assert repo_state_snapshot.default_remote_name == "origin"
    assert repo_state_snapshot.worktree_is_clean
    assert repo_state_snapshot.in_progress_operation is None


def test_collect_repo_state_finds_a_stopped_merge(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["checkout", "-b", "side"], cwd=make_repo_)
    (make_repo_ / "clash.txt").write_text("side\n")
    vtest_helpers.git(["add", "clash.txt"], cwd=make_repo_)
    vtest_helpers.git(["commit", "-m", "side"], cwd=make_repo_)
    vtest_helpers.git(["checkout", "main"], cwd=make_repo_)
    (make_repo_ / "clash.txt").write_text("main\n")
    vtest_helpers.git(["add", "clash.txt"], cwd=make_repo_)
    vtest_helpers.git(["commit", "-m", "main"], cwd=make_repo_)
    with pytest.raises(subprocess.CalledProcessError):
        vtest_helpers.git(["merge", "side"], cwd=make_repo_)
    assert repo_state.collect_repo_state().in_progress_operation == "merge"


##
## === get_attached_branch_name
##


def test_get_attached_branch_name_returns_branch(
    make_repo_: Path,
) -> None:
    assert repo_state.get_attached_branch_name() == "main"


def test_get_attached_branch_name_exits_when_detached(
    make_repo_: Path,
) -> None:
    vtest_helpers.git(["checkout", "--detach", "HEAD"], cwd=make_repo_)
    with pytest.raises(SystemExit):
        repo_state.get_attached_branch_name()


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
