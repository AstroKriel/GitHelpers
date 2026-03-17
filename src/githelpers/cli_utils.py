"""
Command-line interface: subcommand registry and entry point.
"""

import argparse
import subprocess
import sys

from githelpers import run_cmds

##
## === COMMAND LINE INTERFACE
##


def cli_command(cmd_name, cmd_fn, cmd_args=None):
    """Build a (name, entry) pair for COMMANDS; handler is auto-generated from cmd_args."""
    arg_specs = cmd_args or []

    ## extract each arg's value from the parsed namespace by name, then pass positionally to cmd_fn
    def handler(args):
        return cmd_fn(*[getattr(args, arg_name) for arg_name, _arg_kwargs in arg_specs])

    return (
        cmd_name,
        {
            "arg_specs": arg_specs,
            "handler": handler,
        },
    )


## maps each CLI subcommand name to an entry dict with its arg specs and handler
COMMANDS = dict(
    [
        cli_command(
            cmd_name="set-global-config",
            cmd_fn=run_cmds.set_global_config,
        ),
        cli_command(
            cmd_name="show-global-config",
            cmd_fn=run_cmds.show_global_config,
        ),
        cli_command(
            cmd_name="is-detached",
            cmd_fn=run_cmds.cmd_is_detached,
        ),
        cli_command(
            cmd_name="show-upstream",
            cmd_fn=run_cmds.cmd_show_upstream,
        ),
        cli_command(
            cmd_name="branches-status",
            cmd_fn=run_cmds.cmd_branches_status,
        ),
        cli_command(
            cmd_name="ahead-behind",
            cmd_fn=run_cmds.cmd_ahead_behind,
        ),
        cli_command(
            cmd_name="unpulled-commits",
            cmd_fn=run_cmds.cmd_unpulled_commits,
        ),
        cli_command(
            cmd_name="local-remotes",
            cmd_fn=run_cmds.cmd_local_remotes,
        ),
        cli_command(
            cmd_name="show-recent-commits",
            cmd_fn=run_cmds.cmd_show_recent_commits,
            cmd_args=[(
                "max_entries",
                {
                    "nargs": "?",
                    "type": int,
                    "default": 20,
                },
            )],
        ),
        cli_command(
            cmd_name="submodules-status",
            cmd_fn=run_cmds.cmd_submodules_status,
        ),
        cli_command(
            cmd_name="rename-last-commit",
            cmd_fn=run_cmds.cmd_rename_last_commit,
            cmd_args=[(
                "message",
                {
                    "nargs": "+",
                },
            )],
        ),
        cli_command(
            cmd_name="delete-local-branch",
            cmd_fn=run_cmds.cmd_delete_local_branch,
            cmd_args=[("branch_name", {})],
        ),
        cli_command(
            cmd_name="prune-gone-locals",
            cmd_fn=run_cmds.cmd_prune_gone_locals,
        ),
        cli_command(
            cmd_name="prune-merged-locals",
            cmd_fn=run_cmds.cmd_prune_merged_locals,
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            cmd_name="cleanup-local-branches",
            cmd_fn=run_cmds.cmd_cleanup_local_branches,
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            cmd_name="track-remote-branch",
            cmd_fn=run_cmds.cmd_track_remote_branch,
            cmd_args=[
                (
                    "remote_branch",
                    {},
                ),
                (
                    "local_branch",
                    {
                        "nargs": "?",
                    },
                ),
            ],
        ),
        cli_command(
            cmd_name="create-branch-from-default",
            cmd_fn=run_cmds.cmd_create_branch_from_default,
            cmd_args=[(
                "new_branch_name",
                {},
            )],
        ),
        cli_command(
            cmd_name="create-branch-from-remote",
            cmd_fn=run_cmds.cmd_create_branch_from_remote,
            cmd_args=[
                (
                    "new_branch_name",
                    {},
                ),
                (
                    "start_ref",
                    {},
                ),
            ],
        ),
        cli_command(
            cmd_name="push",
            cmd_fn=run_cmds.cmd_push,
            cmd_args=[(
                "extra_args",
                {
                    "nargs": "*",
                },
            )],
        ),
        cli_command(
            cmd_name="sync-branch",
            cmd_fn=run_cmds.cmd_sync_branch,
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            cmd_name="self-check",
            cmd_fn=run_cmds.cmd_self_check,
        ),
    ],
)


def main() -> None:
    """Parse arguments and dispatch to the appropriate command function."""
    arg_parser = argparse.ArgumentParser(
        description="Git workflow helpers",
    )
    sub_parsers = arg_parser.add_subparsers(
        dest="cmd",  # the chosen subcommand name: parse_args().cmd
        required=True,
    )
    ## register every subcommand and its positional args in one pass over COMMANDS
    for cmd_name, entry in COMMANDS.items():
        subparser = sub_parsers.add_parser(cmd_name)
        for arg_name, kwargs in entry["arg_specs"]:
            subparser.add_argument(arg_name, **kwargs)
    args = arg_parser.parse_args()
    try:
        COMMANDS[args.cmd]["handler"](args)
    except subprocess.CalledProcessError as proc_error:
        sys.exit(proc_error.returncode)
