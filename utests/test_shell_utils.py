## { SCRIPT

##
## === DEPENDENCIES
##

## stdlib
from unittest.mock import MagicMock, patch

## local
from git_helpers import shell_interface

##
## === LOGGING
##


def test_log_msg_writes_to_stderr(
    capsys,
):
    shell_interface.log_msg("hello")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "hello" in captured.err


def test_log_step_prefix(
    capsys,
):
    shell_interface.log_step("doing something")
    captured = capsys.readouterr()
    assert "○" in captured.err
    assert "doing something" in captured.err


def test_log_outcome_prefix(
    capsys,
):
    shell_interface.log_outcome("it worked")
    captured = capsys.readouterr()
    assert "●" in captured.err
    assert "it worked" in captured.err


def test_bind_var_format(
    capsys,
):
    shell_interface.bind_var("branch_name", "main")
    captured = capsys.readouterr()
    assert "→" in captured.err
    assert "branch_name" in captured.err
    assert "main" in captured.err


def test_log_result_writes_to_stdout(
    capsys,
):
    shell_interface.log_result("all good")
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "●" in captured.out
    assert "all good" in captured.out


##
## === DRY-RUN: run_cmd
##


def test_run_cmd_dry_run_skips_subprocess():
    config = shell_interface.Config(dry_run=True)
    with patch("subprocess.run") as mock_run:
        shell_interface.run_cmd(config=config, cmd=["git", "push"])
        mock_run.assert_not_called()


def test_run_cmd_dry_run_logs_skipped(
    capsys,
):
    config = shell_interface.Config(dry_run=True)
    shell_interface.run_cmd(config=config, cmd=["git", "push"])
    captured = capsys.readouterr()
    assert "dryrun" in captured.err
    assert "git push" in captured.err


def test_run_cmd_executes_when_not_dry_run():
    config = shell_interface.Config(dry_run=False)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        shell_interface.run_cmd(config=config, cmd=["git", "status"])
        mock_run.assert_called_once()


def test_run_cmd_logs_command_before_executing(
    capsys,
):
    config = shell_interface.Config(dry_run=False)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        shell_interface.run_cmd(config=config, cmd=["git", "status"])
        captured = capsys.readouterr()
        assert "git status" in captured.err


##
## === DRY-RUN: run_cmd_and_capture_output
##


def test_run_cmd_and_capture_dry_run_skips_subprocess():
    config = shell_interface.Config(dry_run=True)
    with patch("subprocess.run") as mock_run:
        shell_interface.run_cmd_and_capture_output(config=config, cmd=["git", "rev-list", "--count", "HEAD"])
        mock_run.assert_not_called()


def test_run_cmd_and_capture_dry_run_returns_empty():
    config = shell_interface.Config(dry_run=True)
    result = shell_interface.run_cmd_and_capture_output(config=config, cmd=["git", "rev-list", "--count", "HEAD"])
    assert result == ""


##
## === query_cmd always executes
##


def test_query_cmd_always_executes_regardless_of_dry_run():
    ## query_cmd has no config parameter — it always runs; this test confirms that
    ## by verifying subprocess.run is called even when a dry-run Config would suppress run_cmd
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="main\n", returncode=0)
        shell_interface.query_cmd(cmd=["git", "branch", "--show-current"])
        mock_run.assert_called_once()


## } SCRIPT
