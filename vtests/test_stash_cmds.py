## { SCRIPT

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## third-party
import pytest

## local
from git_helpers import git_sync
from git_helpers.shell_interface import Config
from vtests import helpers as vtest_helpers

##
## === stash
##


def test_stash_clears_working_tree(
    make_repo_: Path,
) -> None:
    (make_repo_ / "stashed.txt").write_text("uncommitted work")
    vtest_helpers.git(["add", "stashed.txt"], cwd=make_repo_)
    git_sync.cmd_stash_work(Config())
    status = vtest_helpers.git(["status", "--porcelain"], cwd=make_repo_).stdout.strip()
    assert status == ""


def test_unstash_restores_working_tree(
    make_repo_: Path,
) -> None:
    (make_repo_ / "stashed.txt").write_text("uncommitted work")
    vtest_helpers.git(["add", "stashed.txt"], cwd=make_repo_)
    git_sync.cmd_stash_work(Config())
    git_sync.cmd_unstash_work(Config())
    assert (make_repo_ / "stashed.txt").exists()


def test_stash_with_name_labels_entry(
    make_repo_: Path,
) -> None:
    (make_repo_ / "labelled.txt").write_text("labelled work")
    vtest_helpers.git(["add", "labelled.txt"], cwd=make_repo_)
    git_sync.cmd_stash_work(Config(), "my-label")
    stash_list = vtest_helpers.git(["stash", "list"], cwd=make_repo_).stdout
    assert "my-label" in stash_list


def test_unstash_by_name_pops_correct_entry(
    make_repo_: Path,
) -> None:
    ## stash file-a first, then file-b — stack order: work-b on top, work-a below
    (make_repo_ / "file-a.txt").write_text("work a")
    vtest_helpers.git(["add", "file-a.txt"], cwd=make_repo_)
    git_sync.cmd_stash_work(Config(), "work-a")
    (make_repo_ / "file-b.txt").write_text("work b")
    vtest_helpers.git(["add", "file-b.txt"], cwd=make_repo_)
    git_sync.cmd_stash_work(Config(), "work-b")
    ## pop work-a by name — should restore file-a, leave file-b stashed
    git_sync.cmd_unstash_work(Config(), "work-a")
    assert (make_repo_ / "file-a.txt").exists()
    assert not (make_repo_ / "file-b.txt").exists()


def test_unstash_unknown_name_kills(
    make_repo_: Path,
) -> None:
    with pytest.raises(SystemExit):
        git_sync.cmd_unstash_work(Config(), "nonexistent-label")


## } SCRIPT
