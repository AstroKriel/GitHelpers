## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
from unittest.mock import MagicMock, patch

## third-party
import pytest

## local
from git_helpers import shell_interface

##
## === TEST SUITE
##


class TestLogMsg_Output:

    def test_writes_to_stderr(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.log_msg("hello")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "hello" in captured.err


class TestLogStep_Output:

    def test_includes_prefix_and_message(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.log_step("doing something")
        captured = capsys.readouterr()
        assert "○" in captured.err
        assert "doing something" in captured.err


class TestLogOutcome_Output:

    def test_includes_prefix_and_message(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.log_outcome("it worked")
        captured = capsys.readouterr()
        assert "●" in captured.err
        assert "it worked" in captured.err


class TestBindVar_Output:

    def test_includes_arrow_and_values(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.bind_var("branch_name", "main")
        captured = capsys.readouterr()
        assert "→" in captured.err
        assert "branch_name" in captured.err
        assert "main" in captured.err


class TestLogResult_Output:

    def test_writes_to_stdout(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.log_result("all good")
        captured = capsys.readouterr()
        assert captured.err == ""
        assert "●" in captured.out
        assert "all good" in captured.out


class TestRunCmd_DryRun:

    def test_skips_subprocess(
        self,
    ) -> None:
        config = shell_interface.Config(dry_run=True)
        with patch("subprocess.run") as mock_run:
            shell_interface.run_cmd(config=config, cmd=["git", "push"])
            mock_run.assert_not_called()

    def test_logs_skipped(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        config = shell_interface.Config(dry_run=True)
        shell_interface.run_cmd(config=config, cmd=["git", "push"])
        captured = capsys.readouterr()
        assert "dryrun" in captured.err
        assert "git push" in captured.err

    def test_executes_when_not_dry_run(
        self,
    ) -> None:
        config = shell_interface.Config(dry_run=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            shell_interface.run_cmd(config=config, cmd=["git", "status"])
            mock_run.assert_called_once()

    def test_logs_command_before_executing(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        config = shell_interface.Config(dry_run=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            shell_interface.run_cmd(config=config, cmd=["git", "status"])
            captured = capsys.readouterr()
            assert "git status" in captured.err


class TestRunCmdAndCaptureOutput_DryRun:

    def test_skips_subprocess(
        self,
    ) -> None:
        config = shell_interface.Config(dry_run=True)
        with patch("subprocess.run") as mock_run:
            _ = shell_interface.run_cmd_and_capture_output(
                config=config,
                cmd=["git", "rev-list", "--count", "HEAD"],
            )
            mock_run.assert_not_called()

    def test_returns_empty_string(
        self,
    ) -> None:
        config = shell_interface.Config(dry_run=True)
        result = shell_interface.run_cmd_and_capture_output(
            config=config,
            cmd=["git", "rev-list", "--count", "HEAD"],
        )
        assert result == ""


class TestQueryCmd_Behaviour:

    def test_always_executes_regardless_of_dry_run(
        self,
    ) -> None:
        ## query_cmd has no config parameter — it always runs; this test confirms that
        ## by verifying subprocess.run is called even when a dry-run Config would suppress run_cmd
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="main\n", returncode=0)
            _ = shell_interface.query_cmd(cmd=["git", "branch", "--show-current"])
            mock_run.assert_called_once()


## } U-TEST
