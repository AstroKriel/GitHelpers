## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import inspect

## third-party
import pytest

## personal
from huginn import manage_cli

## local
from git_helpers import user_interface

##
## === TEST SUITE
##


class TestCommandTable_Signatures:

    def test_every_cmd_fn_takes_exactly_its_args_by_keyword(
        self,
    ) -> None:
        for cmd in user_interface.COMMAND_LINE_TOOL.all_cmds:
            fn_params = inspect.signature(cmd.fn).parameters.values()
            fn_param_names = {_fn_param.name for _fn_param in fn_params}
            arg_param_names = {_arg.param_name for _arg in cmd.args}
            assert fn_param_names == arg_param_names, cmd.name
            for fn_param in fn_params:
                assert fn_param.kind is inspect.Parameter.KEYWORD_ONLY, f"{cmd.name}: {fn_param.name}"


class TestCommandTable_Help:

    def test_help_lists_every_cmd(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        try:
            manage_cli.run_cli(
                command_line_tool=user_interface.COMMAND_LINE_TOOL,
                argv=["--help"],
            )
        except SystemExit:
            pass
        help_text = capsys.readouterr().out
        for cmd in user_interface.COMMAND_LINE_TOOL.all_cmds:
            assert f"    {cmd.name} " in help_text


##
## === ENTRY POINT
##

## } U-TEST
