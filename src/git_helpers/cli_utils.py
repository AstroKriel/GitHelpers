"""
Command-line interface: subcommand registry and entry point.
"""

##
## === DEPENDENCIES
##

## stdlib
import argparse
import subprocess
import sys
from collections.abc import Callable
from typing import Any

## local
from git_helpers import git_cmds, shell_utils

##
## === COMMAND LINE INTERFACE
##


def cli_command(
    cmd_name: str,
    cmd_fn: Callable[..., Any],
    cmd_help: str = "",
    cmd_args: list[tuple[str, dict[str, Any]]] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build a (name, entry) pair for COMMANDS; handler is auto-generated from cmd_args."""
    arg_specs: list[tuple[str, dict[str, Any]]] = cmd_args or []

    ## build Config from global flags, then pass it as the first positional arg to cmd_fn
    def handler(
        args: argparse.Namespace,
    ) -> Any:
        config = shell_utils.Config(
            dry_run=args.dry_run,
            allow_dirty=args.allow_dirty,
        )
        return cmd_fn(
            config,
            *[getattr(args, arg_name) for arg_name, _ in arg_specs],
        )

    return (
        cmd_name,
        {
            "help": cmd_help,
            "arg_specs": arg_specs,
            "handler": handler,
        },
    )


## maps each CLI subcommand name to an entry dict with its arg specs and handler
COMMANDS: dict[str, dict[str, Any]] = dict(
    [
        cli_command(
            cmd_name="set-global-config",
            cmd_fn=git_cmds.cmd_set_global_config,
            cmd_help="write FF-first merge defaults + rerere to ~/.gitconfig",
        ),
        cli_command(
            cmd_name="show-global-config",
            cmd_fn=git_cmds.show_global_config,
            cmd_help="print current values of the git settings this tool manages",
        ),
        cli_command(
            cmd_name="is-detached",
            cmd_fn=git_cmds.check_is_detached,
            cmd_help="exit 0 if HEAD is detached, 1 if on a branch (for shell conditionals)",
        ),
        cli_command(
            cmd_name="show-upstream",
            cmd_fn=git_cmds.show_upstream,
            cmd_help="show the current branch, its upstream ref, and the latest upstream commit",
        ),
        cli_command(
            cmd_name="branches-status",
            cmd_fn=git_cmds.show_branches_status,
            cmd_help="fetch, then list all branches with upstream and ahead/behind counts",
        ),
        cli_command(
            cmd_name="ahead-behind",
            cmd_fn=git_cmds.show_ahead_behind,
            cmd_help="print how many commits ahead/behind the current branch is vs its upstream",
        ),
        cli_command(
            cmd_name="unpulled-commits",
            cmd_fn=git_cmds.show_unpulled_commits,
            cmd_help="list commits on upstream not yet pulled locally",
        ),
        cli_command(
            cmd_name="local-remotes",
            cmd_fn=git_cmds.show_local_remotes,
            cmd_help="list all configured remotes and their URLs",
        ),
        cli_command(
            cmd_name="show-recent-commits",
            cmd_fn=git_cmds.show_recent_commits,
            cmd_help="print the most recent N commits on the current branch (default: 20)",
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
            cmd_fn=git_cmds.show_submodules_status,
            cmd_help="show SHA and init status of each submodule",
        ),
        cli_command(
            cmd_name="rename-last-commit",
            cmd_fn=git_cmds.cmd_rename_last_commit,
            cmd_help="amend the most recent commit message (rewrites history)",
            cmd_args=[(
                "message",
                {
                    "nargs": "+",
                },
            )],
        ),
        cli_command(
            cmd_name="delete-local-branch",
            cmd_fn=git_cmds.cmd_delete_local_branch,
            cmd_help="safely delete a local branch (refuses if unmerged)",
            cmd_args=[("branch_name", {})],
        ),
        cli_command(
            cmd_name="prune-gone-locals",
            cmd_fn=git_cmds.cmd_prune_gone_locals,
            cmd_help="delete local branches whose remote counterpart has been deleted",
        ),
        cli_command(
            cmd_name="prune-merged-locals",
            cmd_fn=git_cmds.cmd_prune_merged_locals,
            cmd_help="delete local branches fully merged into base (default: remote default branch)",
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            cmd_name="cleanup-local-branches",
            cmd_fn=git_cmds.cmd_cleanup_local_branches,
            cmd_help="run prune-gone-locals then prune-merged-locals in sequence",
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            cmd_name="track-remote-branch",
            cmd_fn=git_cmds.cmd_track_remote_branch,
            cmd_help="create a local branch tracking an existing remote branch and check it out",
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
            cmd_fn=git_cmds.cmd_create_branch_from_default,
            cmd_help="cut a new branch from the remote default branch and push it",
            cmd_args=[(
                "new_branch_name",
                {},
            )],
        ),
        cli_command(
            cmd_name="create-branch-from-remote",
            cmd_fn=git_cmds.cmd_create_branch_from_remote,
            cmd_help="cut a new branch from an explicit remote ref and push it",
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
            cmd_fn=git_cmds.cmd_push,
            cmd_help="push current branch; sets upstream automatically if not already configured",
            cmd_args=[(
                "extra_args",
                {
                    "nargs": "*",
                },
            )],
        ),
        cli_command(
            cmd_name="sync-branch",
            cmd_fn=git_cmds.cmd_sync_branch,
            cmd_help="pull/merge with --ff against upstream or an explicit remote base ref",
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            cmd_name="self-check",
            cmd_fn=git_cmds.check_self,
            cmd_help="verify that git is available on PATH",
        ),
    ],
)


def main() -> None:
    """Parse arguments and dispatch to the appropriate command function."""
    arg_parser = argparse.ArgumentParser(
        description="Git workflow helpers",
    )
    arg_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="print commands without executing them",
    )
    arg_parser.add_argument(
        "--allow-dirty",
        action="store_true",
        default=False,
        help="skip the clean worktree check",
    )
    sub_parsers = arg_parser.add_subparsers(
        dest="cmd",  # the chosen subcommand name: parse_args().cmd
        required=True,
        metavar="<command>",
    )
    ## register every subcommand and its positional args in one pass over COMMANDS
    for cmd_name, entry in COMMANDS.items():
        subparser = sub_parsers.add_parser(cmd_name, help=entry["help"])
        for arg_name, kwargs in entry["arg_specs"]:
            subparser.add_argument(arg_name, **kwargs)
    args = arg_parser.parse_args()
    try:
        COMMANDS[args.cmd]["handler"](args)
    except subprocess.CalledProcessError as proc_error:
        sys.exit(proc_error.returncode)
