## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import sys

## local
from git_helpers import shell_interface, repo_state

##
## === PROBING COMMANDS
##


def check_is_detached(
    _config: shell_interface.Config,
) -> None:
    """Exit 0 if HEAD is detached, 1 if on a branch — usable in shell conditionals."""
    ## exit 0 (success/true) if detached, 1 (false) if on a branch — matches
    ## the Unix convention so this can be used in shell conditionals.
    sys.exit(0 if repo_state.is_detached() else 1)


def show_upstream_state(
    config: shell_interface.Config,
) -> None:
    """Print the current branch name, its upstream ref, and the upstream's latest commit."""
    repo_state.require_repo()
    shell_interface.log_step("identifying current branch")
    current_branch_name = repo_state.current_branch()
    shell_interface.log_result(f"local branch: {current_branch_name}")
    shell_interface.log_step("resolving upstream (if any)")
    ## resolve `@{u}` to a human-readable name like "origin/main".
    cmd_resolve_upstream = ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]
    upstream_name = shell_interface.query_cmd(cmd=cmd_resolve_upstream) if repo_state.has_upstream() else ""
    if upstream_name:
        shell_interface.log_result(f"upstream:     {upstream_name}")
        shell_interface.log_step("showing the latest commit on the upstream")
        ## `-1` limits to one commit; `--oneline` keeps output compact;
        ## `--decorate` shows branch/tag labels alongside the SHA.
        cmd_show_upstream_commit = ["git", "log", "--oneline", "--decorate", "-1", upstream_name]
        shell_interface.run_cmd(config=config, cmd=cmd_show_upstream_commit)
        shell_interface.log_outcome(f"upstream detected: {upstream_name}")
    else:
        shell_interface.log_outcome("no upstream configured for current branch")
        shell_interface.log_result("upstream:     (none)")


def show_branches_status(
    config: shell_interface.Config,
) -> None:
    """Fetch from remote, then list all local branches with their upstream and ahead/behind counts."""
    repo_state.require_repo()
    shell_interface.log_step("refreshing remote-tracking information")
    ## `--prune` removes local tracking refs for branches that no longer exist
    ## on the remote, so the status view reflects current reality.
    cmd_fetch_prune = ["git", "fetch", "--prune", "--quiet"]
    shell_interface.run_cmd(config=config, cmd=cmd_fetch_prune)
    shell_interface.log_step("showing local branches with upstream and ahead/behind")
    ## `-vv` (very verbose) shows the upstream ref and ahead/behind counts
    ## for each branch. `--no-abbrev` prints full SHAs so nothing is truncated.
    cmd_show_branch_verbose = ["git", "branch", "-vv", "--no-abbrev"]
    shell_interface.run_cmd(config=config, cmd=cmd_show_branch_verbose)


def count_ahead_behind(
    config: shell_interface.Config,
) -> None:
    """Print how many commits the current branch is ahead of and behind its upstream."""
    repo_state.require_repo()
    shell_interface.log_step("determining upstream for current branch")
    if not repo_state.has_upstream():
        shell_interface.kill(f"no upstream set for {repo_state.current_branch()}")
    cmd_resolve_upstream = ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]
    upstream_name = shell_interface.query_cmd(cmd=cmd_resolve_upstream)
    shell_interface.bind_var(
        var_name="upstream_name",
        var_value=upstream_name,
    )
    shell_interface.log_step("fetching latest refs from remote")
    cmd_fetch_quiet = ["git", "fetch", "--quiet"]
    shell_interface.run_cmd(config=config, cmd=cmd_fetch_quiet)
    shell_interface.log_step("computing ahead/behind vs upstream")
    ## `rev-list --left-right HEAD...<upstream>` lists commits reachable from
    ## either side but not both (the symmetric difference). `--count` collapses
    ## that to two numbers: commits only in HEAD (ahead) and only in upstream (behind).
    ## the `...` (three dots) means symmetric difference; `..` (two dots) would
    ## only show one direction.
    cmd_count_ahead_behind = ["git", "rev-list", "--left-right", "--count", f"HEAD...{upstream_name}"]
    ahead_behind_counts = shell_interface.run_cmd_and_capture_output(config=config, cmd=cmd_count_ahead_behind)
    if not ahead_behind_counts and config.dry_run:
        return
    ahead_count, behind_count = ahead_behind_counts.split()
    shell_interface.bind_var(
        var_name="ahead_count",
        var_value=ahead_count,
    )
    shell_interface.bind_var(
        var_name="behind_count",
        var_value=behind_count,
    )
    shell_interface.log_result(f"ahead: {ahead_count}; behind: {behind_count}")


def show_unpulled_commits(
    config: shell_interface.Config,
) -> None:
    """List commits that exist on the upstream but have not yet been pulled locally."""
    repo_state.require_repo()
    shell_interface.log_step("determining upstream")
    if not repo_state.has_upstream():
        shell_interface.kill("no upstream set")
    cmd_resolve_upstream = ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]
    upstream_name = shell_interface.query_cmd(cmd=cmd_resolve_upstream)
    shell_interface.bind_var(
        var_name="upstream_name",
        var_value=upstream_name,
    )
    shell_interface.log_step("fetching latest from remote")
    cmd_fetch_quiet = ["git", "fetch", "--quiet"]
    shell_interface.run_cmd(config=config, cmd=cmd_fetch_quiet)
    shell_interface.log_step("listing commits present upstream but missing locally")
    ## `HEAD..upstream` (two dots) = commits reachable from upstream but NOT
    ## from HEAD — i.e. commits that exist on the remote but haven't been pulled yet.
    cmd_show_unpulled = ["git", "log", "--oneline", f"HEAD..{upstream_name}"]
    shell_interface.run_cmd(config=config, cmd=cmd_show_unpulled)


def show_local_remotes(
    _config: shell_interface.Config,
) -> None:
    """List all configured remotes and their fetch/push URLs."""
    repo_state.require_repo()
    ## `-v` prints both fetch and push URLs for each remote; deduplicate with
    ## a set in case fetch == push (the common case), then sort for stable output.
    cmd_list_remotes = ["git", "remote", "-v"]
    remotes_output = shell_interface.query_cmd(cmd=cmd_list_remotes)
    for line in sorted(set(remotes_output.splitlines())):
        shell_interface.log_result(line)


def show_recent_commits(
    config: shell_interface.Config,
    max_entries: int = 20,
) -> None:
    """Print the most recent N commits on the current branch (default 20)."""
    repo_state.require_repo()
    shell_interface.bind_var(
        var_name="max_entries",
        var_value=str(max_entries),
    )
    shell_interface.log_step("showing recent commits on current branch")
    ## `--oneline` = one commit per line (short SHA + subject).
    ## `--decorate` = show branch/tag pointers next to commits.
    ## `-n` = limit to the most recent N entries.
    cmd_show_recent_commits = ["git", "log", "--oneline", "--decorate", "-n", str(max_entries)]
    shell_interface.run_cmd(config=config, cmd=cmd_show_recent_commits)


def show_submodules_status(
    _config: shell_interface.Config,
) -> None:
    """Print the SHA and initialisation status of each submodule, if any."""
    repo_state.require_repo()
    ## `submodule status` prints one line per submodule:
    ##   <SHA> <path> (<describe>)
    ## A leading `-` means not initialized; `+` means the checked-out SHA
    ## differs from what the parent repo recorded; ` ` means up to date.
    cmd_submodule_status = ["git", "submodule", "status"]
    submodules_output = shell_interface.query_cmd(cmd=cmd_submodule_status, error_on_failure=False)
    for line in (submodules_output.splitlines()
                 if submodules_output else ["no submodules or not initialized"]):
        shell_interface.log_result(line)


## } MODULE
