## { MODULE

##
## === DEPENDENCIES
##

## local
from git_helpers import repo_state, shell_interface

##
## === HELPERS
##


def _set_skip_worktree(
    config: shell_interface.Config,
    paths: list[str],
    skip: bool,
) -> None:
    flag = "--skip-worktree" if skip else "--no-skip-worktree"
    cmd_update_index = ["git", "update-index", flag, *paths]
    shell_interface.run_cmd(
        config=config,
        cmd=cmd_update_index,
    )


##
## === LOCAL EDITS
##


def cmd_ignore_local_edits(
    config: shell_interface.Config,
    paths: list[str],
) -> None:
    """Hide local edits to tracked files from status, diff, and add; nothing is committed or lost."""
    repo_state.require_repo()
    joined_paths = ", ".join(paths)
    shell_interface.log_step(f"ignoring local edits to {joined_paths}")
    _set_skip_worktree(
        config=config,
        paths=paths,
        skip=True,
    )
    shell_interface.log_outcome(f"local edits to {joined_paths} are hidden from git")


def cmd_unignore_local_edits(
    config: shell_interface.Config,
    paths: list[str],
) -> None:
    """Reverse ignore-local-edits; local edits to these files are reported by git again."""
    repo_state.require_repo()
    joined_paths = ", ".join(paths)
    shell_interface.log_step(f"unignoring local edits to {joined_paths}")
    _set_skip_worktree(
        config=config,
        paths=paths,
        skip=False,
    )
    shell_interface.log_outcome(f"local edits to {joined_paths} are visible to git again")


## } MODULE
