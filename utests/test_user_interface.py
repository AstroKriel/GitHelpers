## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import argparse

## local
from git_helpers import user_interface
from git_helpers.shell_interface import Config

##
## === TEST SUITE
##


class TestCliCommand_ArgMapping:

    def test_positional_arg_is_passed_to_fn(
        self,
    ) -> None:
        received: list[str] = []

        def fn(
            config: Config,
            branch_name: str,
        ) -> None:
            received.append(branch_name)

        _, cmd_details = user_interface.cli_command(
            cmd_name="test-cmd",
            cmd_fn=fn,
            cmd_args=[user_interface._CommandArg(arg_name="branch_name")],
        )
        ns = argparse.Namespace(dry_run=False, allow_dirty=False, branch_name="feature")
        cmd_details.handler(ns)
        assert received == ["feature"]

    def test_named_flag_is_passed_to_fn(
        self,
    ) -> None:
        ## regression: getattr(args, "--base") fails; must strip "--" to get args.base
        received: list[str | None] = []

        def fn(
            config: Config,
            base: str | None = None,
        ) -> None:
            received.append(base)

        _, cmd_details = user_interface.cli_command(
            cmd_name="test-cmd",
            cmd_fn=fn,
            cmd_args=[user_interface._CommandArg(arg_name="--base")],
        )
        ns = argparse.Namespace(dry_run=False, allow_dirty=False, base="development")
        cmd_details.handler(ns)
        assert received == ["development"]

    def test_named_flag_passes_none_when_not_set(
        self,
    ) -> None:
        received: list[str | None] = []

        def fn(
            config: Config,
            base: str | None = None,
        ) -> None:
            received.append(base)

        _, cmd_details = user_interface.cli_command(
            cmd_name="test-cmd",
            cmd_fn=fn,
            cmd_args=[user_interface._CommandArg(arg_name="--base")],
        )
        ns = argparse.Namespace(dry_run=False, allow_dirty=False, base=None)
        cmd_details.handler(ns)
        assert received == [None]

    def test_named_flag_and_positional_arg_together(
        self,
    ) -> None:
        received: list[str | None] = []

        def fn(
            config: Config,
            base: str | None,
            path: str | None,
        ) -> None:
            received.extend([base, path])

        _, cmd_details = user_interface.cli_command(
            cmd_name="test-cmd",
            cmd_fn=fn,
            cmd_args=[
                user_interface._CommandArg(arg_name="--base"),
                user_interface._CommandArg(
                    arg_name="path",
                    nargs="?",
                ),
            ],
        )
        ns = argparse.Namespace(dry_run=False, allow_dirty=False, base="main", path="src/foo.py")
        cmd_details.handler(ns)
        assert received == ["main", "src/foo.py"]


class TestMakeCommandGroup_SectionStamping:

    def test_stamps_section_title_on_every_command(
        self,
    ) -> None:
        def fn(
            config: Config,
        ) -> None:
            return None

        group = user_interface._make_command_group(
            section_title=user_interface._SectionTitle.STASHING,
            commands=[
                user_interface.cli_command(
                    cmd_name="alpha",
                    cmd_fn=fn,
                ),
                user_interface.cli_command(
                    cmd_name="beta",
                    cmd_fn=fn,
                ),
            ],
        )
        assert [details.section_title for _, details in group] == [
            user_interface._SectionTitle.STASHING,
            user_interface._SectionTitle.STASHING,
        ]

    def test_preserves_command_names_and_order(
        self,
    ) -> None:
        def fn(
            config: Config,
        ) -> None:
            return None

        group = user_interface._make_command_group(
            section_title=user_interface._SectionTitle.SYNCING,
            commands=[
                user_interface.cli_command(
                    cmd_name="alpha",
                    cmd_fn=fn,
                ),
                user_interface.cli_command(
                    cmd_name="beta",
                    cmd_fn=fn,
                ),
            ],
        )
        assert [cmd_name for cmd_name, _ in group] == ["alpha", "beta"]


##
## === ENTRY POINT
##

if __name__ == "__main__":
    import unittest

    _ = unittest.main()

## } U-TEST
