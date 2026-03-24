## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import sys

## local
from git_helpers import shell_utils, repo_utils

##
## === GIT CONFIGURATION
##


def cmd_set_global_config(
    config: shell_utils.Config,
) -> None:
    """Write FF-first merge defaults and enable rerere to ~/.gitconfig."""
    ## pull.rebase=false: when pulling, merge diverged branches instead of
    ## rebasing them. Safer default — rebase rewrites history.
    shell_utils.run_cmd(config, "git", "config", "--global", "pull.rebase", "false")
    ## pull.ff=true + merge.ff=true: prefer fast-forward when the histories
    ## are linear; only create a merge commit when branches have actually diverged.
    shell_utils.run_cmd(config, "git", "config", "--global", "pull.ff", "true")
    shell_utils.run_cmd(config, "git", "config", "--global", "merge.ff", "true")
    ## rerere (Reuse Recorded Resolution): git remembers how you resolved a
    ## conflict and re-applies the same resolution automatically next time.
    shell_utils.run_cmd(config, "git", "config", "--global", "rerere.enabled", "true")
    shell_utils.log_result("installed FF-first merge defaults globally in ~/.gitconfig")


def show_global_config(
    _config: shell_utils.Config,
) -> None:
    """Print the current values of the git settings this module relies on."""

    ## inner helper to read one config key; returns "(unset)" rather than
    ## empty string so the display is always meaningful.
    def read_config_value(
        key: str,
    ) -> str:
        return shell_utils.query_cmd_or_empty("git", "config", "--global", "--get", key) or "(unset)"

    shell_utils.log_result("global git configuration:")
    for label, key in [
        ("pull.rebase", "pull.rebase"),
        ("pull.ff", "pull.ff"),
        ("merge.ff", "merge.ff"),
        ("rerere.enabled", "rerere.enabled"),
    ]:
        ## `{label:<15}` left-aligns the label in a 15-char field so values line up.
        shell_utils.log_result(f"  {label:<15} = {read_config_value(key)}")
    shell_utils.log_result(
        "tip: edit directly via 'git config --global --edit' or run 'git_helpers set-global-config'"
    )


##
## === PROBING COMMANDS
##


def check_is_detached(
    _config: shell_utils.Config,
) -> None:
    """Exit 0 if HEAD is detached, 1 if on a branch — usable in shell conditionals."""
    ## exit 0 (success/true) if detached, 1 (false) if on a branch — matches
    ## the Unix convention so this can be used in shell conditionals.
    sys.exit(0 if repo_utils.is_detached() else 1)


def show_upstream_state(
    config: shell_utils.Config,
) -> None:
    """Print the current branch name, its upstream ref, and the upstream's latest commit."""
    repo_utils.require_repo()
    shell_utils.log_step("identifying current branch")
    current_branch_name = repo_utils.current_branch()
    shell_utils.log_result(f"local branch: {current_branch_name}")
    shell_utils.log_step("resolving upstream (if any)")
    ## resolve `@{u}` to a human-readable name like "origin/main".
    upstream_name = shell_utils.query_cmd(
        "git",
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    ) if repo_utils.has_upstream() else ""
    if upstream_name:
        shell_utils.log_result(f"upstream:     {upstream_name}")
        shell_utils.log_step("showing the latest commit on the upstream")
        ## `-1` limits to one commit; `--oneline` keeps output compact;
        ## `--decorate` shows branch/tag labels alongside the SHA.
        shell_utils.run_cmd(config, "git", "log", "--oneline", "--decorate", "-1", upstream_name)
        shell_utils.log_outcome(f"upstream detected: {upstream_name}")
    else:
        shell_utils.log_outcome("no upstream configured for current branch")
        shell_utils.log_result("upstream:     (none)")


def show_branches_status(
    config: shell_utils.Config,
) -> None:
    """Fetch from remote, then list all local branches with their upstream and ahead/behind counts."""
    repo_utils.require_repo()
    shell_utils.log_step("refreshing remote-tracking information")
    ## `--prune` removes local tracking refs for branches that no longer exist
    ## on the remote, so the status view reflects current reality.
    shell_utils.run_cmd(config, "git", "fetch", "--prune", "--quiet")
    shell_utils.log_step("showing local branches with upstream and ahead/behind")
    ## `-vv` (very verbose) shows the upstream ref and ahead/behind counts
    ## for each branch. `--no-abbrev` prints full SHAs so nothing is truncated.
    shell_utils.run_cmd(config, "git", "branch", "-vv", "--no-abbrev")


def count_ahead_behind(
    config: shell_utils.Config,
) -> None:
    """Print how many commits the current branch is ahead of and behind its upstream."""
    repo_utils.require_repo()
    shell_utils.log_step("determining upstream for current branch")
    if not repo_utils.has_upstream():
        shell_utils.kill(f"no upstream set for {repo_utils.current_branch()}")
    upstream_name = shell_utils.query_cmd("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    shell_utils.bind_var(
        var_name="upstream_name",
        var_value=upstream_name,
    )
    shell_utils.log_step("fetching latest refs from remote")
    shell_utils.run_cmd(config, "git", "fetch", "--quiet")
    shell_utils.log_step("computing ahead/behind vs upstream")
    ## `rev-list --left-right HEAD...<upstream>` lists commits reachable from
    ## either side but not both (the symmetric difference). `--count` collapses
    ## that to two numbers: commits only in HEAD (ahead) and only in upstream (behind).
    ## the `...` (three dots) means symmetric difference; `..` (two dots) would
    ## only show one direction.
    ahead_behind_counts = shell_utils.run_cmd_and_capture_output(
        config,
        "git",
        "rev-list",
        "--left-right",
        "--count",
        f"HEAD...{upstream_name}",
    )
    if not ahead_behind_counts and config.dry_run:
        return
    ahead_count, behind_count = ahead_behind_counts.split()
    shell_utils.bind_var(
        var_name="ahead_count",
        var_value=ahead_count,
    )
    shell_utils.bind_var(
        var_name="behind_count",
        var_value=behind_count,
    )
    shell_utils.log_result(f"ahead: {ahead_count}; behind: {behind_count}")


def show_unpulled_commits(
    config: shell_utils.Config,
) -> None:
    """List commits that exist on the upstream but have not yet been pulled locally."""
    repo_utils.require_repo()
    shell_utils.log_step("determining upstream")
    if not repo_utils.has_upstream():
        shell_utils.kill("no upstream set")
    upstream_name = shell_utils.query_cmd("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    shell_utils.bind_var(
        var_name="upstream_name",
        var_value=upstream_name,
    )
    shell_utils.log_step("fetching latest from remote")
    shell_utils.run_cmd(config, "git", "fetch", "--quiet")
    shell_utils.log_step("listing commits present upstream but missing locally")
    ## `HEAD..upstream` (two dots) = commits reachable from upstream but NOT
    ## from HEAD — i.e. commits that exist on the remote but haven't been pulled yet.
    shell_utils.run_cmd(config, "git", "log", "--oneline", f"HEAD..{upstream_name}")


def show_local_remotes(
    _config: shell_utils.Config,
) -> None:
    """List all configured remotes and their fetch/push URLs."""
    repo_utils.require_repo()
    ## `-v` prints both fetch and push URLs for each remote; deduplicate with
    ## a set in case fetch == push (the common case), then sort for stable output.
    remotes_output = shell_utils.query_cmd("git", "remote", "-v")
    for line in sorted(set(remotes_output.splitlines())):
        shell_utils.log_result(line)


def show_recent_commits(
    config: shell_utils.Config,
    max_entries: int = 20,
) -> None:
    """Print the most recent N commits on the current branch (default 20)."""
    repo_utils.require_repo()
    shell_utils.bind_var(
        var_name="max_entries",
        var_value=str(max_entries),
    )
    shell_utils.log_step("showing recent commits on current branch")
    ## `--oneline` = one commit per line (short SHA + subject).
    ## `--decorate` = show branch/tag pointers next to commits.
    ## `-n` = limit to the most recent N entries.
    shell_utils.run_cmd(config, "git", "log", "--oneline", "--decorate", "-n", str(max_entries))


def show_submodules_status(
    _config: shell_utils.Config,
) -> None:
    """Print the SHA and initialisation status of each submodule, if any."""
    repo_utils.require_repo()
    ## `submodule status` prints one line per submodule:
    ##   <SHA> <path> (<describe>)
    ## A leading `-` means not initialized; `+` means the checked-out SHA
    ## differs from what the parent repo recorded; ` ` means up to date.
    submodules_output = shell_utils.query_cmd_or_empty("git", "submodule", "status")
    for line in (submodules_output.splitlines()
                 if submodules_output else ["no submodules or not initialized"]):
        shell_utils.log_result(line)


##
## === SUBMODULE COMMANDS
##


def cmd_update_submodules(
    config: shell_utils.Config,
) -> None:
    """Pull the latest commits for all submodules from their tracked branches."""
    repo_utils.require_repo()
    shell_utils.log_step("updating all submodules to latest on their tracked branch")
    ## `--remote` fetches from each submodule's remote and checks out the latest
    ## commit on the tracked branch (set in .gitmodules via `branch = main`).
    ## `--recursive` handles nested submodules.
    shell_utils.run_cmd(config, "git", "submodule", "update", "--remote", "--recursive")
    shell_utils.log_outcome("all submodules updated to latest")


def cmd_fix_submodule(
    config: shell_utils.Config,
    submodule_path: str,
) -> None:
    """Repair a submodule stuck in detached HEAD: checkout main, pull, bump parent pointer."""
    repo_utils.require_repo()
    shell_utils.bind_var(
        var_name="submodule_path",
        var_value=submodule_path,
    )
    shell_utils.log_step("checking out main inside the submodule")
    ## `git -C <path>` runs the command as if cwd were <path> — avoids needing
    ## to actually cd in and out of the submodule directory.
    shell_utils.run_cmd(config, "git", "-C", submodule_path, "checkout", "main")
    shell_utils.log_step("pulling latest commits inside the submodule")
    shell_utils.run_cmd(config, "git", "-C", submodule_path, "pull")
    shell_utils.log_step("staging updated submodule pointer in parent repo")
    ## staging the submodule path tells the parent to record the new HEAD SHA.
    shell_utils.run_cmd(config, "git", "add", submodule_path)
    shell_utils.log_step("committing updated pointer in parent repo")
    shell_utils.run_cmd(
        config,
        "git",
        "commit",
        "-m",
        f"fix: update {submodule_path} pointer after repair",
    )
    shell_utils.log_outcome(f"repaired '{submodule_path}' and bumped parent pointer")


def cmd_add_submodule(
    config: shell_utils.Config,
    url: str,
    local_name: str,
) -> None:
    """Add a new submodule, pin it to track main, and commit .gitmodules + pointer."""
    repo_utils.require_repo()
    shell_utils.bind_var(
        var_name="url",
        var_value=url,
    )
    shell_utils.bind_var(
        var_name="local_name",
        var_value=local_name,
    )
    shell_utils.log_step("adding submodule")
    ## `submodule add` clones the remote into <local_name> and registers it in .gitmodules.
    shell_utils.run_cmd(config, "git", "submodule", "add", url, local_name)
    shell_utils.log_step("setting tracked branch to main in .gitmodules")
    ## record `branch = main` so `git submodule update --remote` knows which
    ## branch to follow when pulling new commits.
    shell_utils.run_cmd(
        config,
        "git",
        "config",
        "-f",
        ".gitmodules",
        f"submodule.{local_name}.branch",
        "main",
    )
    shell_utils.log_step("staging .gitmodules and submodule pointer")
    shell_utils.run_cmd(config, "git", "add", ".gitmodules", local_name)
    shell_utils.log_step("committing")
    shell_utils.run_cmd(config, "git", "commit", "-m", f"add {local_name} submodule")
    shell_utils.log_outcome(f"added submodule '{local_name}' tracking main")


##
## === MUTATING COMMANDS
##


def cmd_rename_last_commit(
    config: shell_utils.Config,
    message: list[str],
) -> None:
    """Replace the message of the most recent commit; rewrites history — avoid if already pushed."""
    repo_utils.require_repo()
    ## verify there is at least one commit to amend; a brand-new repo has no HEAD.
    if shell_utils.probe_cmd("git", "rev-parse", "--verify", "HEAD") != 0:
        shell_utils.kill("no commits yet (nothing to amend)")
    ## argparse splits the message into words via nargs="+"; rejoin into a single string.
    new_message = " ".join(message)
    shell_utils.bind_var(
        var_name="new_message",
        var_value=new_message,
    )
    shell_utils.log_step("renaming last commit")
    shell_utils.log_msg("note: this rewrites commit history; avoid if already pushed")
    ## `--amend` replaces the most recent commit with a new one that has the
    ## same tree/parent but a different message. The SHA changes, so force-push
    ## would be needed if this commit is already on a shared remote.
    shell_utils.run_cmd(config, "git", "commit", "--amend", "-m", new_message)
    shell_utils.log_outcome("amended last commit message")


def cmd_delete_local_branch(
    config: shell_utils.Config,
    branch_name: str,
) -> None:
    """Safely delete a local branch; refuses if it has unmerged commits."""
    repo_utils.require_repo()
    repo_utils.require_attached()
    shell_utils.log_step("verifying not deleting the current branch")
    if repo_utils.current_branch() == branch_name:
        shell_utils.kill("cannot delete the current branch")
    shell_utils.log_step("deleting local branch (-d)")
    ## `-d` is the safe delete: git refuses if the branch has commits that
    ## haven't been merged into its upstream or HEAD. Use `-D` to force.
    ## `--` separates the flag from the branch name to avoid ambiguity.
    shell_utils.run_cmd(config, "git", "branch", "-d", "--", branch_name)
    shell_utils.log_outcome(f"deleted local branch '{branch_name}'")


def cmd_prune_gone_locals(
    config: shell_utils.Config,
) -> None:
    """Delete local branches whose remote counterpart has been deleted ([gone])."""
    repo_utils.require_repo()
    repo_utils.require_attached()
    shell_utils.log_step("refreshing remote-tracking refs (fetch --prune)")
    ## `--prune` deletes local tracking refs (e.g. origin/feature-x) for
    ## branches that have been deleted on the remote since the last fetch.
    shell_utils.run_cmd(config, "git", "fetch", "--prune", "--quiet")
    shell_utils.log_step("finding local branches with [gone] upstream")
    ## `for-each-ref` iterates over all refs matching a pattern. The format
    ## string requests the short branch name and its upstream tracking status.
    ## when the remote branch has been deleted, git marks the tracking status
    ## as "[gone]" — that's what we filter on.
    all_branches_output = shell_utils.query_cmd(
        "git",
        "for-each-ref",
        "--format=%(refname:short) %(upstream:track)",
        "refs/heads/",
    )
    gone_branches = [line.split()[0] for line in all_branches_output.splitlines() if "[gone]" in line]
    if not gone_branches:
        shell_utils.log_outcome("no [gone] local branches")
        return
    shell_utils.bind_var(
        var_name="branches_to_delete",
        var_value=" ".join(gone_branches),
    )
    shell_utils.log_step("deleting [gone] local branches (-d)")
    for branch_name in gone_branches:
        shell_utils.run_cmd(config, "git", "branch", "-d", "--", branch_name)
    shell_utils.log_outcome("deleted [gone] local branches")


def cmd_prune_merged_locals(
    config: shell_utils.Config,
    base_name: str | None = None,
) -> None:
    """Delete local branches whose commits are fully contained in base_name's history."""
    repo_utils.require_repo()
    repo_utils.require_attached()
    if not base_name:
        ## auto-detect the base: ask the remote what its default branch is.
        ## fall back to "origin/main" if the remote hasn't advertised one.
        remote_name = repo_utils.get_default_remote_name()
        default_branch_name = repo_utils.get_default_branch_name()
        base_name = f"{remote_name}/{default_branch_name}" if default_branch_name else "origin/main"
    if "/" not in base_name:
        shell_utils.kill("base must be remote-qualified, e.g. origin/main")
    shell_utils.bind_var(
        var_name="base_name",
        var_value=base_name,
    )
    current_branch_name = shell_utils.query_cmd("git", "rev-parse", "--abbrev-ref", "HEAD")
    shell_utils.log_step(
        f"finding local branches merged into '{base_name}' (excluding current and main/master)",
    )
    ## `--merged <ref>` lists branches whose tip is reachable from <ref>,
    ## meaning all their commits are already in <ref>'s history — safe to delete.
    ## never delete the current branch, main, or master even if technically merged —
    ## main/master are protected by convention; current branch can't be deleted while checked out.
    excluded_branches = {current_branch_name, "main", "master"}
    merged_branches_output = shell_utils.query_cmd(
        "git",
        "branch",
        "--merged",
        base_name,
        "--format=%(refname:short)",
    )
    branches_to_delete = [
        branch_name for branch_name in merged_branches_output.splitlines()
        if branch_name and branch_name not in excluded_branches
    ]
    if not branches_to_delete:
        shell_utils.log_outcome("no merged local branches to delete")
        return
    shell_utils.bind_var(
        var_name="branches_to_delete",
        var_value=" ".join(branches_to_delete),
    )
    shell_utils.log_step("deleting merged local branches (-d)")
    for branch_name in branches_to_delete:
        shell_utils.run_cmd(config, "git", "branch", "-d", "--", branch_name)
    shell_utils.log_outcome("deleted merged local branches")


def cmd_cleanup_local_branches(
    config: shell_utils.Config,
    base_name: str | None = None,
) -> None:
    """End-to-end local branch cleanup: remove [gone] branches, then remove merged branches."""
    repo_utils.require_repo()
    repo_utils.require_attached()
    shell_utils.log_step("refreshing remote-tracking refs (fetch --prune)")
    shell_utils.run_cmd(config, "git", "fetch", "--prune", "--quiet")
    ## two-pass cleanup: first remove branches whose remote was deleted ([gone]),
    ## then remove branches whose commits are already in the base branch.
    cmd_prune_gone_locals(config)
    cmd_prune_merged_locals(config, base_name)
    shell_utils.log_outcome("completed local branch cleanup")


def cmd_track_remote_branch(
    config: shell_utils.Config,
    remote_branch: str,
    local_branch: str | None = None,
) -> None:
    """Create a local branch that tracks an existing remote branch and check it out."""
    repo_utils.require_remote()
    if "/" not in remote_branch:
        shell_utils.kill("argument must be remote-qualified, e.g. origin/feature-x")
    ## default the local name to the branch part after the remote prefix
    ## (e.g. "origin/feature-x" -> "feature-x").
    local_branch_name = local_branch or remote_branch.split("/", 1)[1]
    shell_utils.bind_var(
        var_name="remote_branch",
        var_value=remote_branch,
    )
    shell_utils.bind_var(
        var_name="local_branch_name",
        var_value=local_branch_name,
    )
    shell_utils.log_step("fetching latest remote refs")
    shell_utils.run_cmd(config, "git", "fetch", "--prune", remote_branch.split("/")[0])
    shell_utils.log_step("creating local branch and setting it to track the remote branch")
    ## `switch -c` creates and checks out the new branch.
    ## `--track` configures the upstream so future pull/push know where to go.
    shell_utils.run_cmd(config, "git", "switch", "-c", local_branch_name, "--track", remote_branch)
    shell_utils.log_outcome(f"created '{local_branch_name}' to track '{remote_branch}'")


def cmd_create_branch_from_default(
    config: shell_utils.Config,
    new_branch_name: str,
) -> None:
    """Create a new branch from the remote's default branch and publish it with upstream set."""
    repo_utils.require_remote()
    shell_utils.bind_var(
        var_name="new_branch_name",
        var_value=new_branch_name,
    )
    shell_utils.log_step("selecting default remote")
    remote_name = repo_utils.get_default_remote_name()
    shell_utils.bind_var(
        var_name="remote_name",
        var_value=remote_name,
    )
    shell_utils.log_step("fetching remote refs")
    shell_utils.run_cmd(config, "git", "fetch", "--prune", remote_name)
    shell_utils.log_step("discovering remote default branch (<remote>/HEAD)")
    base_branch_name = repo_utils.get_default_branch_name()
    if not base_branch_name:
        shell_utils.kill(
            f"no remote default branch set (refs/remotes/{remote_name}/HEAD unknown); "
            f"be explicit: git_helpers create-branch-from-remote {new_branch_name} {remote_name}/<base>",
        )
    shell_utils.bind_var(
        var_name="base_branch_name",
        var_value=base_branch_name,
    )
    shell_utils.log_step("creating local branch from remote default (no tracking)")
    ## `--no-track` means the new branch does NOT track the base it was created
    ## from — we want it to track its own remote counterpart once pushed, not origin/main.
    shell_utils.run_cmd(
        config,
        "git",
        "switch",
        "-c",
        new_branch_name,
        "--no-track",
        f"{remote_name}/{base_branch_name}",
    )
    shell_utils.log_step("publishing branch and setting upstream (-u)")
    ## `HEAD` pushes the current branch; `-u` sets the upstream so subsequent
    ## `git push` / `git pull` work without arguments.
    shell_utils.run_cmd(config, "git", "push", "-u", remote_name, "HEAD")
    shell_utils.log_outcome(
        f"created '{new_branch_name}' from '{remote_name}/{base_branch_name}' and set upstream to '{remote_name}/{new_branch_name}'",
    )


def cmd_create_branch_from_remote(
    config: shell_utils.Config,
    new_branch_name: str,
    start_ref: str,
) -> None:
    """Create a new branch from an explicit remote ref and publish it with upstream set."""
    repo_utils.require_remote()
    if "/" not in start_ref:
        shell_utils.kill("startpoint must be remote-qualified, e.g. origin/development")
    shell_utils.bind_var(
        var_name="new_branch_name",
        var_value=new_branch_name,
    )
    shell_utils.bind_var(
        var_name="start_ref",
        var_value=start_ref,
    )
    shell_utils.log_step("selecting default remote")
    remote_name = repo_utils.get_default_remote_name()
    shell_utils.bind_var(
        var_name="remote_name",
        var_value=remote_name,
    )
    shell_utils.log_step("fetching remote refs")
    shell_utils.run_cmd(config, "git", "fetch", "--prune", remote_name)
    shell_utils.log_step("creating local branch from explicit start point (no tracking)")
    ## `--no-track`: don't track the start point; the branch will track its own
    ## remote counterpart after the push below, not the branch it was cut from.
    shell_utils.run_cmd(config, "git", "switch", "-c", new_branch_name, "--no-track", start_ref)
    shell_utils.log_step("publishing branch and setting upstream (-u)")
    ## `-u` wires up the upstream so future push/pull work without arguments.
    shell_utils.run_cmd(config, "git", "push", "-u", remote_name, "HEAD")
    shell_utils.log_outcome(
        f"created '{new_branch_name}' from '{start_ref}' and set upstream to '{remote_name}/{new_branch_name}'",
    )


def cmd_push(
    config: shell_utils.Config,
    extra_args: list[str],
) -> None:
    """Push the current branch; sets upstream automatically if not already configured."""
    repo_utils.require_remote()
    repo_utils.require_attached()
    shell_utils.log_step("publishing current branch")
    remote_name = repo_utils.get_default_remote_name()
    shell_utils.bind_var(
        var_name="remote_name",
        var_value=remote_name,
    )
    shell_utils.log_step("detecting whether upstream is already set")
    if repo_utils.has_upstream():
        ## upstream already configured — plain push uses it automatically.
        shell_utils.log_outcome("using plain push (upstream already set)")
        shell_utils.run_cmd(config, "git", "push", *extra_args)
    else:
        ## no upstream yet: push and set it in one step with `-u`.
        ## `HEAD` means "push the current branch, whatever it's named".
        shell_utils.log_outcome(f"creating upstream and pushing with -u to {remote_name}/<same-name>")
        shell_utils.run_cmd(config, "git", "push", "-u", remote_name, "HEAD", *extra_args)


def cmd_sync_branch(
    config: shell_utils.Config,
    base_name: str | None = None,
) -> None:
    """Sync the current branch with its upstream or an explicit remote base ref, fast-forward first."""
    repo_utils.require_remote()
    repo_utils.require_attached()
    shell_utils.log_step("identifying default remote")
    remote_name = repo_utils.get_default_remote_name()
    shell_utils.bind_var(
        var_name="remote_name",
        var_value=remote_name,
    )
    shell_utils.log_step("verifying clean worktree (unless --allow-dirty)")
    repo_utils.ensure_clean_worktree(config)
    shell_utils.log_step("fetching from remote")
    ## fetch before any merge/pull so we're working with up-to-date remote refs.
    shell_utils.run_cmd(config, "git", "fetch", "--prune", remote_name)
    shell_utils.log_step("deciding on the sync method")
    if base_name:
        if "/" not in base_name:
            shell_utils.kill("base must be remote-qualified, e.g. origin/main")
        shell_utils.bind_var(
            var_name="base_name",
            var_value=base_name,
        )
        shell_utils.log_step("merging explicit base into current branch with --ff")
        ## `--ff` means: fast-forward if possible (no merge commit needed when
        ## the histories are linear), but fall back to a real merge commit if
        ## the branches have diverged. This is the least-surprising default.
        shell_utils.run_cmd(config, "git", "merge", "--ff", base_name)
        shell_utils.log_outcome(f"synced by merging '{base_name}' (fast-forward if possible)")
    elif repo_utils.has_upstream():
        shell_utils.log_step("pulling with --ff")
        ## same semantics as above but via `pull`, which combines fetch + merge
        ## against the configured upstream in one step.
        shell_utils.run_cmd(config, "git", "pull", "--ff")
        shell_utils.log_outcome("synced via 'git pull --ff'")
    else:
        shell_utils.kill(
            "no upstream set; publish (git_helpers push) or provide a base: git_helpers sync-branch <remote>/<base>",
        )


def cmd_stash_work(
    config: shell_utils.Config,
    name: str | None = None,
) -> None:
    """Stash uncommitted work; optionally label it with a name for easy retrieval."""
    repo_utils.require_repo()
    if name:
        shell_utils.bind_var(
            var_name="name",
            var_value=name,
        )
        shell_utils.log_step("stashing work with label")
        ## `-m` attaches a descriptive message to the stash entry, making it
        ## identifiable by name when listing or popping later.
        shell_utils.run_cmd(config, "git", "stash", "push", "-m", name)
        shell_utils.log_outcome(f"stashed work as '{name}'")
    else:
        shell_utils.log_step("stashing work")
        shell_utils.run_cmd(config, "git", "stash", "push")
        shell_utils.log_outcome("stashed work")


def cmd_unstash_work(
    config: shell_utils.Config,
    name: str | None = None,
) -> None:
    """Pop stashed work; if a name is given, finds and pops that specific stash entry."""
    repo_utils.require_repo()
    if name:
        shell_utils.bind_var(
            var_name="name",
            var_value=name,
        )
        shell_utils.log_step("finding stash entry by name")
        ## `stash list` prints entries like: stash@{0}: On main: <message>
        ## search for the label to find the matching index.
        stash_list = shell_utils.query_cmd_or_empty("git", "stash", "list")
        stash_ref = ""
        for line in (stash_list.splitlines() if stash_list else []):
            if name in line:
                stash_ref = line.split(":")[0]
                break
        if not stash_ref:
            shell_utils.kill(f"no stash entry found matching '{name}'")
        shell_utils.bind_var(
            var_name="stash_ref",
            var_value=stash_ref,
        )
        shell_utils.log_step(f"popping {stash_ref}")
        shell_utils.run_cmd(config, "git", "stash", "pop", stash_ref)
        shell_utils.log_outcome(f"restored stash '{name}'")
    else:
        shell_utils.log_step("popping most recent stash entry")
        shell_utils.run_cmd(config, "git", "stash", "pop")
        shell_utils.log_outcome("restored most recent stash")


def cmd_amend_last_commit(
    config: shell_utils.Config,
    message: list[str],
) -> None:
    """Amend the last commit with currently staged changes; optionally update the message too."""
    repo_utils.require_repo()
    if shell_utils.probe_cmd("git", "rev-parse", "--verify", "HEAD") != 0:
        shell_utils.kill("no commits yet (nothing to amend)")
    shell_utils.log_step("amending last commit with staged changes")
    shell_utils.log_msg("note: this rewrites commit history; avoid if already pushed")
    if message:
        ## argparse nargs="*" returns a list; rejoin into a single string.
        new_message = " ".join(message)
        shell_utils.bind_var(
            var_name="new_message",
            var_value=new_message,
        )
        ## amend tree and message together.
        shell_utils.run_cmd(config, "git", "commit", "--amend", "-m", new_message)
        shell_utils.log_outcome("amended last commit with staged changes and new message")
    else:
        ## `--no-edit` keeps the existing commit message unchanged.
        shell_utils.run_cmd(config, "git", "commit", "--amend", "--no-edit")
        shell_utils.log_outcome("amended last commit with staged changes (message unchanged)")


def check_self(
    _config: shell_utils.Config,
) -> None:
    """Verify that git is available on PATH."""
    ## verify git is on PATH before any other operation that would rely on it.
    if shell_utils.probe_cmd("which", "git") != 0:
        shell_utils.kill("git not found in PATH")
    shell_utils.log_outcome("selfcheck passed")


## } MODULE
