## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from typing import Any

## third-party
from rich.console import Console

## local
from git_helpers import git_utils, shell_utils

##
## === COMMAND LINE INTERFACE
##


class _HelpFormatter(argparse.HelpFormatter):

    def __init__(self, prog: str) -> None:
        ## pre-set _action_max_length so all subcommand names fit in the left column;
        ## argparse's default computation underestimates the threshold.
        super().__init__(
            prog,
            max_help_position=100,
            width=120,
        )
        self._action_max_length = 30


def cli_command(
    cmd_name: str,
    cmd_fn: Callable[..., Any],
    cmd_help: str = "",
    cmd_args: list[tuple[str, dict[str, Any]]] | None = None,
    section: str = "",
    is_hidden: bool = False,
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
            "section": section,
            "is_hidden": is_hidden,
        },
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
        for name, entry in COMMANDS.items():
            if entry.get("is_hidden"):
                continue
            entry_section = entry.get("section", "")
            if entry_section != current_section:
                if current_section is not None:
                    console.print()
                console.print(f"[bold]{entry_section}[/bold]")
                current_section = entry_section
            console.print(f"  [cyan]{name:<30}[/cyan]{entry['help']}")
        console.print()
        console.print("[bold]Global flags[/bold]")
        console.print(f"  [cyan]{'--dry-run':<30}[/cyan]print commands without executing them")
        console.print(f"  [cyan]{'--allow-dirty':<30}[/cyan]skip the clean worktree check")
        console.print()
        parser.exit()


## maps each CLI subcommand name to an entry dict with its arg specs and handler
COMMANDS: dict[str, dict[str, Any]] = dict(
    [
        ## --- global configuration ---
        cli_command(
            cmd_name="set-global-config",
            cmd_fn=git_utils.cmd_set_global_config,
            cmd_help="write FF-first merge defaults + rerere to ~/.gitconfig",
            section="Global configuration",
        ),
        cli_command(
            cmd_name="show-global-config",
            cmd_fn=git_utils.show_global_config,
            cmd_help="print current values of the git settings this tool manages",
            section="Global configuration",
        ),
        ## --- inspection ---
        cli_command(
            cmd_name="show-upstream-state",
            cmd_fn=git_utils.show_upstream_state,
            cmd_help="show the current branch, its upstream ref, and the latest upstream commit",
            section="Inspection",
        ),
        cli_command(
            cmd_name="show-branches-status",
            cmd_fn=git_utils.show_branches_status,
            cmd_help="fetch, then list all branches with upstream and ahead/behind counts",
            section="Inspection",
        ),
        cli_command(
            cmd_name="count-ahead-behind",
            cmd_fn=git_utils.count_ahead_behind,
            cmd_help="print how many commits ahead/behind the current branch is vs its upstream",
            section="Inspection",
        ),
        cli_command(
            cmd_name="show-unpulled-commits",
            cmd_fn=git_utils.show_unpulled_commits,
            cmd_help="list commits on upstream not yet pulled locally",
            section="Inspection",
        ),
        cli_command(
            cmd_name="show-recent-commits",
            cmd_fn=git_utils.show_recent_commits,
            cmd_help="print the most recent N commits on the current branch (default: 20)",
            cmd_args=[(
                "max_entries",
                {
                    "nargs": "?",
                    "type": int,
                    "default": 20,
                },
            )],
            section="Inspection",
        ),
        cli_command(
            cmd_name="show-local-remotes",
            cmd_fn=git_utils.show_local_remotes,
            cmd_help="list all configured remotes and their URLs",
            section="Inspection",
        ),
        cli_command(
            cmd_name="show-submodules-status",
            cmd_fn=git_utils.show_submodules_status,
            cmd_help="show SHA and init status of each submodule",
            section="Inspection",
        ),
        ## --- branch management ---
        cli_command(
            cmd_name="create-branch-from-default",
            cmd_fn=git_utils.cmd_create_branch_from_default,
            cmd_help="cut a new branch from the remote default branch and push it",
            cmd_args=[(
                "new_branch_name",
                {},
            )],
            section="Branch management",
        ),
        cli_command(
            cmd_name="create-branch-from-remote",
            cmd_fn=git_utils.cmd_create_branch_from_remote,
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
            section="Branch management",
        ),
        cli_command(
            cmd_name="track-remote-branch",
            cmd_fn=git_utils.cmd_track_remote_branch,
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
            section="Branch management",
        ),
        cli_command(
            cmd_name="delete-local-branch",
            cmd_fn=git_utils.cmd_delete_local_branch,
            cmd_help="safely delete a local branch (refuses if unmerged)",
            cmd_args=[("branch_name", {})],
            section="Branch management",
        ),
        cli_command(
            cmd_name="prune-gone-locals",
            cmd_fn=git_utils.cmd_prune_gone_locals,
            cmd_help="delete local branches whose remote counterpart has been deleted",
            section="Branch management",
        ),
        cli_command(
            cmd_name="prune-merged-locals",
            cmd_fn=git_utils.cmd_prune_merged_locals,
            cmd_help="delete local branches fully merged into base (default: remote default branch)",
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
            section="Branch management",
        ),
        cli_command(
            cmd_name="cleanup-local-branches",
            cmd_fn=git_utils.cmd_cleanup_local_branches,
            cmd_help="run prune-gone-locals then prune-merged-locals in sequence",
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
            section="Branch management",
        ),
        ## --- submodule management ---
        cli_command(
            cmd_name="update-submodules",
            cmd_fn=git_utils.cmd_update_submodules,
            cmd_help="pull latest commits for all submodules from their tracked branches",
            section="Submodule management",
        ),
        cli_command(
            cmd_name="fix-submodule",
            cmd_fn=git_utils.cmd_fix_submodule,
            cmd_help="repair a submodule in detached HEAD: checkout main, pull, bump parent pointer",
            cmd_args=[("submodule_path", {})],
            section="Submodule management",
        ),
        cli_command(
            cmd_name="add-submodule",
            cmd_fn=git_utils.cmd_add_submodule,
            cmd_help="add a submodule tracking main, and commit .gitmodules + pointer",
            cmd_args=[
                ("url", {}),
                ("local_name", {}),
            ],
            section="Submodule management",
        ),
        ## --- syncing and history ---
        cli_command(
            cmd_name="push",
            cmd_fn=git_utils.cmd_push,
            cmd_help="push current branch; sets upstream automatically if not already configured",
            cmd_args=[(
                "extra_args",
                {
                    "nargs": "*",
                },
            )],
            section="Syncing and history",
        ),
        cli_command(
            cmd_name="sync-branch",
            cmd_fn=git_utils.cmd_sync_branch,
            cmd_help="pull/merge with --ff against upstream or an explicit remote base ref",
            cmd_args=[(
                "base_name",
                {
                    "nargs": "?",
                },
            )],
            section="Syncing and history",
        ),
        cli_command(
            cmd_name="stash-work",
            cmd_fn=git_utils.cmd_stash_work,
            cmd_help="stash uncommitted work; optionally label it with a name",
            cmd_args=[(
                "name",
                {
                    "nargs": "?",
                },
            )],
            section="Syncing and history",
        ),
        cli_command(
            cmd_name="unstash-work",
            cmd_fn=git_utils.cmd_unstash_work,
            cmd_help="pop stashed work; if a name is given, finds and pops that specific entry",
            cmd_args=[(
                "name",
                {
                    "nargs": "?",
                },
            )],
            section="Syncing and history",
        ),
        cli_command(
            cmd_name="amend-last-commit",
            cmd_fn=git_utils.cmd_amend_last_commit,
            cmd_help="amend the last commit with staged changes; optionally update the message too",
            cmd_args=[(
                "message",
                {
                    "nargs": "*",
                },
            )],
            section="Syncing and history",
        ),
        cli_command(
            cmd_name="rename-last-commit",
            cmd_fn=git_utils.cmd_rename_last_commit,
            cmd_help="amend the most recent commit message (rewrites history)",
            cmd_args=[(
                "message",
                {
                    "nargs": "+",
                },
            )],
            section="Syncing and history",
        ),
        ## --- utilities ---
        cli_command(
            cmd_name="self-check",
            cmd_fn=git_utils.check_self,
            cmd_help="verify that git is available on PATH",
            is_hidden=True,
        ),
        cli_command(
            cmd_name="is-detached",
            cmd_fn=git_utils.check_is_detached,
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
    for cmd_name, entry in COMMANDS.items():
        subparser = sub_parsers.add_parser(cmd_name, help=entry["help"])
        for arg_name, kwargs in entry["arg_specs"]:
            subparser.add_argument(arg_name, **kwargs)
    args = arg_parser.parse_args()
    try:
        COMMANDS[args.cmd]["handler"](args)
    except subprocess.CalledProcessError as proc_error:
        sys.exit(proc_error.returncode)


## } MODULE
