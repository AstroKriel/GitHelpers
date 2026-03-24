## { MODULE

##
## === DEPENDENCIES
##

## local
from git_helpers import shell_interface, repo_state

##
## === MUTATING COMMANDS
##


def cmd_rename_last_commit(
    config: shell_interface.Config,
    message: list[str],
) -> None:
    """Replace the message of the most recent commit; rewrites history — avoid if already pushed."""
    repo_state.require_repo()
    ## verify there is at least one commit to amend; a brand-new repo has no HEAD.
    if shell_interface.probe_cmd("git", "rev-parse", "--verify", "HEAD") != 0:
        shell_interface.kill("no commits yet (nothing to amend)")
    ## argparse splits the message into words via nargs="+"; rejoin into a single string.
    new_message = " ".join(message)
    shell_interface.bind_var(
        var_name="new_message",
        var_value=new_message,
    )
    shell_interface.log_step("renaming last commit")
    shell_interface.log_msg("note: this rewrites commit history; avoid if already pushed")
    ## `--amend` replaces the most recent commit with a new one that has the
    ## same tree/parent but a different message. The SHA changes, so force-push
    ## would be needed if this commit is already on a shared remote.
    shell_interface.run_cmd(config, "git", "commit", "--amend", "-m", new_message)
    shell_interface.log_outcome("amended last commit message")


def cmd_push(
    config: shell_interface.Config,
    extra_args: list[str],
) -> None:
    """Push the current branch; sets upstream automatically if not already configured."""
    repo_state.require_remote()
    repo_state.require_attached()
    shell_interface.log_step("publishing current branch")
    remote_name = repo_state.get_default_remote_name()
    shell_interface.bind_var(
        var_name="remote_name",
        var_value=remote_name,
    )
    shell_interface.log_step("detecting whether upstream is already set")
    if repo_state.has_upstream():
        ## upstream already configured — plain push uses it automatically.
        shell_interface.log_outcome("using plain push (upstream already set)")
        shell_interface.run_cmd(config, "git", "push", *extra_args)
    else:
        ## no upstream yet: push and set it in one step with `-u`.
        ## `HEAD` means "push the current branch, whatever it's named".
        shell_interface.log_outcome(f"creating upstream and pushing with -u to {remote_name}/<same-name>")
        shell_interface.run_cmd(config, "git", "push", "-u", remote_name, "HEAD", *extra_args)


def cmd_sync_branch(
    config: shell_interface.Config,
    base_name: str | None = None,
) -> None:
    """Sync the current branch with its upstream or an explicit remote base ref, fast-forward first."""
    repo_state.require_remote()
    repo_state.require_attached()
    shell_interface.log_step("identifying default remote")
    remote_name = repo_state.get_default_remote_name()
    shell_interface.bind_var(
        var_name="remote_name",
        var_value=remote_name,
    )
    shell_interface.log_step("verifying clean worktree (unless --allow-dirty)")
    repo_state.ensure_clean_worktree(config)
    shell_interface.log_step("fetching from remote")
    ## fetch before any merge/pull so we're working with up-to-date remote refs.
    shell_interface.run_cmd(config, "git", "fetch", "--prune", remote_name)
    shell_interface.log_step("deciding on the sync method")
    if base_name:
        if "/" not in base_name:
            shell_interface.kill("base must be remote-qualified, e.g. origin/main")
        shell_interface.bind_var(
            var_name="base_name",
            var_value=base_name,
        )
        shell_interface.log_step("merging explicit base into current branch with --ff")
        ## `--ff` means: fast-forward if possible (no merge commit needed when
        ## the histories are linear), but fall back to a real merge commit if
        ## the branches have diverged. This is the least-surprising default.
        shell_interface.run_cmd(config, "git", "merge", "--ff", base_name)
        shell_interface.log_outcome(f"synced by merging '{base_name}' (fast-forward if possible)")
    elif repo_state.has_upstream():
        shell_interface.log_step("pulling with --ff")
        ## same semantics as above but via `pull`, which combines fetch + merge
        ## against the configured upstream in one step.
        shell_interface.run_cmd(config, "git", "pull", "--ff")
        shell_interface.log_outcome("synced via 'git pull --ff'")
    else:
        shell_interface.kill(
            "no upstream set; publish (git_helpers push) or provide a base: git_helpers sync-branch <remote>/<base>",
        )


def cmd_stash_work(
    config: shell_interface.Config,
    name: str | None = None,
) -> None:
    """Stash uncommitted work; optionally label it with a name for easy retrieval."""
    repo_state.require_repo()
    if name:
        shell_interface.bind_var(
            var_name="name",
            var_value=name,
        )
        shell_interface.log_step("stashing work with label")
        ## `-m` attaches a descriptive message to the stash entry, making it
        ## identifiable by name when listing or popping later.
        shell_interface.run_cmd(config, "git", "stash", "push", "-m", name)
        shell_interface.log_outcome(f"stashed work as '{name}'")
    else:
        shell_interface.log_step("stashing work")
        shell_interface.run_cmd(config, "git", "stash", "push")
        shell_interface.log_outcome("stashed work")


def cmd_unstash_work(
    config: shell_interface.Config,
    name: str | None = None,
) -> None:
    """Pop stashed work; if a name is given, finds and pops that specific stash entry."""
    repo_state.require_repo()
    if name:
        shell_interface.bind_var(
            var_name="name",
            var_value=name,
        )
        shell_interface.log_step("finding stash entry by name")
        ## `stash list` prints entries like: stash@{0}: On main: <message>
        ## search for the label to find the matching index.
        stash_list = shell_interface.query_cmd_or_empty("git", "stash", "list")
        stash_ref = ""
        for line in (stash_list.splitlines() if stash_list else []):
            if name in line:
                stash_ref = line.split(":")[0]
                break
        if not stash_ref:
            shell_interface.kill(f"no stash entry found matching '{name}'")
        shell_interface.bind_var(
            var_name="stash_ref",
            var_value=stash_ref,
        )
        shell_interface.log_step(f"popping {stash_ref}")
        shell_interface.run_cmd(config, "git", "stash", "pop", stash_ref)
        shell_interface.log_outcome(f"restored stash '{name}'")
    else:
        shell_interface.log_step("popping most recent stash entry")
        shell_interface.run_cmd(config, "git", "stash", "pop")
        shell_interface.log_outcome("restored most recent stash")


def cmd_amend_last_commit(
    config: shell_interface.Config,
    message: list[str],
) -> None:
    """Amend the last commit with currently staged changes; optionally update the message too."""
    repo_state.require_repo()
    if shell_interface.probe_cmd("git", "rev-parse", "--verify", "HEAD") != 0:
        shell_interface.kill("no commits yet (nothing to amend)")
    shell_interface.log_step("amending last commit with staged changes")
    shell_interface.log_msg("note: this rewrites commit history; avoid if already pushed")
    if message:
        ## argparse nargs="*" returns a list; rejoin into a single string.
        new_message = " ".join(message)
        shell_interface.bind_var(
            var_name="new_message",
            var_value=new_message,
        )
        ## amend tree and message together.
        shell_interface.run_cmd(config, "git", "commit", "--amend", "-m", new_message)
        shell_interface.log_outcome("amended last commit with staged changes and new message")
    else:
        ## `--no-edit` keeps the existing commit message unchanged.
        shell_interface.run_cmd(config, "git", "commit", "--amend", "--no-edit")
        shell_interface.log_outcome("amended last commit with staged changes (message unchanged)")


## } MODULE
