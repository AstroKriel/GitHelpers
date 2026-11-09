## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import pathlib

## personal
from huginn import manage_log, manage_shell

## local
from git_helpers import repo_state

##
## === HELPERS
##


def _get_main_worktree_path() -> pathlib.Path:
    """Return the path of the main (non-linked) worktree; always index 0 in the worktree list."""
    return pathlib.Path(repo_state.list_worktrees()[0]["path"])


def _list_worktree_changes(
    *,
    worktree_path: str,
) -> list[str]:
    """Return one `git status --porcelain` line per uncommitted or untracked change in a worktree."""
    ## removal needs --force when a worktree holds submodules, and --force also discards
    ## uncommitted and untracked work; check for that work first.
    cmd_list_changes = [
        "git",
        "-C",
        worktree_path,
        "status",
        "--porcelain",
    ]
    changes_output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_list_changes,
        raise_error=True,
    )
    return changes_output.splitlines()


##
## === WORKTREE COMMANDS
##


def cmd_create_worktree(
    *,
    branch_name: str,
    worktree_path: str | None = None,
    base: str | None = None,
) -> None:
    """Create a worktree for a branch, initialising submodules automatically.

    Defaults the path to ../<repo-name>-worktrees/<branch-slug> (sibling of the main checkout).
    When base is given, branch_name is created fresh from it (git refuses if branch_name
    already exists); otherwise an existing branch_name is worktree'd as-is.
    """
    repo_state.require_repo()
    if worktree_path is None:
        manage_log.log_task("deriving default worktree path from repo name and branch")
        ## use the main worktree (index 0) rather than --show-toplevel so the path
        ## is correct when this command is called from inside a linked worktree.
        main_worktree = _get_main_worktree_path()
        repo_name = main_worktree.name
        branch_slug = branch_name.replace("/", "-")
        worktree_path = str(main_worktree.parent / f"{repo_name}-worktrees" / branch_slug)
    manage_log.log_task("creating worktree")
    if base is None:
        cmd_worktree_add = [
            "git",
            "worktree",
            "add",
            worktree_path,
            branch_name,
        ]
    else:
        manage_log.log_note(
            "creating branch from base",
            items={"base": base},
        )
        ## `-b` creates branch_name fresh from base in the same step; the
        ## repo this command is run from is never switched or checked out into.
        ## `--no-track`: git auto-tracks a remote-tracking base (e.g. upstream/development)
        ## otherwise, which is wrong: branch_name should track its own remote counterpart once
        ## pushed, not the ref it was branched from (same reasoning as create-branch-from-remote).
        cmd_worktree_add = [
            "git",
            "worktree",
            "add",
            worktree_path,
            "-b",
            branch_name,
            "--no-track",
            base,
        ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_worktree_add)
    manage_log.log_task("initialising submodules")
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
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_submodule_init)
    manage_log.log_task("configuring upstream tracking")
    remote_name = repo_state.find_default_remote_name()
    if remote_name is None:
        manage_log.log_outcome(
            "no remote configured, so there is no upstream to set",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
    elif repo_state.remote_branch_exists(remote_name, branch_name):
        manage_log.log_outcome(
            f"'{remote_name}/{branch_name}' exists, so setting it as the upstream; "
            "push and pull then need no arguments, and cleanup can tell when it is deleted",
            status=manage_log.OutcomeStatus.SUCCESS,
        )
        cmd_set_upstream = [
            "git",
            "-C",
            worktree_path,
            "branch",
            "--set-upstream-to",
            f"{remote_name}/{branch_name}",
            branch_name,
        ]
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_set_upstream)
    else:
        manage_log.log_outcome(
            f"'{remote_name}/{branch_name}' is not on the remote yet; "
            "run 'git_helpers push' inside the worktree to publish it and set the upstream",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
    manage_log.log_outcome(
        f"created worktree for '{branch_name}' at '{worktree_path}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


def cmd_remove_worktree(
    *,
    branch_name: str,
) -> None:
    """Remove the worktree for a branch and delete the local branch in one step."""
    repo_state.require_repo()
    manage_log.log_task("finding worktree for branch")
    worktrees = repo_state.list_worktrees()
    ## index 0 is the main checkout; never remove it
    match = next(
        (worktree for worktree in worktrees[1:] if worktree.get("branch") == branch_name),
        None,
    )
    if not match:
        manage_log.exit_with_error(f"no worktree found for branch '{branch_name}'")
    worktree_path = match["path"]
    manage_log.log_task("checking the worktree has no uncommitted or untracked work")
    worktree_changes = _list_worktree_changes(worktree_path=worktree_path)
    if worktree_changes:
        manage_log.log_note(
            "uncommitted or untracked work",
            items={"changes": "; ".join(worktree_changes)},
        )
        manage_log.exit_with_error(f"worktree for '{branch_name}' has work that removal would discard; commit or stash it first")
    manage_log.log_outcome(
        "worktree is clean",
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    manage_log.log_task("removing worktree (--force for submodules)")
    ## --force is required when the worktree contains submodules; without it git
    ## refuses because submodule .git dirs look like nested repositories.
    cmd_remove = [
        "git",
        "worktree",
        "remove",
        "--force",
        worktree_path,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_remove)
    manage_log.log_task("deleting local branch (-d)")
    cmd_delete_branch = [
        "git",
        "branch",
        "-d",
        "--",
        branch_name,
    ]
    success = manage_shell.run_cmd_and_show_output(
        cmd_parts=cmd_delete_branch,
        raise_error=False,
    )
    if success:
        branch_is_kept = False
    else:
        remote_name = repo_state.get_default_remote_name()
        if not repo_state.remote_branch_exists(remote_name, branch_name):
            manage_log.log_task(
                f"'{remote_name}/{branch_name}' no longer exists on remote; force-deleting local branch (-D)",
            )
            cmd_force_delete_branch = [
                "git",
                "branch",
                "-D",
                "--",
                branch_name,
            ]
            manage_shell.run_cmd_and_show_output(cmd_parts=cmd_force_delete_branch)
            branch_is_kept = False
        else:
            branch_is_kept = True
    if branch_is_kept:
        manage_log.log_outcome(
            f"removed worktree for '{branch_name}' but kept the branch: its remote branch still exists; merge or close it first",
            status=manage_log.OutcomeStatus.WARNING,
            items={"worktree path": worktree_path},
        )
    else:
        manage_log.log_outcome(
            f"removed worktree for '{branch_name}'",
            status=manage_log.OutcomeStatus.SUCCESS,
            items={"worktree path": worktree_path},
        )


def cmd_prune_worktrees() -> None:
    """Remove worktrees whose upstream branch has been deleted and delete their local branches."""
    repo_state.require_repo()
    manage_log.log_task("refreshing remote-tracking refs (fetch --prune)")
    cmd_fetch_prune = [
        "git",
        "fetch",
        "--prune",
        "--quiet",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_fetch_prune)
    manage_log.log_task("finding local branches with [gone] upstream")
    cmd_list_branch_tracking = [
        "git",
        "for-each-ref",
        "--format=%(refname:short) %(upstream:track)",
        "refs/heads/",
    ]
    all_branches_output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_list_branch_tracking,
        raise_error=True,
    )
    gone_branches = {line.split()[0] for line in all_branches_output.splitlines() if "[gone]" in line}
    manage_log.log_task("finding worktrees checked out on [gone] branches")
    worktrees = repo_state.list_worktrees()
    ## index 0 is the main checkout; never prune it
    prunable = [worktree for worktree in worktrees[1:] if worktree.get("branch") in gone_branches]
    if not prunable:
        manage_log.log_outcome(
            "no prunable worktrees",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
        return
    removed_worktree_paths: list[str] = []
    kept_worktree_paths: list[str] = []
    kept_branches: list[str] = []
    for worktree in prunable:
        path = worktree["path"]
        branch = worktree["branch"]
        manage_log.log_task(f"checking '{path}' has no uncommitted or untracked work")
        worktree_changes = _list_worktree_changes(worktree_path=path)
        if worktree_changes:
            kept_worktree_paths.append(path)
            manage_log.log_outcome(
                f"kept '{path}': removal would discard its uncommitted or untracked work",
                status=manage_log.OutcomeStatus.WARNING,
                items={"changes": "; ".join(worktree_changes)},
            )
        else:
            manage_log.log_task(f"removing worktree '{path}'")
            cmd_remove = [
                "git",
                "worktree",
                "remove",
                "--force",
                path,
            ]
            manage_shell.run_cmd_and_show_output(cmd_parts=cmd_remove)
            removed_worktree_paths.append(path)
            manage_log.log_task(f"deleting local branch '{branch}' (-d)")
            cmd_delete_branch = [
                "git",
                "branch",
                "-d",
                "--",
                branch,
            ]
            success = manage_shell.run_cmd_and_show_output(
                cmd_parts=cmd_delete_branch,
                raise_error=False,
            )
            if not success:
                kept_branches.append(branch)
                manage_log.log_note(
                    f"kept '{branch}' (unmerged commits; likely squash-merged: "
                    "run 'git_helpers force-delete-gone' to force-delete all [gone] branches with -D)",
                )
    all_prune_items = {
        "removed worktrees": " ".join(removed_worktree_paths),
        "kept worktrees": " ".join(kept_worktree_paths),
        "kept branches": " ".join(kept_branches),
    }
    prune_items = {_label: _value for _label, _value in all_prune_items.items() if _value}
    if kept_worktree_paths or kept_branches:
        manage_log.log_outcome(
            f"removed {len(removed_worktree_paths)} of {len(prunable)} worktree(s); kept some work",
            status=manage_log.OutcomeStatus.WARNING,
            items=prune_items,
        )
    else:
        manage_log.log_outcome(
            f"removed {len(prunable)} worktree(s) and deleted their branches",
            status=manage_log.OutcomeStatus.SUCCESS,
            items=prune_items,
        )


def cmd_rename_branch(
    *,
    new_name: str,
) -> None:
    """Rename the current branch; move and relink its worktree if one exists.

    The worktree path is derived by the same convention as create-worktree:
    ../<repo-name>-worktrees/<new-branch-slug>. Aborts before touching anything
    if that path already exists on disk.
    """
    repo_state.require_repo()
    old_name = repo_state.get_attached_branch_name()
    manage_log.log_task("checking for a linked worktree on this branch")
    worktrees = repo_state.list_worktrees()
    worktree_match = next(
        (worktree for worktree in worktrees[1:] if worktree.get("branch") == old_name),
        None,
    )
    old_worktree_path: pathlib.Path | None = None
    new_worktree_path: pathlib.Path | None = None
    main_worktree: pathlib.Path | None = None
    if worktree_match:
        old_worktree_path = pathlib.Path(worktree_match["path"])
        main_worktree = pathlib.Path(worktrees[0]["path"])
        new_branch_slug = new_name.replace("/", "-")
        new_worktree_path = main_worktree.parent / f"{main_worktree.name}-worktrees" / new_branch_slug
        if new_worktree_path.exists():
            manage_log.exit_with_error(f"target worktree path '{new_worktree_path}' already exists")
    manage_log.log_task("renaming branch")
    cmd_branch_rename = ["git", "branch", "-m", old_name, new_name]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_branch_rename)
    manage_log.log_outcome(
        f"renamed branch '{old_name}' to '{new_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    if old_worktree_path is not None and new_worktree_path is not None and main_worktree is not None:
        manage_log.log_task("moving worktree directory")
        old_worktree_path.rename(new_worktree_path)
        manage_log.log_task("relinking worktree")
        ## run repair via the main worktree so the cwd is always valid, even when
        ## called from inside the worktree that was just moved.
        cmd_repair = [
            "git",
            "-C",
            str(main_worktree),
            "worktree",
            "repair",
            str(new_worktree_path),
        ]
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_repair)
        manage_log.log_outcome(
            f"moved worktree to '{new_worktree_path}'",
            status=manage_log.OutcomeStatus.SUCCESS,
            items={"old worktree path": old_worktree_path},
        )


## } MODULE
