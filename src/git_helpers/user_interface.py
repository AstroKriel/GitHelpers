## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, TypeAlias

## third-party
from rich.console import Console

## local
from git_helpers import shell_interface
from git_helpers.commands import (
    git_config,
    git_inspection,
    git_branches,
    git_submodules,
    git_sync,
    git_worktrees,
)
from git_helpers.summary import git_scan

##
## === DATA STRUCTURES
##


class _SectionTitle(str, Enum):
    TRACKING = "Inspecting tracking state"
    CHANGES = "Inspecting changes"
    STASHING = "Stashing work"
    EDITING = "Editing the last commit"
    SYNCING = "Syncing with the remote"
    BRANCHES = "Managing branches"
    WORKTREES = "Managing worktrees"
    SUBMODULES = "Submodules"
    SUMMARY = "Summary"
    CONFIG = "Global git configuration"


@dataclass(frozen=True)
class _CommandDetails:
    help: str
    cmd_args: list[tuple[str, dict[str, Any]]]
    handler: Callable[[argparse.Namespace], None]
    section_title: _SectionTitle | None
    is_hidden: bool


##
## === TYPE ALIASES
##

_CommandEntry: TypeAlias = tuple[str, _CommandDetails]

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
        self._action_max_length: int = 30


def cli_command(
    *,
    cmd_name: str,
    cmd_fn: Callable[..., None],
    cmd_help: str = "",
    cmd_args: list[tuple[str, dict[str, Any]]] | None = None,
    is_hidden: bool = False,
) -> _CommandEntry:
    """Build a (name, details) entry for the command table; handler is auto-generated from cmd_args.

    The section_title is left unset here; _make_command_group stamps it per group.
    """
    cmd_args = cmd_args or []

    ## build Config from global flags, then pass it as the first positional arg to cmd_fn
    def handler(
        args: argparse.Namespace,
    ) -> None:
        config = shell_interface.Config(
            dry_run=args.dry_run,
            allow_dirty=args.allow_dirty,
        )
        return cmd_fn(
            config,
            *[getattr(args, arg_name.lstrip("-").replace("-", "_")) for arg_name, _ in cmd_args],
        )

    return (
        cmd_name,
        _CommandDetails(
            help=cmd_help,
            cmd_args=cmd_args,
            handler=handler,
            section_title=None,
            is_hidden=is_hidden,
        ),
    )


def _make_command_group(
    *,
    section_title: _SectionTitle,
    commands: list[_CommandEntry],
) -> list[_CommandEntry]:
    """Stamp section_title onto each command so a group's section is named exactly once."""
    return [
        (cmd_name, replace(cmd_details, section_title=section_title))
        for cmd_name, cmd_details in commands
    ]


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
        values: str | Sequence[str] | None,
        option_string: str | None = None,
    ) -> None:
        console = Console()
        console.print()
        console.print("[bold]git_helpers[/bold]: git workflow helpers")
        console.print()
        console.print("[dim]usage:[/dim] git_helpers \\[--dry-run] \\[--allow-dirty] <command> \\[args]")
        console.print()
        ## iterate _ALL_COMMANDS in order, printing a header each time the section changes.
        current_section = None
        for cmd_name, cmd_details in _ALL_COMMANDS.items():
            section_title = cmd_details.section_title
            if cmd_details.is_hidden or section_title is None:
                continue
            if section_title != current_section:
                if current_section is not None:
                    console.print()
                console.print(f"[bold]{section_title.value}[/bold]")
                current_section = section_title
            console.print(f"\t[cyan]{cmd_name:<30}[/cyan]{cmd_details.help}")
        console.print()
        console.print("[bold]Global flags[/bold]")
        console.print(f"\t[cyan]{'--dry-run':<30}[/cyan]print commands without executing them")
        console.print(f"\t[cyan]{'--allow-dirty':<30}[/cyan]skip the clean worktree check")
        console.print()
        console.print("[bold]Output legend[/bold]")
        console.print(f"\t[#FFFFFF]{'○ white':<30}[/]action starting")
        console.print(f"\t[#32CD32]{'● green':<30}[/]action outcome")
        console.print(f"\t[#FF4500]{'● red':<30}[/]error")
        console.print(f"\t[#2A71F6]{'→ blue':<30}[/]command being run")
        console.print(f"\t[#E48500]{'→ orange':<30}[/]skipped command (dry-run)")
        console.print(f"\t[#818181]{'→ gray':<30}[/]read-only lookup command")
        console.print(f"\t[#818181]{'· gray':<30}[/]resolved value / context")
        console.print()
        parser.exit()


##
## === COMMAND TABLE
##

_TRACKING_COMMANDS: list[_CommandEntry] = _make_command_group(
    section_title=_SectionTitle.TRACKING,
    commands=[
        cli_command(
            cmd_name="show-local-remotes",
            cmd_fn=git_inspection.show_local_remotes,
            cmd_help="list all configured remotes and their URLs",
        ),
        cli_command(
            cmd_name="show-upstream-state",
            cmd_fn=git_inspection.show_upstream_state,
            cmd_help="show which remote branch the current branch is tracking and its latest commit",
        ),
        cli_command(
            cmd_name="show-branches-status",
            cmd_fn=git_inspection.show_branches_status,
            cmd_help="see all local branches and whether they're ahead or behind their remote (fetches first)",
        ),
        cli_command(
            cmd_name="count-ahead-behind",
            cmd_fn=git_inspection.count_ahead_behind,
            cmd_help="show how many commits the current branch is ahead of and behind its upstream",
        ),
        cli_command(
            cmd_name="show-unpulled-commits",
            cmd_fn=git_inspection.show_unpulled_commits,
            cmd_help="list commits on the remote that haven't been pulled yet",
        ),
        cli_command(
            cmd_name="show-recent-commits",
            cmd_fn=git_inspection.show_recent_commits,
            cmd_help="show the last N commits on the current branch (default: 20)",
            cmd_args=[
                (
                    "--max-entries",
                    {
                        "type": int,
                        "default": 20,
                        "metavar": "N",
                    },
                ),
                (
                    "--show-files-changed",
                    {
                        "action": "store_true",
                        "default": False,
                    },
                ),
            ],
        ),
        cli_command(
            cmd_name="show-commits-on-branch",
            cmd_fn=git_inspection.show_commits_on_branch,
            cmd_help="show commits on the current branch that are not on the base; fetches first",
            cmd_args=[
                (
                    "--base",
                    {
                        "type": str,
                        "default": None,
                        "metavar": "branch",
                        "help": "remote-qualified, e.g. origin/main (default: remote default)",
                    },
                ),
                (
                    "--show-files-changed",
                    {
                        "action": "store_true",
                        "default": False,
                    },
                ),
                (
                    "--no-fetch",
                    {
                        "action": "store_true",
                        "default": False,
                    },
                ),
            ],
        ),
    ],
)

_CHANGES_COMMANDS: list[_CommandEntry] = _make_command_group(
    section_title=_SectionTitle.CHANGES,
    commands=[
        cli_command(
            cmd_name="show-commit",
            cmd_fn=git_inspection.show_commit,
            cmd_help="show the message and diff introduced by a specific commit",
            cmd_args=[("commit", {"type": str})],
        ),
        cli_command(
            cmd_name="show-diff-uncommitted",
            cmd_fn=git_inspection.show_diff,
            cmd_help="show all local changes vs HEAD; optionally scope to a filepath",
            cmd_args=[(
                "--path",
                {
                    "type": str,
                    "default": None,
                    "metavar": "path",
                },
            )],
        ),
        cli_command(
            cmd_name="show-diff-untracked",
            cmd_fn=git_inspection.show_diff_untracked,
            cmd_help="show the diff for an untracked file, as if it were newly added",
            cmd_args=[("path", {"type": str})],
        ),
        cli_command(
            cmd_name="show-diff-n-commits",
            cmd_fn=git_inspection.show_diff_last,
            cmd_help="show changes over the last N commits; add --include-uncommitted to include local changes",
            cmd_args=[
                (
                    "--num-commits",
                    {
                        "type": int,
                        "required": True,
                        "metavar": "N",
                    },
                ),
                (
                    "--include-uncommitted",
                    {
                        "action": "store_true",
                        "default": False,
                    },
                ),
                (
                    "--path",
                    {
                        "type": str,
                        "default": None,
                        "metavar": "path",
                    },
                ),
            ],
        ),
        cli_command(
            cmd_name="show-diff-committed",
            cmd_fn=git_inspection.show_diff_committed,
            cmd_help="show committed changes on the current branch vs a base; fetches first",
            cmd_args=[
                (
                    "--base",
                    {
                        "type": str,
                        "default": None,
                        "metavar": "branch",
                        "help": "remote-qualified, e.g. origin/main (default: remote default)",
                    },
                ),
                (
                    "--name-only",
                    {
                        "action": "store_true",
                        "default": False,
                    },
                ),
                (
                    "--no-fetch",
                    {
                        "action": "store_true",
                        "default": False,
                    },
                ),
                (
                    "--path",
                    {
                        "type": str,
                        "default": None,
                        "metavar": "path",
                    },
                ),
            ],
        ),
    ],
)

_STASHING_COMMANDS: list[_CommandEntry] = _make_command_group(
    section_title=_SectionTitle.STASHING,
    commands=[
        cli_command(
            cmd_name="stash-work",
            cmd_fn=git_sync.cmd_stash_work,
            cmd_help="temporarily save uncommitted work so you can switch context; optionally label it",
            cmd_args=[(
                "name",
                {
                    "type": str,
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            cmd_name="unstash-work",
            cmd_fn=git_sync.cmd_unstash_work,
            cmd_help="restore the most recently stashed work, or a specific stash by name",
            cmd_args=[(
                "name",
                {
                    "type": str,
                    "nargs": "?",
                },
            )],
        ),
    ],
)

_EDITING_COMMANDS: list[_CommandEntry] = _make_command_group(
    section_title=_SectionTitle.EDITING,
    commands=[
        cli_command(
            cmd_name="amend-last-commit",
            cmd_fn=git_sync.cmd_amend_last_commit,
            cmd_help="fold staged changes into the last commit; optionally update the message too",
            cmd_args=[(
                "msg",
                {
                    "type": str,
                    "nargs": "*",
                },
            )],
        ),
        cli_command(
            cmd_name="rename-last-commit",
            cmd_fn=git_sync.cmd_rename_last_commit,
            cmd_help="update the message of the last commit without changing its content (rewrites history)",
            cmd_args=[(
                "msg",
                {
                    "type": str,
                    "nargs": "+",
                },
            )],
        ),
    ],
)

_SYNCING_COMMANDS: list[_CommandEntry] = _make_command_group(
    section_title=_SectionTitle.SYNCING,
    commands=[
        cli_command(
            cmd_name="push",
            cmd_fn=git_sync.cmd_push,
            cmd_help="push the current branch; sets the upstream automatically if it's a new branch",
            cmd_args=[(
                "extra_args",
                {
                    "type": str,
                    "nargs": "*",
                },
            )],
        ),
        cli_command(
            cmd_name="sync-branch",
            cmd_fn=git_sync.cmd_sync_branch,
            cmd_help="bring the current branch up to date with its upstream (or an explicit remote branch)",
            cmd_args=[(
                "base_name",
                {
                    "type": str,
                    "nargs": "?",
                },
            )],
        ),
    ],
)

_BRANCHES_COMMANDS: list[_CommandEntry] = _make_command_group(
    section_title=_SectionTitle.BRANCHES,
    commands=[
        cli_command(
            cmd_name="create-branch-from-default",
            cmd_fn=git_branches.cmd_create_branch_from_default,
            cmd_help="create and push a new branch from the remote default (e.g. origin/main)",
            cmd_args=[(
                "new_branch_name",
                {"type": str},
            )],
        ),
        cli_command(
            cmd_name="create-branch-from-remote",
            cmd_fn=git_branches.cmd_create_branch_from_remote,
            cmd_help="create and push a new branch from a specific remote branch",
            cmd_args=[
                (
                    "new_branch_name",
                    {"type": str},
                ),
                (
                    "start_ref",
                    {"type": str},
                ),
            ],
        ),
        cli_command(
            cmd_name="track-remote-branch",
            cmd_fn=git_branches.cmd_track_remote_branch,
            cmd_help="create a local tracking branch for an existing remote branch and check it out",
            cmd_args=[
                (
                    "remote_branch",
                    {"type": str},
                ),
                (
                    "local_branch",
                    {
                        "type": str,
                        "nargs": "?",
                    },
                ),
            ],
        ),
        cli_command(
            cmd_name="delete-local-branch",
            cmd_fn=git_branches.cmd_delete_local_branch,
            cmd_help="delete a local branch safely (refuses if it has unmerged commits)",
            cmd_args=[("branch_name", {"type": str})],
        ),
        cli_command(
            cmd_name="prune-gone-locals",
            cmd_fn=git_branches.cmd_prune_gone_locals,
            cmd_help="delete local branches whose remote counterpart has been deleted",
        ),
        cli_command(
            cmd_name="force-delete-gone",
            cmd_fn=git_branches.cmd_force_delete_gone,
            cmd_help="force-delete [gone] local branches regardless of merge status (use for squash-merged branches)",
        ),
        cli_command(
            cmd_name="prune-merged-locals",
            cmd_fn=git_branches.cmd_prune_merged_locals,
            cmd_help="delete local branches whose commits are already in the base branch",
            cmd_args=[(
                "base_name",
                {
                    "type": str,
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            cmd_name="cleanup-local-branches",
            cmd_fn=git_branches.cmd_cleanup_local_branches,
            cmd_help="delete all gone and merged local branches in one step",
            cmd_args=[(
                "base_name",
                {
                    "type": str,
                    "nargs": "?",
                },
            )],
        ),
        cli_command(
            cmd_name="rename-branch",
            cmd_fn=git_worktrees.cmd_rename_branch,
            cmd_help="rename the current branch; moves and relinks its worktree automatically if one exists",
            cmd_args=[("new_name", {"type": str})],
        ),
    ],
)

_WORKTREES_COMMANDS: list[_CommandEntry] = _make_command_group(
    section_title=_SectionTitle.WORKTREES,
    commands=[
        cli_command(
            cmd_name="create-worktree",
            cmd_fn=git_worktrees.cmd_create_worktree,
            cmd_help="create a worktree for a branch and initialise submodules (path defaults to ../<repo>-worktrees/<branch-slug>)",
            cmd_args=[
                ("branch_name", {"type": str}),
                (
                    "worktree_path",
                    {
                        "type": str,
                        "nargs": "?",
                    },
                ),
            ],
        ),
        cli_command(
            cmd_name="remove-worktree",
            cmd_fn=git_worktrees.cmd_remove_worktree,
            cmd_help="remove a worktree and delete its local branch in one step",
            cmd_args=[("branch_name", {"type": str})],
        ),
        cli_command(
            cmd_name="prune-worktrees",
            cmd_fn=git_worktrees.cmd_prune_worktrees,
            cmd_help="remove all worktrees whose upstream branch has been deleted and delete their local branches",
        ),
    ],
)

_SUBMODULES_COMMANDS: list[_CommandEntry] = _make_command_group(
    section_title=_SectionTitle.SUBMODULES,
    commands=[
        cli_command(
            cmd_name="show-submodules-status",
            cmd_fn=git_inspection.show_submodules_status,
            cmd_help="show the current state of each submodule (commit SHA and init status)",
        ),
        cli_command(
            cmd_name="update-submodules",
            cmd_fn=git_submodules.cmd_update_submodules,
            cmd_help="update all submodules to their latest commit on the tracked branch",
        ),
        cli_command(
            cmd_name="fix-submodule",
            cmd_fn=git_submodules.cmd_fix_submodule,
            cmd_help=
            "repair a submodule in detached HEAD state (auto-detects branch, pulls, updates parent pointer)",
            cmd_args=[
                ("submodule_path", {"type": str}),
                (
                    "branch",
                    {
                        "type": str,
                        "nargs": "?",
                        "default": None,
                        "metavar": "branch",
                    },
                ),
            ],
        ),
        cli_command(
            cmd_name="add-submodule",
            cmd_fn=git_submodules.cmd_add_submodule,
            cmd_help="add a new submodule tracking its default branch and commit the result",
            cmd_args=[
                ("url", {"type": str}),
                ("local_name", {"type": str}),
                (
                    "branch",
                    {
                        "type": str,
                        "nargs": "?",
                        "default": None,
                        "metavar": "branch",
                    },
                ),
            ],
        ),
    ],
)

_SUMMARY_COMMANDS: list[_CommandEntry] = _make_command_group(
    section_title=_SectionTitle.SUMMARY,
    commands=[
        cli_command(
            cmd_name="scan-repos",
            cmd_fn=git_scan.scan_repos,
            cmd_help="scan below CWD for dirty, unpushed, and recently active git repos",
            cmd_args=[
                (
                    "--depth",
                    {
                        "type": int,
                        "default": 3,
                        "metavar": "N",
                    },
                ),
                (
                    "--since",
                    {
                        "type": int,
                        "default": None,
                        "metavar": "DAYS",
                        "help": "only repos active in the last N days; counts commits per repo",
                    },
                ),
                (
                    "--no-fetch",
                    {
                        "action": "store_true",
                        "default": False,
                    },
                ),
                (
                    "--pull",
                    {
                        "action": "store_true",
                        "default": False,
                        "help": "fast-forward pull the checked-out branch in each repo where it is behind and clean",
                    },
                ),
                (
                    "--push",
                    {
                        "action": "store_true",
                        "default": False,
                        "help": "push each branch that is ahead of its established upstream (skips diverged branches)",
                    },
                ),
            ],
        ),
    ],
)

_CONFIG_COMMANDS: list[_CommandEntry] = _make_command_group(
    section_title=_SectionTitle.CONFIG,
    commands=[
        cli_command(
            cmd_name="set-global-config",
            cmd_fn=git_config.cmd_set_global_config,
            cmd_help="set sensible merge rules in ~/.gitconfig (fast-forward preferred, rerere enabled)",
        ),
        cli_command(
            cmd_name="show-global-config",
            cmd_fn=git_config.show_global_config,
            cmd_help="show the current values of the git settings this tool manages",
        ),
    ],
)

## hidden (not promoted) utilities; no section header, skipped in --help
_HIDDEN_COMMANDS: list[_CommandEntry] = [
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
]

## maps each CLI subcommand name to its details; the group order here sets the order shown in --help
_ALL_COMMANDS: dict[str, _CommandDetails] = dict([
    *_TRACKING_COMMANDS,
    *_CHANGES_COMMANDS,
    *_STASHING_COMMANDS,
    *_EDITING_COMMANDS,
    *_SYNCING_COMMANDS,
    *_BRANCHES_COMMANDS,
    *_WORKTREES_COMMANDS,
    *_SUBMODULES_COMMANDS,
    *_SUMMARY_COMMANDS,
    *_CONFIG_COMMANDS,
    *_HIDDEN_COMMANDS,
])

##
## === ENTRY POINT
##


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
    ## register every subcommand and its positional args in one pass over _ALL_COMMANDS
    for cmd_name, cmd_details in _ALL_COMMANDS.items():
        subparser = sub_parsers.add_parser(cmd_name, help=cmd_details.help)
        for arg_name, arg_kwargs in cmd_details.cmd_args:
            should_inject = (
                arg_name.startswith("--")
                and "help" not in arg_kwargs
                and not arg_kwargs.get("required", False)
            )
            kwargs = {**arg_kwargs, "help": "(default: %(default)s)"} if should_inject else arg_kwargs
            subparser.add_argument(arg_name, **kwargs)
    args = arg_parser.parse_args()
    try:
        _ALL_COMMANDS[args.cmd].handler(args)
    except subprocess.CalledProcessError as proc_error:
        sys.exit(proc_error.returncode)


## } MODULE
