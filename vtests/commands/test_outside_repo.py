## { SCRIPT

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## third-party
import pytest

## personal
from huginn import cmd_args, manage_cli

## local
from git_helpers import user_interface

##
## === HELPERS
##

NON_REPO_COMMAND_NAMES = {
    "scan-repos",
    "set-global-config",
    "show-global-config",
}


def _list_repo_commands() -> list[manage_cli.Command]:
    all_commands = [
        _command
        for _command_group in user_interface.COMMAND_LINE_TOOL.cmd_groups
        for _command in _command_group.cmds
    ]
    return [_command for _command in all_commands if _command.name not in NON_REPO_COMMAND_NAMES]


def _build_required_argv(
    *,
    command: manage_cli.Command,
) -> list[str]:
    """Return argv for a command with a placeholder value for each required argument."""
    argv = [command.name]
    for _arg in command.args:
        if isinstance(_arg, cmd_args.PositionalArgument) and (not _arg.allowed_num_input_values.is_zero_allowed):
            argv.append("1")
        elif isinstance(_arg, cmd_args.NamedArgument) and _arg.is_required:
            argv.extend([f"--{_arg.long_arg_name}", "1"])
    return argv


##
## === TESTS
##


@pytest.mark.parametrize(
    "command",
    _list_repo_commands(),
    ids=lambda _command: _command.name,
)
def test_command_outside_a_repo_exits_with_a_clear_error(
    command: manage_cli.Command,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ## stop git from finding a repo in a parent of the temp directory
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exit_info:
        manage_cli.run_cli(
            command_line_tool=user_interface.COMMAND_LINE_TOOL,
            argv=_build_required_argv(command=command),
        )
    assert exit_info.value.code == 1
    assert "not inside a git repo" in capsys.readouterr().err


## } SCRIPT
