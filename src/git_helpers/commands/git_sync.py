## { MODULE

##
## === DEPENDENCIES
##

## personal
from huginn import manage_log, manage_shell

## local
from git_helpers import repo_state

##
## === MUTATING COMMANDS
##


def cmd_rename_last_commit(
    *,
    msg: list[str],
) -> None:
    """Replace the message of the most recent commit; rewrites history, avoid if already pushed."""
    repo_state.require_repo()
    ## verify there is at least one commit to amend; a brand-new repo has no HEAD.
    cmd_verify_head = [
        "git",
        "rev-parse",
        "--verify",
        "HEAD",
    ]
    if manage_shell.query_cmd_and_discard_output(cmd_parts=cmd_verify_head) != 0:
        manage_log.exit_with_error("no commits yet (nothing to amend)")
    ## argparse splits the message into words via nargs="+"; rejoin into a single string.
    new_msg = " ".join(msg)
    manage_log.log_task("renaming last commit")
    manage_log.log_note("this rewrites commit history; avoid if already pushed")
    ## `--amend` replaces the most recent commit with a new one that has the
    ## same tree/parent but a different message. The commit hash changes, so force-push
    ## would be needed if this commit is already on a shared remote.
    cmd_amend_msg = [
        "git",
        "commit",
        "--amend",
        "-m",
        new_msg,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_amend_msg)
    manage_log.log_outcome(
        "amended last commit message",
        status=manage_log.OutcomeStatus.SUCCESS,
        items={"new message": new_msg},
    )


def cmd_push(
    *,
    extra_args: list[str],
) -> None:
    """Push the current branch; sets upstream automatically if not already configured."""
    repo_state.require_repo()
    branch_name = repo_state.get_attached_branch_name()
    manage_log.log_task("reading the upstream")
    upstream = repo_state.find_upstream(branch_name=branch_name)
    if upstream is None:
        upstream_text = "no upstream yet"
        matching_upstream_ref = None
    elif upstream.is_local:
        upstream_text = f"upstream is the local branch '{upstream.branch_name}', not a remote branch"
        matching_upstream_ref = None
    elif upstream.branch_name != branch_name:
        upstream_text = f"upstream is '{upstream.ref_name}', which is a different branch"
        matching_upstream_ref = None
    else:
        upstream_text = f"upstream is '{upstream.ref_name}', which matches this branch"
        matching_upstream_ref = upstream.ref_name
    manage_log.log_outcome(
        upstream_text,
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    if matching_upstream_ref is not None:
        manage_log.log_task(f"pushing to '{matching_upstream_ref}'")
        cmd_push_existing = [
            "git",
            "push",
        ] + extra_args
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_push_existing)
        manage_log.log_outcome(
            f"pushed to '{matching_upstream_ref}'",
            status=manage_log.OutcomeStatus.SUCCESS,
        )
    else:
        ## push to the same-named remote branch and make that the upstream with `-u`.
        ## `HEAD` means "push the current branch, whatever it's named".
        manage_log.log_task("choosing the remote")
        remote_name = repo_state.get_default_remote_name()
        target_ref = f"{remote_name}/{branch_name}"
        manage_log.log_task(
            f"pushing to '{target_ref}' and setting it as the upstream, so later pushes and pulls need no arguments",
        )
        cmd_push_set_upstream = [
            "git",
            "push",
            "-u",
            remote_name,
            "HEAD",
        ] + extra_args
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_push_set_upstream)
        manage_log.log_outcome(
            f"pushed to '{target_ref}' and set it as the upstream",
            status=manage_log.OutcomeStatus.SUCCESS,
        )


def cmd_sync_branch(
    *,
    base_name: str | None = None,
    allow_dirty: bool,
) -> None:
    """Sync the current branch with its upstream or an explicit remote base ref, fast-forward first."""
    repo_state.require_repo()
    branch_name = repo_state.get_attached_branch_name()
    manage_log.log_task("choosing the remote")
    default_remote_name = repo_state.get_default_remote_name()
    manage_log.log_task("checking the worktree is clean")
    repo_state.ensure_clean_worktree(allow_dirty=allow_dirty)
    manage_log.log_task("fetching from remote")
    ## fetch before any merge/pull so we're working with up-to-date remote refs.
    cmd_fetch_remote = [
        "git",
        "fetch",
        "--prune",
        default_remote_name,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_fetch_remote)
    manage_log.log_task("deciding on the sync method")
    if base_name:
        if "/" not in base_name:
            manage_log.exit_with_error("base must be remote-qualified, e.g. origin/main")
        manage_log.log_outcome(
            f"a base was given, so merging '{base_name}' instead of pulling from the upstream",
            status=manage_log.OutcomeStatus.SUCCESS,
        )
        manage_log.log_task("merging explicit base into current branch with --ff")
        ## `--ff` means: fast-forward if possible (no merge commit needed when
        ## the histories are linear), but fall back to a real merge commit if
        ## the branches have diverged. This is the least-surprising default.
        cmd_merge_base = [
            "git",
            "merge",
            "--ff",
            base_name,
        ]
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_merge_base)
        manage_log.log_outcome(
            f"synced by merging '{base_name}' (fast-forward if possible)",
            status=manage_log.OutcomeStatus.SUCCESS,
            items={"default remote": default_remote_name},
        )
    else:
        upstream = repo_state.find_upstream(branch_name=branch_name)
        if upstream is None:
            manage_log.exit_with_error(
                "no upstream set; publish (git_helpers push) or provide a base: git_helpers sync-branch <remote>/<base>",
            )
        manage_log.log_outcome(
            f"no base given, so pulling from the upstream '{upstream.ref_name}'",
            status=manage_log.OutcomeStatus.SUCCESS,
        )
        manage_log.log_task("pulling with --ff")
        ## same semantics as above but via `pull`, which combines fetch + merge
        ## against the configured upstream in one step. `--no-rebase` overrides
        ## the global pull.rebase=true so this command keeps its merge semantics.
        cmd_pull_ff = [
            "git",
            "pull",
            "--no-rebase",
            "--ff",
        ]
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_pull_ff)
        manage_log.log_outcome(
            "synced via 'git pull --ff'",
            status=manage_log.OutcomeStatus.SUCCESS,
            items={"default remote": default_remote_name},
        )


def cmd_stash_work(
    *,
    name: str | None = None,
) -> None:
    """Stash uncommitted work; optionally label it with a name for easy retrieval."""
    repo_state.require_repo()
    if name:
        manage_log.log_task("stashing work with label")
        ## `-m` attaches a descriptive message to the stash entry, making it
        ## identifiable by name when listing or popping later.
        cmd_stash_named = [
            "git",
            "stash",
            "push",
            "-m",
            name,
        ]
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_stash_named)
        manage_log.log_outcome(
            f"stashed work as '{name}'",
            status=manage_log.OutcomeStatus.SUCCESS,
        )
    else:
        manage_log.log_task("stashing work")
        cmd_stash_push = [
            "git",
            "stash",
            "push",
        ]
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_stash_push)
        manage_log.log_outcome(
            "stashed work",
            status=manage_log.OutcomeStatus.SUCCESS,
        )


def cmd_unstash_work(
    *,
    name: str | None = None,
) -> None:
    """Pop stashed work; if a name is given, finds and pops that specific stash entry."""
    repo_state.require_repo()
    if name:
        manage_log.log_task("finding stash entry by name")
        ## `stash list` prints entries like: stash@{0}: On main: <message>
        ## search for the label to find the matching index.
        cmd_list_stashes = [
            "git",
            "stash",
            "list",
        ]
        stash_list = manage_shell.query_cmd_and_capture_output(
            cmd_parts=cmd_list_stashes,
            raise_error=False,
        )
        stash_ref = ""
        for line in stash_list.splitlines():
            if name in line:
                stash_ref = line.split(":")[0]
                break
        if not stash_ref:
            manage_log.exit_with_error(f"no stash entry found matching '{name}'")
        manage_log.log_task(f"popping {stash_ref}")
        cmd_pop_named_stash = [
            "git",
            "stash",
            "pop",
            stash_ref,
        ]
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_pop_named_stash)
        manage_log.log_outcome(
            f"restored stash '{name}'",
            status=manage_log.OutcomeStatus.SUCCESS,
            items={"stash entry": stash_ref},
        )
    else:
        manage_log.log_task("popping most recent stash entry")
        cmd_pop_stash = [
            "git",
            "stash",
            "pop",
        ]
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_pop_stash)
        manage_log.log_outcome(
            "restored most recent stash",
            status=manage_log.OutcomeStatus.SUCCESS,
        )


def cmd_amend_last_commit(
    *,
    msg: list[str],
) -> None:
    """Amend the last commit with currently staged changes; optionally update the message too."""
    repo_state.require_repo()
    cmd_verify_head = [
        "git",
        "rev-parse",
        "--verify",
        "HEAD",
    ]
    if manage_shell.query_cmd_and_discard_output(cmd_parts=cmd_verify_head) != 0:
        manage_log.exit_with_error("no commits yet (nothing to amend)")
    manage_log.log_task("amending last commit with staged changes")
    manage_log.log_note("this rewrites commit history; avoid if already pushed")
    if msg:
        ## argparse nargs="*" returns a list; rejoin into a single string.
        new_msg = " ".join(msg)
        ## amend tree and message together.
        cmd_amend_with_msg = [
            "git",
            "commit",
            "--amend",
            "-m",
            new_msg,
        ]
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_amend_with_msg)
        manage_log.log_outcome(
            "amended last commit with staged changes and new message",
            status=manage_log.OutcomeStatus.SUCCESS,
            items={"new message": new_msg},
        )
    else:
        ## `--no-edit` keeps the existing commit message unchanged.
        cmd_amend_no_edit = [
            "git",
            "commit",
            "--amend",
            "--no-edit",
        ]
        manage_shell.run_cmd_and_show_output(cmd_parts=cmd_amend_no_edit)
        manage_log.log_outcome(
            "amended last commit with staged changes (message unchanged)",
            status=manage_log.OutcomeStatus.SUCCESS,
        )


## } MODULE
