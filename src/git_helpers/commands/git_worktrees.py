## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import pathlib

## local
from git_helpers import shell_interface, repo_state

##
## === HELPERS
##


def _parse_worktree_list() -> list[dict[str, str]]:
    """Parse `git worktree list --porcelain` into a list of dicts with path, head, and branch keys.

    Detached and bare worktrees omit the branch key.
    """
    cmd_list_worktrees = [
        "git",
        "worktree",
        "list",
        "--porcelain",
    ]
    output = shell_interface.query_cmd(
        cmd=cmd_list_worktrees,
        error_on_failure=True,
    )
    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        if line.startswith("worktree "):
            current = {"path": line[len("worktree "):]}
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):]
        elif line.startswith("branch "):
            branch_ref = line[len("branch "):]
            current["branch"] = branch_ref.removeprefix("refs/heads/")
        elif line == "" and current:
            worktrees.append(current)
            current = {}
    if current:
        worktrees.append(current)
    return worktrees


##
## === WORKTREE COMMANDS
##


def cmd_create_worktree(
    config: shell_interface.Config,
    branch_name: str,
    worktree_path: str | None = None,
) -> None:
    """Create a worktree for a branch, initialising submodules automatically.

    Defaults the path to ../<repo-name>-<branch-slug> (sibling of the main checkout).
    """
    repo_state.require_repo()
    shell_interface.bind_var(
        var_name="branch_name",
        var_value=branch_name,
    )
    if worktree_path is None:
        shell_interface.log_step("deriving default worktree path from repo name and branch")
        cmd_get_repo_root = [
            "git",
            "rev-parse",
            "--show-toplevel",
        ]
        repo_root = shell_interface.query_cmd(
            cmd=cmd_get_repo_root,
            error_on_failure=True,
        )
        repo_name = pathlib.Path(repo_root).name
        branch_slug = branch_name.replace("/", "-")
        worktree_path = str(pathlib.Path(repo_root).parent / f"{repo_name}-{branch_slug}")
    shell_interface.bind_var(
        var_name="worktree_path",
        var_value=worktree_path,
    )
    shell_interface.log_step("creating worktree")
    cmd_worktree_add = [
        "git",
        "worktree",
        "add",
        worktree_path,
        branch_name,
    ]
    shell_interface.run_cmd(
        config=config,
        cmd=cmd_worktree_add,
    )
    shell_interface.log_step("initialising submodules")
    ## `git -C` runs the submodule command from inside the new worktree without
    ## changing the shell's working directory.
    cmd_submodule_init = [
        "git",
        "-C",
        worktree_path,
        "submodule",
        "update",
        "--init",
    ]
    shell_interface.run_cmd(
        config=config,
        cmd=cmd_submodule_init,
    )
    shell_interface.log_step("configuring upstream tracking")
    if repo_state.has_remote():
        remote_name = repo_state.get_default_remote_name()
        if repo_state.remote_branch_exists(remote_name, branch_name):
            ## branch already exists on the remote; wire up tracking so push/pull
            ## work without arguments and [gone] detection works on cleanup.
            cmd_set_upstream = [
                "git",
                "-C",
                worktree_path,
                "branch",
                "--set-upstream-to",
                f"{remote_name}/{branch_name}",
                branch_name,
            ]
            shell_interface.run_cmd(
                config=config,
                cmd=cmd_set_upstream,
            )
        else:
            shell_interface.log_msg(
                f"  '{remote_name}/{branch_name}' not on remote yet; "
                f"run 'git_helpers push' from inside the worktree to publish and set tracking",
            )
    else:
        shell_interface.log_msg("  no remote configured; skipping upstream setup")
    shell_interface.log_outcome(
        f"created worktree for '{branch_name}' at '{worktree_path}'",
    )


def cmd_remove_worktree(
    config: shell_interface.Config,
    branch_name: str,
) -> None:
    """Remove the worktree for a branch and delete the local branch in one step."""
    repo_state.require_repo()
    shell_interface.bind_var(
        var_name="branch_name",
        var_value=branch_name,
    )
    shell_interface.log_step("finding worktree for branch")
    worktrees = _parse_worktree_list()
    ## index 0 is the main checkout; never remove it
    match = next(
        (wt for wt in worktrees[1:] if wt.get("branch") == branch_name),
        None,
    )
    if not match:
        shell_interface.kill(f"no worktree found for branch '{branch_name}'")
    worktree_path = match["path"]
    shell_interface.bind_var(
        var_name="worktree_path",
        var_value=worktree_path,
    )
    shell_interface.log_step("removing worktree (--force for submodules)")
    ## --force is required when the worktree contains submodules; without it git
    ## refuses because submodule .git dirs look like nested repositories.
    cmd_remove = [
        "git",
        "worktree",
        "remove",
        "--force",
        worktree_path,
    ]
    shell_interface.run_cmd(
        config=config,
        cmd=cmd_remove,
    )
    shell_interface.log_step("deleting local branch (-d)")
    cmd_delete_branch = [
        "git",
        "branch",
        "-d",
        "--",
        branch_name,
    ]
    success = shell_interface.try_run_cmd(
        config=config,
        cmd=cmd_delete_branch,
    )
    if not success:
        remote_name = repo_state.get_default_remote_name()
        if not repo_state.remote_branch_exists(remote_name, branch_name):
            shell_interface.log_step(
                f"'{remote_name}/{branch_name}' no longer exists on remote; force-deleting local branch (-D)",
            )
            cmd_force_delete_branch = [
                "git",
                "branch",
                "-D",
                "--",
                branch_name,
            ]
            shell_interface.run_cmd(
                config=config,
                cmd=cmd_force_delete_branch,
            )
        else:
            shell_interface.log_msg(
                f"  could not delete '{branch_name}' (remote branch still exists; merge or close it first)",
            )
    shell_interface.log_outcome(f"removed worktree for '{branch_name}'")


def cmd_prune_worktrees(
    config: shell_interface.Config,
) -> None:
    """Remove worktrees whose upstream branch has been deleted and delete their local branches."""
    repo_state.require_repo()
    shell_interface.log_step("refreshing remote-tracking refs (fetch --prune)")
    cmd_fetch_prune = [
        "git",
        "fetch",
        "--prune",
        "--quiet",
    ]
    shell_interface.run_cmd(
        config=config,
        cmd=cmd_fetch_prune,
    )
    shell_interface.log_step("finding local branches with [gone] upstream")
    cmd_list_branch_tracking = [
        "git",
        "for-each-ref",
        "--format=%(refname:short) %(upstream:track)",
        "refs/heads/",
    ]
    all_branches_output = shell_interface.query_cmd(
        cmd=cmd_list_branch_tracking,
        error_on_failure=True,
    )
    gone_branches = {
        line.split()[0] for line in all_branches_output.splitlines() if "[gone]" in line
    }
    shell_interface.log_step("finding worktrees checked out on [gone] branches")
    worktrees = _parse_worktree_list()
    ## index 0 is the main checkout; never prune it
    prunable = [
        wt for wt in worktrees[1:]
        if wt.get("branch") in gone_branches
    ]
    if not prunable:
        shell_interface.log_outcome("no prunable worktrees")
        return
    shell_interface.bind_var(
        var_name="worktrees_to_remove",
        var_value=" ".join(wt["path"] for wt in prunable),
    )
    skipped_branches: list[str] = []
    for wt in prunable:
        path = wt["path"]
        branch = wt["branch"]
        shell_interface.log_step(f"removing worktree '{path}'")
        cmd_remove = [
            "git",
            "worktree",
            "remove",
            "--force",
            path,
        ]
        shell_interface.run_cmd(
            config=config,
            cmd=cmd_remove,
        )
        shell_interface.log_step(f"deleting local branch '{branch}' (-d)")
        cmd_delete_branch = [
            "git",
            "branch",
            "-d",
            "--",
            branch,
        ]
        success = shell_interface.try_run_cmd(
            config=config,
            cmd=cmd_delete_branch,
        )
        if not success:
            skipped_branches.append(branch)
            shell_interface.log_msg(
                f"  skipped '{branch}' (unmerged commits; likely squash-merged: "
                f"run 'git_helpers force-delete-gone' to force-delete all [gone] branches with -D)",
            )
    removed_count = len(prunable) - len(skipped_branches)
    if skipped_branches:
        shell_interface.log_outcome(
            f"removed {removed_count} worktree(s); could not delete {len(skipped_branches)} branch(es): {', '.join(skipped_branches)}",
        )
    else:
        shell_interface.log_outcome(
            f"removed {len(prunable)} worktree(s) and deleted their branches",
        )


## } MODULE
