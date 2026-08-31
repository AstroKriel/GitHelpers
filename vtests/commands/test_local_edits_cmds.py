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
from git_helpers.commands import git_local_edits
from git_helpers.shell_interface import Config
from vtests import helpers as vtest_helpers

##
## === ignore-local-edits / unignore-local-edits
##


def test_ignore_hides_local_edit(
    make_repo_: Path,
) -> None:
    tracked = make_repo_ / "tracked.txt"
    tracked.write_text("original")
    vtest_helpers.git(["add", "tracked.txt"], cwd=make_repo_)
    vtest_helpers.git(["commit", "-m", "add tracked.txt"], cwd=make_repo_)
    git_local_edits.cmd_ignore_local_edits(Config(), ["tracked.txt"])
    tracked.write_text("edited locally")
    status = vtest_helpers.git(["status", "--porcelain"], cwd=make_repo_).stdout.strip()
    assert status == ""


def test_unignore_reveals_local_edit(
    make_repo_: Path,
) -> None:
    tracked = make_repo_ / "tracked.txt"
    tracked.write_text("original")
    vtest_helpers.git(["add", "tracked.txt"], cwd=make_repo_)
    vtest_helpers.git(["commit", "-m", "add tracked.txt"], cwd=make_repo_)
    git_local_edits.cmd_ignore_local_edits(Config(), ["tracked.txt"])
    tracked.write_text("edited locally")
    git_local_edits.cmd_unignore_local_edits(Config(), ["tracked.txt"])
    status = vtest_helpers.git(["status", "--porcelain"], cwd=make_repo_).stdout.strip()
    assert status == "M tracked.txt"


def test_ignore_accepts_multiple_paths(
    make_repo_: Path,
) -> None:
    tracked_a = make_repo_ / "a.txt"
    tracked_b = make_repo_ / "b.txt"
    tracked_a.write_text("a")
    tracked_b.write_text("b")
    vtest_helpers.git(["add", "a.txt", "b.txt"], cwd=make_repo_)
    vtest_helpers.git(["commit", "-m", "add a.txt and b.txt"], cwd=make_repo_)
    git_local_edits.cmd_ignore_local_edits(Config(), ["a.txt", "b.txt"])
    tracked_a.write_text("edited a")
    tracked_b.write_text("edited b")
    status = vtest_helpers.git(["status", "--porcelain"], cwd=make_repo_).stdout.strip()
    assert status == ""


def test_ignore_untracked_path_fails(
    make_repo_: Path,
) -> None:
    (make_repo_ / "untracked.txt").write_text("never added")
    ## git refuses to mark an untracked path — raises CalledProcessError
    with pytest.raises(subprocess.CalledProcessError):
        git_local_edits.cmd_ignore_local_edits(Config(), ["untracked.txt"])


## } SCRIPT
