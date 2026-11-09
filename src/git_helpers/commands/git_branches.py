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


def _fetch_prune() -> None:
    manage_log.log_task("refreshing remote-tracking refs (fetch --prune)")
    ## `--prune` deletes local tracking refs (e.g. origin/feature-x) for
    ## branches that have been deleted on the remote since the last fetch.
    cmd_fetch_prune = [
        "git",
        "fetch",
        "--prune",
        "--quiet",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_fetch_prune)


##
## === BRANCH COMMANDS
##


def cmd_delete_local_branch(
    *,
    branch_name: str,
) -> None:
    """Safely delete a local branch; refuses if it has unmerged commits."""
    repo_state.require_repo()
    manage_log.log_task("deleting local branch (-d)")
    ## `-d` is the safe delete: git refuses if the branch has commits that
    ## haven't been merged into its upstream or HEAD. Use `-D` to force.
    ## `--` separates the flag from the branch name to avoid ambiguity.
    cmd_delete_branch = [
        "git",
        "branch",
        "-d",
        "--",
        branch_name,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_delete_branch)
    manage_log.log_outcome(
        f"deleted local branch '{branch_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


def cmd_prune_gone_locals() -> None:
    """Delete local branches whose remote counterpart has been deleted ([gone])."""
    repo_state.require_repo()
    _fetch_prune()
    _delete_gone_locals()


def _delete_gone_locals() -> None:
    manage_log.log_task("finding local branches with [gone] upstream")
    ## `for-each-ref` iterates over all refs matching a pattern. The format
    ## string requests the short branch name and its upstream tracking status.
    ## when the remote branch has been deleted, git marks the tracking status
    ## as "[gone]"; that's what we filter on.
    cmd_list_branch_tracking = [
        "git",
        "for-each-ref",
        "--format=%(refname:short) %(upstream:track)",
        "refs/heads/",
    ]
    branch_tracking_output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_list_branch_tracking,
        raise_error=True,
    )
    gone_branches = [_line.split()[0] for _line in branch_tracking_output.splitlines() if "[gone]" in _line]
    if not gone_branches:
        manage_log.log_outcome(
            "no [gone] local branches",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
        return
    manage_log.log_note(
        "found [gone] local branches",
        items={"gone branches": " ".join(gone_branches)},
    )
    manage_log.log_task("deleting [gone] local branches (-d)")
    skipped_branches: list[str] = []
    for branch_name in gone_branches:
        cmd_delete_gone_branch = [
            "git",
            "branch",
            "-d",
            "--",
            branch_name,
        ]
        branch_was_deleted = manage_shell.run_cmd_and_show_output(
            cmd_parts=cmd_delete_gone_branch,
            raise_error=False,
        )
        if not branch_was_deleted:
            skipped_branches.append(branch_name)
            manage_log.log_note(
                f"kept '{branch_name}' (unmerged commits; likely squash-merged: "
                "run 'git_helpers force-delete-gone' to force-delete all [gone] branches with -D)",
            )
    deleted_count = len(gone_branches) - len(skipped_branches)
    if skipped_branches:
        manage_log.log_outcome(
            f"deleted {deleted_count} [gone] branch(es); kept {len(skipped_branches)}: {', '.join(skipped_branches)}",
            status=manage_log.OutcomeStatus.WARNING,
        )
    else:
        manage_log.log_outcome(
            "deleted [gone] local branches",
            status=manage_log.OutcomeStatus.SUCCESS,
        )


def cmd_force_delete_gone() -> None:
    """Force-delete (-D) all local branches whose remote has been deleted, including those with unmerged commits."""
    repo_state.require_repo()
    _fetch_prune()
    manage_log.log_task("finding local branches with [gone] upstream")
    cmd_list_branch_tracking = [
        "git",
        "for-each-ref",
        "--format=%(refname:short) %(upstream:track)",
        "refs/heads/",
    ]
    branch_tracking_output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_list_branch_tracking,
        raise_error=True,
    )
    gone_branches = [_line.split()[0] for _line in branch_tracking_output.splitlines() if "[gone]" in _line]
    if not gone_branches:
        manage_log.log_outcome(
            "no [gone] local branches",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
        return
    ## `-D` skips the merge check: use only when certain all [gone] branches have
    ## been merged (e.g. via squash merge) or intentionally closed without merging.
    manage_log.log_outcome(
        "force-deleting regardless of merge status; only run this if all [gone] branches have been merged or intentionally closed",
        status=manage_log.OutcomeStatus.WARNING,
        items={"gone branches": " ".join(gone_branches)},
    )
    manage_log.log_task("force-deleting [gone] local branches (-D)")
    for branch_name in gone_branches:
        cmd_force_delete_branch = [
            "git",
            "branch",
            "-D",
            "--",
            branch_name,
        ]
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_force_delete_branch)
    manage_log.log_outcome(
        "force-deleted [gone] local branches",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


def cmd_prune_merged_locals(
    *,
    base_name: str | None = None,
) -> None:
    """Delete local branches whose commits are fully contained in base_name's history.

    Excludes any branch with an attached worktree, even if its commits are trivially "merged"
    (e.g. it has no commits ahead of base_name yet): a worktree can hold real, uncommitted or
    untracked work that no commit-ancestry check can see.
    """
    repo_state.require_repo()
    current_branch_name = repo_state.get_attached_branch_name()
    _delete_merged_locals(
        base_name=base_name,
        current_branch_name=current_branch_name,
    )


def _delete_merged_locals(
    *,
    base_name: str | None,
    current_branch_name: str,
) -> None:
    manage_log.log_task("choosing the base branch")
    if base_name:
        manage_log.log_outcome(
            f"using the given base '{base_name}'",
            status=manage_log.OutcomeStatus.SUCCESS,
        )
    else:
        ## ask the remote what its default branch is; fall back to main if it has not advertised one.
        default_remote_name = repo_state.get_default_remote_name()
        default_branch_name = repo_state.get_default_branch_name(remote_name=default_remote_name)
        if default_branch_name is None:
            base_name = f"{default_remote_name}/main"
            manage_log.log_outcome(
                f"no base given and no remote default branch, so falling back to '{base_name}'",
                status=manage_log.OutcomeStatus.WARNING,
            )
        else:
            base_name = f"{default_remote_name}/{default_branch_name}"
            manage_log.log_outcome(
                f"no base given, so using the remote default '{base_name}'",
                status=manage_log.OutcomeStatus.SUCCESS,
            )
    if "/" not in base_name:
        manage_log.exit_with_error("base must be remote-qualified, e.g. origin/main")
    manage_log.log_task(
        f"finding local branches merged into '{base_name}' (excluding current, main/master, and worktrees)",
    )
    ## `--merged <ref>` lists branches whose tip is reachable from <ref>, meaning all their
    ## commits are already in <ref>'s history. This is blind to uncommitted or untracked work
    ## sitting in a branch's worktree, so a freshly branched worktree with zero unique commits
    ## looks identical to a genuinely merged one; treat "has a worktree" as its own protected
    ## category, on top of: never delete the current branch, main, or master even if technically
    ## merged (main/master are protected by convention; current branch can't be deleted while
    ## checked out).
    worktree_branches = repo_state.branches_with_worktrees()
    excluded_branches = {current_branch_name, "main", "master"} | worktree_branches
    cmd_list_merged_branches = [
        "git",
        "branch",
        "--merged",
        base_name,
        "--format=%(refname:short)",
    ]
    merged_branches_output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_list_merged_branches,
        raise_error=True,
    )
    all_merged_branches = [branch_name for branch_name in merged_branches_output.splitlines() if branch_name]
    skipped_worktree_branches = sorted(worktree_branches & set(all_merged_branches) - {current_branch_name})
    if skipped_worktree_branches:
        manage_log.log_note(
            f"keeping {len(skipped_worktree_branches)} branch(es) with an active worktree: "
            f"{', '.join(skipped_worktree_branches)}",
        )
    branches_to_delete = [
        branch_name for branch_name in all_merged_branches if branch_name not in excluded_branches
    ]
    if not branches_to_delete:
        manage_log.log_outcome(
            "no merged local branches to delete",
            status=manage_log.OutcomeStatus.SKIPPED,
            items={"base": base_name},
        )
        return
    manage_log.log_note(
        "found merged local branches",
        items={
            "base": base_name,
            "merged branches": " ".join(branches_to_delete),
        },
    )
    manage_log.log_task("deleting merged local branches (-d)")
    skipped_branches: list[str] = []
    for branch_name in branches_to_delete:
        cmd_delete_merged_branch = [
            "git",
            "branch",
            "-d",
            "--",
            branch_name,
        ]
        branch_was_deleted = manage_shell.run_cmd_and_show_output(
            cmd_parts=cmd_delete_merged_branch,
            raise_error=False,
        )
        if not branch_was_deleted:
            skipped_branches.append(branch_name)
            manage_log.log_note(f"kept '{branch_name}' (could not delete; see the git error above)")
    deleted_count = len(branches_to_delete) - len(skipped_branches)
    if skipped_branches:
        manage_log.log_outcome(
            f"deleted {deleted_count} merged local branch(es); kept {len(skipped_branches)}: {', '.join(skipped_branches)}",
            status=manage_log.OutcomeStatus.WARNING,
        )
    else:
        manage_log.log_outcome(
            "deleted merged local branches",
            status=manage_log.OutcomeStatus.SUCCESS,
        )


def cmd_cleanup_local_branches(
    *,
    base_name: str | None = None,
) -> None:
    """End-to-end local branch cleanup: remove [gone] branches, then remove merged branches."""
    repo_state.require_repo()
    current_branch_name = repo_state.get_attached_branch_name()
    _fetch_prune()
    ## two-pass cleanup: first remove branches whose remote was deleted ([gone]),
    ## then remove branches whose commits are already in the base branch.
    _delete_gone_locals()
    _delete_merged_locals(
        base_name=base_name,
        current_branch_name=current_branch_name,
    )
    manage_log.log_outcome(
        "completed local branch cleanup",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


def cmd_track_remote_branch(
    *,
    remote_branch: str,
    local_branch: str | None = None,
) -> None:
    """Create a local branch that tracks an existing remote branch and check it out."""
    repo_state.require_repo()
    if "/" not in remote_branch:
        manage_log.exit_with_error("argument must be remote-qualified, e.g. origin/feature-x")
    ## default the local name to the branch part after the remote prefix
    ## (e.g. "origin/feature-x" -> "feature-x").
    local_branch_name = local_branch or remote_branch.split("/", 1)[1]
    manage_log.log_task("fetching latest remote refs")
    cmd_fetch_remote = [
        "git",
        "fetch",
        "--prune",
        remote_branch.split("/")[0],
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_fetch_remote)
    manage_log.log_task("creating local branch and setting it to track the remote branch")
    ## `switch -c` creates and checks out the new branch.
    ## `--track` configures the upstream so future pull/push know where to go.
    cmd_checkout_tracking_branch = [
        "git",
        "switch",
        "-c",
        local_branch_name,
        "--track",
        remote_branch,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_checkout_tracking_branch)
    manage_log.log_outcome(
        f"created '{local_branch_name}' to track '{remote_branch}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


def cmd_create_branch_from_default(
    *,
    new_branch_name: str,
) -> None:
    """Create a new branch from the remote's default branch and publish it with upstream set."""
    repo_state.require_repo()
    manage_log.log_task("choosing the remote")
    default_remote_name = repo_state.get_default_remote_name()
    manage_log.log_task("fetching remote refs")
    cmd_fetch_remote = [
        "git",
        "fetch",
        "--prune",
        default_remote_name,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_fetch_remote)
    manage_log.log_task("discovering remote default branch (<remote>/HEAD)")
    default_branch_name = repo_state.get_default_branch_name(remote_name=default_remote_name)
    if default_branch_name is None:
        manage_log.exit_with_error(
            f"no remote default branch set (refs/remotes/{default_remote_name}/HEAD unknown); "
            f"be explicit: git_helpers create-branch-from-remote {new_branch_name} {default_remote_name}/<base>",
        )
    manage_log.log_task("creating local branch from remote default (no tracking)")
    ## `--no-track` means the new branch does NOT track the base it was created
    ## from; we want it to track its own remote counterpart once pushed, not origin/main.
    cmd_create_branch = [
        "git",
        "switch",
        "-c",
        new_branch_name,
        "--no-track",
        f"{default_remote_name}/{default_branch_name}",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_create_branch)
    manage_log.log_task("publishing branch and setting upstream (-u)")
    ## `HEAD` pushes the current branch; `-u` sets the upstream so subsequent
    ## `git push` / `git pull` work without arguments.
    cmd_publish_branch = [
        "git",
        "push",
        "-u",
        default_remote_name,
        "HEAD",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_publish_branch)
    manage_log.log_outcome(
        f"created '{new_branch_name}' from '{default_remote_name}/{default_branch_name}' and set upstream to '{default_remote_name}/{new_branch_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


def cmd_create_branch_from_remote(
    *,
    new_branch_name: str,
    start_ref: str,
) -> None:
    """Create a new branch from an explicit remote ref and publish it with upstream set."""
    repo_state.require_repo()
    if "/" not in start_ref:
        manage_log.exit_with_error("startpoint must be remote-qualified, e.g. origin/development")
    manage_log.log_task("choosing the remote")
    default_remote_name = repo_state.get_default_remote_name()
    manage_log.log_task("fetching remote refs")
    cmd_fetch_remote = [
        "git",
        "fetch",
        "--prune",
        default_remote_name,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_fetch_remote)
    manage_log.log_task("creating local branch from explicit start point (no tracking)")
    ## `--no-track`: don't track the start point; the branch will track its own
    ## remote counterpart after the push below, not the branch it was cut from.
    cmd_create_branch = [
        "git",
        "switch",
        "-c",
        new_branch_name,
        "--no-track",
        start_ref,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_create_branch)
    manage_log.log_task("publishing branch and setting upstream (-u)")
    ## `-u` wires up the upstream so future push/pull work without arguments.
    cmd_publish_branch = [
        "git",
        "push",
        "-u",
        default_remote_name,
        "HEAD",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_publish_branch)
    manage_log.log_outcome(
        f"created '{new_branch_name}' from '{start_ref}' and set upstream to '{default_remote_name}/{new_branch_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


## } MODULE
