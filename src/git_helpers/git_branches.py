## { MODULE

##
## === DEPENDENCIES
##

## local
from git_helpers import shell_interface, repo_state

##
## === BRANCH COMMANDS
##


def cmd_delete_local_branch(
    config: shell_interface.Config,
    branch_name: str,
) -> None:
    """Safely delete a local branch; refuses if it has unmerged commits."""
    repo_state.require_repo()
    repo_state.require_attached()
    shell_interface.log_step("verifying not deleting the current branch")
    if repo_state.current_branch() == branch_name:
        shell_interface.kill("cannot delete the current branch")
    shell_interface.log_step("deleting local branch (-d)")
    ## `-d` is the safe delete: git refuses if the branch has commits that
    ## haven't been merged into its upstream or HEAD. Use `-D` to force.
    ## `--` separates the flag from the branch name to avoid ambiguity.
    cmd_delete_branch = ["git", "branch", "-d", "--", branch_name]
    shell_interface.run_cmd(config=config, cmd=cmd_delete_branch)
    shell_interface.log_outcome(f"deleted local branch '{branch_name}'")


def cmd_prune_gone_locals(
    config: shell_interface.Config,
) -> None:
    """Delete local branches whose remote counterpart has been deleted ([gone])."""
    repo_state.require_repo()
    repo_state.require_attached()
    shell_interface.log_step("refreshing remote-tracking refs (fetch --prune)")
    ## `--prune` deletes local tracking refs (e.g. origin/feature-x) for
    ## branches that have been deleted on the remote since the last fetch.
    cmd_fetch_prune = ["git", "fetch", "--prune", "--quiet"]
    shell_interface.run_cmd(config=config, cmd=cmd_fetch_prune)
    shell_interface.log_step("finding local branches with [gone] upstream")
    ## `for-each-ref` iterates over all refs matching a pattern. The format
    ## string requests the short branch name and its upstream tracking status.
    ## when the remote branch has been deleted, git marks the tracking status
    ## as "[gone]" — that's what we filter on.
    cmd_list_branch_tracking = [
        "git", "for-each-ref", "--format=%(refname:short) %(upstream:track)", "refs/heads/"
    ]
    all_branches_output = shell_interface.query_cmd(cmd=cmd_list_branch_tracking)
    gone_branches = [line.split()[0] for line in all_branches_output.splitlines() if "[gone]" in line]
    if not gone_branches:
        shell_interface.log_outcome("no [gone] local branches")
        return
    shell_interface.bind_var(
        var_name="branches_to_delete",
        var_value=" ".join(gone_branches),
    )
    shell_interface.log_step("deleting [gone] local branches (-d)")
    for branch_name in gone_branches:
        cmd_delete_gone_branch = ["git", "branch", "-d", "--", branch_name]
        shell_interface.run_cmd(config=config, cmd=cmd_delete_gone_branch)
    shell_interface.log_outcome("deleted [gone] local branches")


def cmd_prune_merged_locals(
    config: shell_interface.Config,
    base_name: str | None = None,
) -> None:
    """Delete local branches whose commits are fully contained in base_name's history."""
    repo_state.require_repo()
    repo_state.require_attached()
    if not base_name:
        ## auto-detect the base: ask the remote what its default branch is.
        ## fall back to "origin/main" if the remote hasn't advertised one.
        remote_name = repo_state.get_default_remote_name()
        default_branch_name = repo_state.get_default_branch_name()
        base_name = f"{remote_name}/{default_branch_name}" if default_branch_name else "origin/main"
    if "/" not in base_name:
        shell_interface.kill("base must be remote-qualified, e.g. origin/main")
    shell_interface.bind_var(
        var_name="base_name",
        var_value=base_name,
    )
    cmd_get_current_branch = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    current_branch_name = shell_interface.query_cmd(cmd=cmd_get_current_branch)
    shell_interface.log_step(
        f"finding local branches merged into '{base_name}' (excluding current and main/master)",
    )
    ## `--merged <ref>` lists branches whose tip is reachable from <ref>,
    ## meaning all their commits are already in <ref>'s history — safe to delete.
    ## never delete the current branch, main, or master even if technically merged —
    ## main/master are protected by convention; current branch can't be deleted while checked out.
    excluded_branches = {current_branch_name, "main", "master"}
    cmd_list_merged_branches = ["git", "branch", "--merged", base_name, "--format=%(refname:short)"]
    merged_branches_output = shell_interface.query_cmd(cmd=cmd_list_merged_branches)
    branches_to_delete = [
        branch_name for branch_name in merged_branches_output.splitlines()
        if branch_name and branch_name not in excluded_branches
    ]
    if not branches_to_delete:
        shell_interface.log_outcome("no merged local branches to delete")
        return
    shell_interface.bind_var(
        var_name="branches_to_delete",
        var_value=" ".join(branches_to_delete),
    )
    shell_interface.log_step("deleting merged local branches (-d)")
    for branch_name in branches_to_delete:
        cmd_delete_merged_branch = ["git", "branch", "-d", "--", branch_name]
        shell_interface.run_cmd(config=config, cmd=cmd_delete_merged_branch)
    shell_interface.log_outcome("deleted merged local branches")


def cmd_cleanup_local_branches(
    config: shell_interface.Config,
    base_name: str | None = None,
) -> None:
    """End-to-end local branch cleanup: remove [gone] branches, then remove merged branches."""
    repo_state.require_repo()
    repo_state.require_attached()
    shell_interface.log_step("refreshing remote-tracking refs (fetch --prune)")
    cmd_fetch_prune = ["git", "fetch", "--prune", "--quiet"]
    shell_interface.run_cmd(config=config, cmd=cmd_fetch_prune)
    ## two-pass cleanup: first remove branches whose remote was deleted ([gone]),
    ## then remove branches whose commits are already in the base branch.
    cmd_prune_gone_locals(config)
    cmd_prune_merged_locals(config, base_name)
    shell_interface.log_outcome("completed local branch cleanup")


def cmd_track_remote_branch(
    config: shell_interface.Config,
    remote_branch: str,
    local_branch: str | None = None,
) -> None:
    """Create a local branch that tracks an existing remote branch and check it out."""
    repo_state.require_remote()
    if "/" not in remote_branch:
        shell_interface.kill("argument must be remote-qualified, e.g. origin/feature-x")
    ## default the local name to the branch part after the remote prefix
    ## (e.g. "origin/feature-x" -> "feature-x").
    local_branch_name = local_branch or remote_branch.split("/", 1)[1]
    shell_interface.bind_var(
        var_name="remote_branch",
        var_value=remote_branch,
    )
    shell_interface.bind_var(
        var_name="local_branch_name",
        var_value=local_branch_name,
    )
    shell_interface.log_step("fetching latest remote refs")
    cmd_fetch_remote = ["git", "fetch", "--prune", remote_branch.split("/")[0]]
    shell_interface.run_cmd(config=config, cmd=cmd_fetch_remote)
    shell_interface.log_step("creating local branch and setting it to track the remote branch")
    ## `switch -c` creates and checks out the new branch.
    ## `--track` configures the upstream so future pull/push know where to go.
    cmd_checkout_tracking_branch = ["git", "switch", "-c", local_branch_name, "--track", remote_branch]
    shell_interface.run_cmd(config=config, cmd=cmd_checkout_tracking_branch)
    shell_interface.log_outcome(f"created '{local_branch_name}' to track '{remote_branch}'")


def cmd_create_branch_from_default(
    config: shell_interface.Config,
    new_branch_name: str,
) -> None:
    """Create a new branch from the remote's default branch and publish it with upstream set."""
    repo_state.require_remote()
    shell_interface.bind_var(
        var_name="new_branch_name",
        var_value=new_branch_name,
    )
    shell_interface.log_step("selecting default remote")
    remote_name = repo_state.get_default_remote_name()
    shell_interface.bind_var(
        var_name="remote_name",
        var_value=remote_name,
    )
    shell_interface.log_step("fetching remote refs")
    cmd_fetch_remote = ["git", "fetch", "--prune", remote_name]
    shell_interface.run_cmd(config=config, cmd=cmd_fetch_remote)
    shell_interface.log_step("discovering remote default branch (<remote>/HEAD)")
    base_branch_name = repo_state.get_default_branch_name()
    if not base_branch_name:
        shell_interface.kill(
            f"no remote default branch set (refs/remotes/{remote_name}/HEAD unknown); "
            f"be explicit: git_helpers create-branch-from-remote {new_branch_name} {remote_name}/<base>",
        )
    shell_interface.bind_var(
        var_name="base_branch_name",
        var_value=base_branch_name,
    )
    shell_interface.log_step("creating local branch from remote default (no tracking)")
    ## `--no-track` means the new branch does NOT track the base it was created
    ## from — we want it to track its own remote counterpart once pushed, not origin/main.
    cmd_create_branch = [
        "git", "switch", "-c", new_branch_name, "--no-track", f"{remote_name}/{base_branch_name}"
    ]
    shell_interface.run_cmd(config=config, cmd=cmd_create_branch)
    shell_interface.log_step("publishing branch and setting upstream (-u)")
    ## `HEAD` pushes the current branch; `-u` sets the upstream so subsequent
    ## `git push` / `git pull` work without arguments.
    cmd_publish_branch = ["git", "push", "-u", remote_name, "HEAD"]
    shell_interface.run_cmd(config=config, cmd=cmd_publish_branch)
    shell_interface.log_outcome(
        f"created '{new_branch_name}' from '{remote_name}/{base_branch_name}' and set upstream to '{remote_name}/{new_branch_name}'",
    )


def cmd_create_branch_from_remote(
    config: shell_interface.Config,
    new_branch_name: str,
    start_ref: str,
) -> None:
    """Create a new branch from an explicit remote ref and publish it with upstream set."""
    repo_state.require_remote()
    if "/" not in start_ref:
        shell_interface.kill("startpoint must be remote-qualified, e.g. origin/development")
    shell_interface.bind_var(
        var_name="new_branch_name",
        var_value=new_branch_name,
    )
    shell_interface.bind_var(
        var_name="start_ref",
        var_value=start_ref,
    )
    shell_interface.log_step("selecting default remote")
    remote_name = repo_state.get_default_remote_name()
    shell_interface.bind_var(
        var_name="remote_name",
        var_value=remote_name,
    )
    shell_interface.log_step("fetching remote refs")
    cmd_fetch_remote = ["git", "fetch", "--prune", remote_name]
    shell_interface.run_cmd(config=config, cmd=cmd_fetch_remote)
    shell_interface.log_step("creating local branch from explicit start point (no tracking)")
    ## `--no-track`: don't track the start point; the branch will track its own
    ## remote counterpart after the push below, not the branch it was cut from.
    cmd_create_branch = ["git", "switch", "-c", new_branch_name, "--no-track", start_ref]
    shell_interface.run_cmd(config=config, cmd=cmd_create_branch)
    shell_interface.log_step("publishing branch and setting upstream (-u)")
    ## `-u` wires up the upstream so future push/pull work without arguments.
    cmd_publish_branch = ["git", "push", "-u", remote_name, "HEAD"]
    shell_interface.run_cmd(config=config, cmd=cmd_publish_branch)
    shell_interface.log_outcome(
        f"created '{new_branch_name}' from '{start_ref}' and set upstream to '{remote_name}/{new_branch_name}'",
    )


## } MODULE
