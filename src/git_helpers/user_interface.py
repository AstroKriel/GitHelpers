## { MODULE

##
## === DEPENDENCIES
##

## stdlib
from typing import ClassVar

## personal
from huginn import cmd_args, manage_cli, manage_log

## local
from git_helpers.commands import (
    git_branches,
    git_config,
    git_inspection,
    git_local_edits,
    git_submodules,
    git_sync,
    git_worktrees,
)
from git_helpers.summary import git_scan

##
## === INPUT VALUE TYPES
## git names and paths are passed to git as typed, so each is text; its placeholder says which kind is expected.
##


class InputValueTypes(cmd_args.InputValueTypes):
    BRANCH: ClassVar[cmd_args.InputValueType] = cmd_args.InputValueType(
        placeholder_name="branch",
        convert_fn=str,
    )
    COMMIT: ClassVar[cmd_args.InputValueType] = cmd_args.InputValueType(
        placeholder_name="commit",
        convert_fn=str,
    )
    REF: ClassVar[cmd_args.InputValueType] = cmd_args.InputValueType(
        placeholder_name="ref",
        convert_fn=str,
    )
    PATHSPEC: ClassVar[cmd_args.InputValueType] = cmd_args.InputValueType(
        placeholder_name="pathspec",
        convert_fn=str,
    )
    MESSAGE: ClassVar[cmd_args.InputValueType] = cmd_args.InputValueType(
        placeholder_name="message",
        convert_fn=str,
    )
    URL: ClassVar[cmd_args.InputValueType] = cmd_args.InputValueType(
        placeholder_name="url",
        convert_fn=str,
    )


##
## === SHARED ARGUMENTS
##

_WORD_DIFF_FLAG = cmd_args.FlagArgument(
    long_arg_name="word-diff",
    description="highlight only the changed words inline, instead of whole re-flowed lines",
)
_SHOW_FILES_CHANGED_FLAG = cmd_args.FlagArgument(
    long_arg_name="show-files-changed",
    description="list the files each commit changed",
)
_NO_FETCH_FLAG = cmd_args.FlagArgument(
    long_arg_name="no-fetch",
    description="skip fetching from the remote first",
)
_BASE_ARG = cmd_args.NamedArgument(
    long_arg_name="base",
    description="remote-qualified base, e.g. origin/main (default: the remote default)",
    input_value_type=InputValueTypes.REF,
)
_PATH_ARG = cmd_args.NamedArgument(
    long_arg_name="path",
    description="only show changes to this path",
    input_value_type=InputValueTypes.PATHSPEC,
)
_BASE_NAME_ARG = cmd_args.PositionalArgument(
    param_name="base_name",
    description=
    "remote-qualified base whose history counts as merged, e.g. origin/main (default: the remote default)",
    input_value_type=InputValueTypes.REF,
    allowed_num_input_values=cmd_args.AllowedNumInputValues.ZERO_OR_ONE,
)

##
## === COMMAND TABLE
##

COMMAND_LINE_TOOL = manage_cli.CommandLineTool(
    name="git_helpers",
    description="git workflow helpers",
    cmd_groups=[
        manage_cli.CommandGroup(
            title="Inspecting tracking state",
            cmds=[
                manage_cli.Command(
                    name="show-local-remotes",
                    description="list all configured remotes and their URLs",
                    fn=git_inspection.show_local_remotes,
                ),
                manage_cli.Command(
                    name="show-current-commit-hash",
                    description="print the full commit hash that HEAD currently points to",
                    fn=git_inspection.show_current_commit_hash,
                ),
                manage_cli.Command(
                    name="show-upstream-state",
                    description=
                    "show which remote branch the current branch is tracking and its latest commit",
                    fn=git_inspection.show_upstream_state,
                ),
                manage_cli.Command(
                    name="show-branches-status",
                    description=
                    "see all local branches and whether they're ahead or behind their remote (fetches first)",
                    fn=git_inspection.show_branches_status,
                ),
                manage_cli.Command(
                    name="count-ahead-behind",
                    description="show how many commits the current branch is ahead of and behind its upstream",
                    fn=git_inspection.count_ahead_behind,
                ),
                manage_cli.Command(
                    name="show-unpulled-commits",
                    description="list commits on the remote that haven't been pulled yet",
                    fn=git_inspection.show_unpulled_commits,
                ),
                manage_cli.Command(
                    name="show-recent-commits",
                    description="show the last N commits on the current branch (default: 20)",
                    fn=git_inspection.show_recent_commits,
                    args=[
                        cmd_args.NamedArgument(
                            long_arg_name="max-entries",
                            description="how many commits to show",
                            input_value_type=InputValueTypes.NUMBER,
                            default_value=20,
                        ),
                        _SHOW_FILES_CHANGED_FLAG,
                    ],
                ),
                manage_cli.Command(
                    name="show-commits-on-branch",
                    description="show commits on the current branch that are not on the base; fetches first",
                    fn=git_inspection.show_commits_on_branch,
                    args=[
                        _BASE_ARG,
                        _SHOW_FILES_CHANGED_FLAG,
                        _NO_FETCH_FLAG,
                    ],
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Inspecting changes",
            cmds=[
                manage_cli.Command(
                    name="show-commit",
                    description="show the message and diff introduced by a specific commit",
                    fn=git_inspection.show_commit,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="commit",
                            description="the commit to show, e.g. a hash or HEAD~1",
                            input_value_type=InputValueTypes.COMMIT,
                        ),
                        _WORD_DIFF_FLAG,
                    ],
                ),
                manage_cli.Command(
                    name="show-commit-info",
                    description=
                    "show the full hash, author date, and subject for a commit; fetches it first if not local",
                    fn=git_inspection.show_commit_info,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="commit",
                            description="the commit to describe, e.g. a hash or HEAD~1",
                            input_value_type=InputValueTypes.COMMIT,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="show-diff-uncommitted",
                    description="show all local changes vs HEAD; optionally scope to a filepath",
                    fn=git_inspection.show_diff,
                    args=[
                        _PATH_ARG,
                        _WORD_DIFF_FLAG,
                    ],
                ),
                manage_cli.Command(
                    name="show-diff-untracked",
                    description="show the diff for an untracked file, as if it were newly added",
                    fn=git_inspection.show_diff_untracked,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="path",
                            description="the untracked file to show",
                            input_value_type=InputValueTypes.PATHSPEC,
                        ),
                        _WORD_DIFF_FLAG,
                    ],
                ),
                manage_cli.Command(
                    name="show-diff-n-commits",
                    description=
                    "show changes over the last N commits; add --include-uncommitted to include local changes",
                    fn=git_inspection.show_diff_last,
                    args=[
                        cmd_args.NamedArgument(
                            long_arg_name="num-commits",
                            description="how many commits back to compare against",
                            input_value_type=InputValueTypes.NUMBER,
                            is_required=True,
                        ),
                        cmd_args.FlagArgument(
                            long_arg_name="include-uncommitted",
                            description="also include local, uncommitted changes",
                        ),
                        _PATH_ARG,
                        _WORD_DIFF_FLAG,
                    ],
                ),
                manage_cli.Command(
                    name="show-diff-committed",
                    description="show committed changes on the current branch vs a base; fetches first",
                    fn=git_inspection.show_diff_committed,
                    args=[
                        _BASE_ARG,
                        cmd_args.FlagArgument(
                            long_arg_name="name-only",
                            description="list only the names of the changed files",
                        ),
                        _NO_FETCH_FLAG,
                        _PATH_ARG,
                        _WORD_DIFF_FLAG,
                    ],
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Stashing work",
            cmds=[
                manage_cli.Command(
                    name="stash-work",
                    description=
                    "temporarily save uncommitted work so you can switch context; optionally label it",
                    fn=git_sync.cmd_stash_work,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="name",
                            description="a label for the stash",
                            input_value_type=InputValueTypes.TEXT,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ZERO_OR_ONE,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="unstash-work",
                    description="restore the most recently stashed work, or a specific stash by name",
                    fn=git_sync.cmd_unstash_work,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="name",
                            description="the label of the stash to restore (default: the most recent stash)",
                            input_value_type=InputValueTypes.TEXT,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ZERO_OR_ONE,
                        ),
                    ],
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Ignoring local edits",
            cmds=[
                manage_cli.Command(
                    name="ignore-local-edits",
                    description=
                    "hide local edits to tracked files from status/diff/add, without committing them",
                    fn=git_local_edits.cmd_ignore_local_edits,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="paths",
                            description="the tracked files whose local edits to hide",
                            input_value_type=InputValueTypes.PATHSPEC,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ONE_OR_MORE,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="unignore-local-edits",
                    description="reverse ignore-local-edits; local edits to these files become visible again",
                    fn=git_local_edits.cmd_unignore_local_edits,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="paths",
                            description="the tracked files whose local edits to show again",
                            input_value_type=InputValueTypes.PATHSPEC,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ONE_OR_MORE,
                        ),
                    ],
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Editing the last commit",
            cmds=[
                manage_cli.Command(
                    name="amend-last-commit",
                    description="fold staged changes into the last commit; optionally update the message too",
                    fn=git_sync.cmd_amend_last_commit,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="msg",
                            description="a new message for the commit (default: keep the current message)",
                            input_value_type=InputValueTypes.MESSAGE,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ZERO_OR_MORE,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="rename-last-commit",
                    description=
                    "update the message of the last commit without changing its content (rewrites history)",
                    fn=git_sync.cmd_rename_last_commit,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="msg",
                            description="the new message for the commit",
                            input_value_type=InputValueTypes.MESSAGE,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ONE_OR_MORE,
                        ),
                    ],
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Syncing with the remote",
            cmds=[
                manage_cli.Command(
                    name="push",
                    description=
                    "push the current branch; sets the upstream automatically if it's a new branch",
                    fn=git_sync.cmd_push,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="extra_args",
                            description="extra args passed on to git push",
                            input_value_type=InputValueTypes.TEXT,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ZERO_OR_MORE,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="sync-branch",
                    description=
                    "bring the current branch up to date with its upstream (or an explicit remote branch)",
                    fn=git_sync.cmd_sync_branch,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="base_name",
                            description=
                            "remote-qualified branch to merge, e.g. origin/main (default: the upstream)",
                            input_value_type=InputValueTypes.REF,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ZERO_OR_ONE,
                        ),
                        cmd_args.FlagArgument(
                            long_arg_name="allow-dirty",
                            description="skip the clean worktree check",
                        ),
                    ],
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Managing branches",
            cmds=[
                manage_cli.Command(
                    name="create-branch-from-default",
                    description="create and push a new branch from the remote default (e.g. origin/main)",
                    fn=git_branches.cmd_create_branch_from_default,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="new_branch_name",
                            description="the name of the new branch",
                            input_value_type=InputValueTypes.BRANCH,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="create-branch-from-remote",
                    description="create and push a new branch from a specific remote branch",
                    fn=git_branches.cmd_create_branch_from_remote,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="new_branch_name",
                            description="the name of the new branch",
                            input_value_type=InputValueTypes.BRANCH,
                        ),
                        cmd_args.PositionalArgument(
                            param_name="start_ref",
                            description="the remote branch to start from, e.g. origin/development",
                            input_value_type=InputValueTypes.REF,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="track-remote-branch",
                    description=
                    "create a local tracking branch for an existing remote branch and check it out",
                    fn=git_branches.cmd_track_remote_branch,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="remote_branch",
                            description="the remote branch to track, e.g. origin/feature",
                            input_value_type=InputValueTypes.REF,
                        ),
                        cmd_args.PositionalArgument(
                            param_name="local_branch",
                            description=
                            "the name of the local branch (default: the name of the remote branch)",
                            input_value_type=InputValueTypes.BRANCH,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ZERO_OR_ONE,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="delete-local-branch",
                    description="delete a local branch safely (refuses if it has unmerged commits)",
                    fn=git_branches.cmd_delete_local_branch,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="branch_name",
                            description="the branch to delete",
                            input_value_type=InputValueTypes.BRANCH,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="prune-gone-locals",
                    description="delete local branches whose remote counterpart has been deleted",
                    fn=git_branches.cmd_prune_gone_locals,
                ),
                manage_cli.Command(
                    name="force-delete-gone",
                    description=
                    "force-delete [gone] local branches regardless of merge status (use for squash-merged branches)",
                    fn=git_branches.cmd_force_delete_gone,
                ),
                manage_cli.Command(
                    name="prune-merged-locals",
                    description="delete local branches whose commits are already in the base branch",
                    fn=git_branches.cmd_prune_merged_locals,
                    args=[_BASE_NAME_ARG],
                ),
                manage_cli.Command(
                    name="cleanup-local-branches",
                    description="delete all gone and merged local branches in one step",
                    fn=git_branches.cmd_cleanup_local_branches,
                    args=[_BASE_NAME_ARG],
                ),
                manage_cli.Command(
                    name="rename-branch",
                    description=
                    "rename the current branch; moves and relinks its worktree automatically if one exists",
                    fn=git_worktrees.cmd_rename_branch,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="new_name",
                            description="the new name for the current branch",
                            input_value_type=InputValueTypes.BRANCH,
                        ),
                    ],
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Managing worktrees",
            cmds=[
                manage_cli.Command(
                    name="create-worktree",
                    description=
                    "create a worktree for an existing branch, or a new one from --base, and initialise submodules (path defaults to ../<repo>-worktrees/<branch-slug>)",
                    fn=git_worktrees.cmd_create_worktree,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="branch_name",
                            description="the branch to check out in the new worktree",
                            input_value_type=InputValueTypes.BRANCH,
                        ),
                        cmd_args.PositionalArgument(
                            param_name="worktree_path",
                            description=
                            "where to create the worktree (default: ../<repo>-worktrees/<branch-slug>)",
                            input_value_type=InputValueTypes.PATHSPEC,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ZERO_OR_ONE,
                        ),
                        cmd_args.NamedArgument(
                            long_arg_name="base",
                            description=
                            "create the branch fresh from this ref instead of using an existing branch, e.g. upstream/development",
                            input_value_type=InputValueTypes.REF,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="remove-worktree",
                    description="remove a worktree and delete its local branch in one step",
                    fn=git_worktrees.cmd_remove_worktree,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="branch_name",
                            description="the branch whose worktree to remove",
                            input_value_type=InputValueTypes.BRANCH,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="prune-worktrees",
                    description=
                    "remove all worktrees whose upstream branch has been deleted and delete their local branches",
                    fn=git_worktrees.cmd_prune_worktrees,
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Submodules",
            cmds=[
                manage_cli.Command(
                    name="show-submodules-status",
                    description="show the current state of each submodule (commit hash and init status)",
                    fn=git_inspection.show_submodules_status,
                ),
                manage_cli.Command(
                    name="update-submodules",
                    description="update all submodules to their latest commit on the tracked branch",
                    fn=git_submodules.cmd_update_submodules,
                ),
                manage_cli.Command(
                    name="fix-submodule",
                    description=
                    "repair a submodule in detached HEAD state (auto-detects branch, pulls, updates parent pointer)",
                    fn=git_submodules.cmd_fix_submodule,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="submodule_path",
                            description="the path of the submodule to repair",
                            input_value_type=InputValueTypes.PATHSPEC,
                        ),
                        cmd_args.PositionalArgument(
                            param_name="branch",
                            description="the branch to check out (default: detected from the submodule)",
                            input_value_type=InputValueTypes.BRANCH,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ZERO_OR_ONE,
                        ),
                    ],
                ),
                manage_cli.Command(
                    name="add-submodule",
                    description="add a new submodule tracking its default branch and commit the result",
                    fn=git_submodules.cmd_add_submodule,
                    args=[
                        cmd_args.PositionalArgument(
                            param_name="url",
                            description="the URL of the repo to add",
                            input_value_type=InputValueTypes.URL,
                        ),
                        cmd_args.PositionalArgument(
                            param_name="local_name",
                            description="the folder name for the submodule",
                            input_value_type=InputValueTypes.TEXT,
                        ),
                        cmd_args.PositionalArgument(
                            param_name="branch",
                            description="the branch to track (default: the default branch of the repo)",
                            input_value_type=InputValueTypes.BRANCH,
                            allowed_num_input_values=cmd_args.AllowedNumInputValues.ZERO_OR_ONE,
                        ),
                    ],
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Summary",
            cmds=[
                manage_cli.Command(
                    name="scan-repos",
                    description="scan below CWD for dirty, unpushed, and recently active git repos",
                    fn=git_scan.scan_repos,
                    args=[
                        cmd_args.NamedArgument(
                            long_arg_name="depth",
                            description="how many folders deep to look",
                            input_value_type=InputValueTypes.NUMBER,
                            default_value=3,
                        ),
                        cmd_args.NamedArgument(
                            long_arg_name="since",
                            description="only repos active in the last N days; counts commits per repo",
                            input_value_type=InputValueTypes.NUMBER,
                        ),
                        _NO_FETCH_FLAG,
                        cmd_args.FlagArgument(
                            long_arg_name="pull",
                            description=
                            "fast-forward pull the checked-out branch in each repo where it is behind and clean",
                        ),
                        cmd_args.FlagArgument(
                            long_arg_name="push",
                            description=
                            "push each branch that is ahead of its established upstream (skips diverged branches)",
                        ),
                    ],
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Global git configuration",
            cmds=[
                manage_cli.Command(
                    name="set-global-config",
                    description=
                    "set sensible defaults in ~/.gitconfig (fast-forward preferred, rerere enabled, default branch main)",
                    fn=git_config.cmd_set_global_config,
                ),
                manage_cli.Command(
                    name="show-global-config",
                    description="show the current values of the git settings this tool manages",
                    fn=git_config.show_global_config,
                ),
            ],
        ),
    ],
)

##
## === ENTRY POINT
##


def main() -> None:
    log_file_path = manage_log.get_home_log_file_path(tool_name=COMMAND_LINE_TOOL.name)
    manage_log.set_log_file_path(log_file_path=log_file_path)
    manage_cli.run_cli(command_line_tool=COMMAND_LINE_TOOL)


## } MODULE
