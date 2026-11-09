## { MODULE

##
## === DEPENDENCIES
##

## personal
from huginn import manage_log, manage_shell

## local
from git_helpers import repo_state

##
## === HELPERS
##


def _set_skip_worktree(
    paths: list[str],
    skip: bool,
) -> None:
    flag = "--skip-worktree" if skip else "--no-skip-worktree"
    cmd_update_index = ["git", "update-index", flag, *paths]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_update_index)


##
## === LOCAL EDITS
##


def cmd_ignore_local_edits(
    *,
    paths: list[str],
) -> None:
    """Hide local edits to tracked files from status, diff, and add; nothing is committed or lost."""
    repo_state.require_repo()
    joined_paths = ", ".join(paths)
    manage_log.log_task(f"ignoring local edits to {joined_paths}")
    _set_skip_worktree(
        paths=paths,
        skip=True,
    )
    manage_log.log_outcome(
        f"local edits to {joined_paths} are hidden from git",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


def cmd_unignore_local_edits(
    *,
    paths: list[str],
) -> None:
    """Reverse ignore-local-edits; local edits to these files are reported by git again."""
    repo_state.require_repo()
    joined_paths = ", ".join(paths)
    manage_log.log_task(f"unignoring local edits to {joined_paths}")
    _set_skip_worktree(
        paths=paths,
        skip=False,
    )
    manage_log.log_outcome(
        f"local edits to {joined_paths} are visible to git again",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


## } MODULE
