"""
Unit tests for shell_utils: logging helpers and dry-run behaviour.
"""

##
## === DEPENDENCIES
##

## stdlib
from unittest.mock import MagicMock, patch

## local
from git_helpers.shell_utils import (
    Config,
    bind_var,
    log_msg,
    log_outcome,
    log_step,
    query_cmd,
    run_cmd,
    run_cmd_and_capture_output,
)


##
## === LOGGING
##


def test_log_msg_writes_to_stderr(
    capsys,
):
    log_msg("hello")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "hello" in captured.err


def test_log_step_prefix(
    capsys,
):
    log_step("doing something")
    captured = capsys.readouterr()
    assert "STEP:" in captured.err
    assert "doing something" in captured.err


def test_log_outcome_prefix(
    capsys,
):
    log_outcome("it worked")
    captured = capsys.readouterr()
    assert "OUTCOME:" in captured.err
    assert "it worked" in captured.err


def test_bind_var_format(
    capsys,
):
    bind_var("branch_name", "main")
    captured = capsys.readouterr()
    assert "SET:" in captured.err
    assert "branch_name" in captured.err
    assert "main" in captured.err


##
## === DRY-RUN: run_cmd
##


def test_run_cmd_dry_run_skips_subprocess():
    config = Config(dry_run=True)
    with patch("subprocess.run") as mock_run:
        run_cmd(config, "git", "push")
        mock_run.assert_not_called()


def test_run_cmd_dry_run_logs_skipped(
    capsys,
):
    config = Config(dry_run=True)
    run_cmd(config, "git", "push")
    captured = capsys.readouterr()
    assert "dryrun" in captured.err
    assert "git push" in captured.err


def test_run_cmd_executes_when_not_dry_run():
    config = Config(dry_run=False)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        run_cmd(config, "git", "status")
        mock_run.assert_called_once()


def test_run_cmd_logs_command_before_executing(
    capsys,
):
    config = Config(dry_run=False)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        run_cmd(config, "git", "status")
        captured = capsys.readouterr()
        assert "git status" in captured.err


##
## === DRY-RUN: run_cmd_and_capture_output
##


def test_run_cmd_and_capture_dry_run_skips_subprocess():
    config = Config(dry_run=True)
    with patch("subprocess.run") as mock_run:
        run_cmd_and_capture_output(config, "git", "rev-list", "--count", "HEAD")
        mock_run.assert_not_called()


def test_run_cmd_and_capture_dry_run_returns_empty():
    config = Config(dry_run=True)
    result = run_cmd_and_capture_output(config, "git", "rev-list", "--count", "HEAD")
    assert result == ""


##
## === query_cmd always executes
##


def test_query_cmd_always_executes_regardless_of_dry_run():
    ## query_cmd has no config parameter — it always runs; this test confirms that
    ## by verifying subprocess.run is called even when a dry-run Config would suppress run_cmd
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="main\n", returncode=0)
        query_cmd("git", "branch", "--show-current")
        mock_run.assert_called_once()
