## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

## third-party
from rich.console import Console

## local
from git_helpers import (
    git_config,
    git_inspection,
    git_branches,
    git_submodules,
    git_sync,
    shell_interface,
)

##
## === COMMAND LINE INTERFACE
##


class _HelpFormatter(argparse.HelpFormatter):

    def __init__(self, prog: str) -> None:
        ## change the width of columns, so command names fit in the left column
        super().__init__(
            prog,
            width=120,  # first colum
            max_help_position=100,  # second column
        )
        self._action_max_length = 30


@dataclass(frozen=True)
class CommandDetails:
    help: str
    cmd_args: list[tuple[str, dict[str, Any]]]
    handler: Callable[[argparse.Namespace], Any]
    section: str
    is_hidden: bool


def cli_command(
    section: str = "",
    *,
    cmd_name: str,
    cmd_fn: Callable[..., Any],
    cmd_help: str = "",
    cmd_args: list[tuple[str, dict[str, Any]]] | None = None,
    is_hidden: bool = False,
) -> tuple[str, CommandDetails]:
    """Build a (name, cmd_details) pair for COMMANDS; handler is auto-generated from cmd_args."""
    cmd_args = cmd_args or []

    ## build Config from global flags, then pass it as the first positional arg to cmd_fn
    def handler(
        args: argparse.Namespace,
    ) -> Any:
        config = shell_interface.Config(
            dry_run=args.dry_run,
            allow_dirty=args.allow_dirty,
        )
        return cmd_fn(
            config,
            *[getattr(args, arg_name) for arg_name, _ in cmd_args],
        )

    return (
        cmd_name,
        CommandDetails(
            help=cmd_help,
            cmd_args=cmd_args,
            handler=handler,
            section=section,
            is_hidden=is_hidden,
        ),
    )


class _GroupedHelpAction(argparse.Action):
    """Replace the default --help with a Rich-formatted, section-grouped command listing."""

    def __init__(
        self,
        option_strings: list[str],
        dest: str = argparse.SUPPRESS,
        default: str = argparse.SUPPRESS,
        help: str = "show this help message and exit",
    ) -> None:
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
        )

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        console = Console()
        console.print()
        console.print("[bold]git_helpers[/bold]: git workflow helpers")
        console.print()
        console.print("[dim]usage:[/dim] git_helpers \\[--dry-run] \\[--allow-dirty] <command> \\[args]")
        console.print()
        ## iterate COMMANDS in order, printing a header each time the section changes.
        current_section = None
        for cmd_name, cmd_details in COMMANDS.items():
            if cmd_details.is_hidden:
                continue
            if cmd_details.section != current_section:
                if current_section is not None:
                    console.print()
                console.print(f"[bold]{cmd_details.section}[/bold]")
                current_section = cmd_details.section
            console.print(f"  [cyan]{cmd_name:<30}[/cyan]{cmd_details.help}")
        console.print()
        console.print("[bold]Global flags[/bold]")
        console.print(f"  [cyan]{'--dry-run':<30}[/cyan]print commands without executing them")
        console.print(f"  [cyan]{'--allow-dirty':<30}[/cyan]skip the clean worktree check")
        console.print()
        parser.exit()


## maps each CLI subcommand name to an cmd_details dict with its arg specs and handler
COMMANDS: dict[str, CommandDetails] = dict(
    [
        ## global configuration
        cli_command(
            section="Global configuration",
            cmd_name="set-global-config",
            cmd_fn=git_config.cmd_set_global_config,
            cmd_help="set sensible merge rules in ~/.gitconfig (fast-forward preferred, rerere enabled)",
        ),
        cli_command(
            section="Global configuration",
            cmd_name="show-global-config",
            cmd_fn=git_config.show_global_config,
            cmd_help="show the current values of the git settings this tool manages",
        ),
        ## inspection
        cli_command(
            section="Inspection",
            cmd_name="show-upstream-state",
            cmd_fn=git_inspection.show_upstream_state,
            cmd_help="show which remote branch the current branch is tracking and its latest commit",
        ),
        cli_command(
            section="Inspection",
            cmd_name="show-branches-status",
            cmd_fn=git_inspection.show_branches_status,
            cmd_help="see all local branches and whether they're ahead or behind their remote (fetches first)",
        ),
        cli_command(
            section="Inspection",
            cmd_name="count-ahead-behind",
            cmd_fn=git_inspection.count_ahead_behind,
            cmd_help="show how many commits the current branch is ahead of and behind its upstream",
        ),
        cli_command(
            section="Inspection",
            cmd_name="show-unpulled-commits",
            cmd_fn=git_inspection.show_unpulled_commits,
            cmd_help="list commits on the remote that haven't been pulled yet",
        ),
        cli_command(
            section="Inspection",
            cmd_name="show-recent-commits",
            cmd_fn=git_inspection.show_recent_commits,
            cmd_help="show the last N commits on the current branch (default: 20)",
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
            section="Inspection",
            cmd_name="show-local-remotes",
            cmd_fn=git_inspection.show_local_remotes,
            cmd_help="list all configured remotes and their URLs",
        ),
        cli_command(
            section="Inspection",
            cmd_name="show-submodules-status",
            cmd_fn=git_inspection.show_submodules_status,
            cmd_help="show the current state of each submodule (commit SHA and init status)",
        ),
        ## branch management
        cli_command(
            section="Branch management",
            cmd_name="create-branch-from-default",
            cmd_fn=git_branches.cmd_create_branch_from_default,
            cmd_help="create and push a new branch from the remote default (e.g. origin/main)",
            cmd_args=[(
                "new_branch_name",
                {},
            )],
        ),
        cli_command(
            section="Branch management",
            cmd_name="create-branch-from-remote",
            cmd_fn=git_branches.cmd_create_branch_from_remote,
            cmd_help="create and push a new branch from a specific remote branch",
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
            section="Branch management",
            cmd_name="track-remote-branch",
            cmd_fn=git_branches.cmd_track_remote_branch,
            cmd_help="create a local tracking branch for an existing remote branch and check it out",
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
            section="Branch management",
            cmd_name="delete-local-branch",
            cmd_fn=git_branches.cmd_delete_local_branch,
            cmd_help="delete a local branch safely (refuses if it has unmerged commits)",
            cmd_args=[("branch_name", {})],
        ),
        cli_command(
            section="Branch management",
            cmd_name="prune-gone-locals",
            cmd_fn=git_branches.cmd_prune_gone_locals,
            cmd_help="delete local branches whose remote counterpart has been deleted",
        ),
        cli_command(
            section="Branch management",
            cmd_name="prune-merged-locals",
            cmd_fn=git_branches.cmd_prune_merged_locals,
            cmd_help="delete local branches whose commits are already in the base branch",
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            section="Branch management",
            cmd_name="cleanup-local-branches",
            cmd_fn=git_branches.cmd_cleanup_local_branches,
            cmd_help="delete all gone and merged local branches in one step",
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
        ),
        ## submodule management
        cli_command(
            section="Submodule management",
            cmd_name="update-submodules",
            cmd_fn=git_submodules.cmd_update_submodules,
            cmd_help="update all submodules to their latest commit on the tracked branch",
        ),
        cli_command(
            section="Submodule management",
            cmd_name="fix-submodule",
            cmd_fn=git_submodules.cmd_fix_submodule,
            cmd_help=
            "repair a submodule in detached HEAD state (auto-detects branch, pulls, updates parent pointer)",
            cmd_args=[
                ("submodule_path", {}),
                (
                    "branch",
                    {
                        "nargs": "?",
                        "default": None,
                        "metavar": "branch",
                    },
                ),
            ],
        ),
        cli_command(
            section="Submodule management",
            cmd_name="add-submodule",
            cmd_fn=git_submodules.cmd_add_submodule,
            cmd_help="add a new submodule tracking its default branch and commit the result",
            cmd_args=[
                ("url", {}),
                ("local_name", {}),
                (
                    "branch",
                    {
                        "nargs": "?",
                        "default": None,
                        "metavar": "branch",
                    },
                ),
            ],
        ),
        ## syncing and history
        cli_command(
            section="Syncing and history",
            cmd_name="push",
            cmd_fn=git_sync.cmd_push,
            cmd_help="push the current branch; sets the upstream automatically if it's a new branch",
            cmd_args=[(
                "extra_args",
                {
                    "nargs": "*",
                },
            )],
        ),
        cli_command(
            section="Syncing and history",
            cmd_name="sync-branch",
            cmd_fn=git_sync.cmd_sync_branch,
            cmd_help="bring the current branch up to date with its upstream (or an explicit remote branch)",
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            section="Syncing and history",
            cmd_name="stash-work",
            cmd_fn=git_sync.cmd_stash_work,
            cmd_help="temporarily save uncommitted work so you can switch context; optionally label it",
            cmd_args=[(
                "name",
                {
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            section="Syncing and history",
            cmd_name="unstash-work",
            cmd_fn=git_sync.cmd_unstash_work,
            cmd_help="restore the most recently stashed work, or a specific stash by name",
            cmd_args=[(
                "name",
                {
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            section="Syncing and history",
            cmd_name="amend-last-commit",
            cmd_fn=git_sync.cmd_amend_last_commit,
            cmd_help="fold staged changes into the last commit; optionally update the message too",
            cmd_args=[(
                "msg",
                {
                    "nargs": "*",
                },
            )],
        ),
        cli_command(
            section="Syncing and history",
            cmd_name="rename-last-commit",
            cmd_fn=git_sync.cmd_rename_last_commit,
            cmd_help="update the message of the last commit without changing its content (rewrites history)",
            cmd_args=[(
                "msg",
                {
                    "nargs": "+",
                },
            )],
        ),
        ## hidden (not promoted) utilities
        cli_command(
            cmd_name="self-check",
            cmd_fn=git_config.check_self,
            cmd_help="verify that git is available on PATH",
            is_hidden=True,
        ),
        cli_command(
            cmd_name="is-detached",
            cmd_fn=git_inspection.check_is_detached,
            cmd_help="exit 0 if HEAD is detached, 1 if on a branch (for shell conditionals)",
            is_hidden=True,
        ),
    ],
)


def main() -> None:
    """Parse arguments and dispatch to the appropriate command function."""
    arg_parser = argparse.ArgumentParser(
        description="Git workflow helpers",
        formatter_class=_HelpFormatter,
        add_help=False,
    )
    arg_parser.add_argument(
        "-h",
        "--help",
        action=_GroupedHelpAction,
        default=argparse.SUPPRESS,
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
    for cmd_name, cmd_details in COMMANDS.items():
        subparser = sub_parsers.add_parser(cmd_name, help=cmd_details.help)
        for arg_name, arg_kwargs in cmd_details.cmd_args:
            subparser.add_argument(arg_name, **arg_kwargs)
    args = arg_parser.parse_args()
    try:
        COMMANDS[args.cmd].handler(args)
    except subprocess.CalledProcessError as proc_error:
        sys.exit(proc_error.returncode)


## } MODULE
