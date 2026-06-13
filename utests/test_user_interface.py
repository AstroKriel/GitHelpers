## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import argparse

## third-party
import pytest

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
            cmd_args=[("branch_name", {})],
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
            cmd_args=[("--base", {"default": None})],
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
            cmd_args=[("--base", {"default": None})],
        )
        ns = argparse.Namespace(dry_run=False, allow_dirty=False, base=None)
        cmd_details.handler(ns)
        assert received == [None]

    def test_named_flag_and_positional_arg_together(
        self,
    ) -> None:
        received: list = []

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
                ("--base", {"default": None}),
                ("path", {"nargs": "?", "default": None}),
            ],
        )
        ns = argparse.Namespace(dry_run=False, allow_dirty=False, base="main", path="src/foo.py")
        cmd_details.handler(ns)
        assert received == ["main", "src/foo.py"]


##
## === ENTRY POINT
##

if __name__ == "__main__":
    import unittest

    _ = unittest.main()

## } U-TEST
