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
    """Exit 0 if HEAD is detached, 1 if on a branch; usable in shell conditionals."""
    ## exit 0 (success/true) if detached, 1 (false) if on a branch; matches
    ## the Unix convention so this can be used in shell conditionals.
    sys.exit(0 if repo_state.is_detached() else 1)


def show_upstream_state(
    config: shell_interface.Config,
) -> None:
    """Print the current branch name, its upstream ref, and the upstream's latest commit."""
    repo_state.require_repo()
    shell_interface.log_step("identifying current branch")
    current_branch_name = repo_state.current_branch()
    shell_interface.log_step("resolving upstream (if any)")
    ## resolve `@{u}` to a human-readable name like "origin/main".
    cmd_resolve_upstream = [
        "git",
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    ]
    if repo_state.has_upstream():
        upstream_name = shell_interface.query_cmd(
            cmd=cmd_resolve_upstream,
            error_on_failure=True,
        )
    else:
        upstream_name = ""
    if upstream_name:
        shell_interface.log_result(f"upstream:     {upstream_name}")
        shell_interface.log_step("showing the latest commit on the upstream")
        ## `-1` limits to one commit; `--oneline` keeps output compact;
        ## `--decorate` shows branch/tag labels alongside the SHA.
        cmd_show_upstream_commit = [
            "git",
            "log",
            "--oneline",
            "--decorate",
            "-1",
            upstream_name,
        ]
        shell_interface.run_cmd(
            config=config,
            cmd=cmd_show_upstream_commit,
        )
    else:
        shell_interface.log_outcome("no upstream configured for current branch")


def show_branches_status(
    config: shell_interface.Config,
) -> None:
    """Fetch from remote, then list all local branches with their upstream and ahead/behind counts."""
    repo_state.require_repo()
    shell_interface.log_step("refreshing remote-tracking information")
    ## `--prune` removes local tracking refs for branches that no longer exist
    ## on the remote, so the status view reflects current reality.
    ## `--no-recurse-submodules` keeps the fetch on the superproject only; this
    ## command reports the superproject's branches, so on-demand submodule
    ## fetching would only add latency and surface unrelated submodule errors.
    cmd_fetch_prune = [
        "git",
        "fetch",
        "--prune",
        "--no-recurse-submodules",
        "--quiet",
    ]
    shell_interface.run_cmd(
        config=config,
        cmd=cmd_fetch_prune,
    )
    shell_interface.log_step("showing local branches with upstream and ahead/behind")
    ## `-vv` (very verbose) shows the upstream ref and ahead/behind counts
    ## for each branch. `--no-abbrev` prints full SHAs so nothing is truncated.
    cmd_show_branch_verbose = [
        "git",
        "branch",
        "-vv",
        "--no-abbrev",
    ]
    shell_interface.run_cmd(
        config=config,
        cmd=cmd_show_branch_verbose,
    )


def count_ahead_behind(
    config: shell_interface.Config,
) -> None:
    """Print how many commits the current branch is ahead of and behind its upstream."""
    repo_state.require_repo()
    shell_interface.log_step("determining upstream for current branch")
    if not repo_state.has_upstream():
        shell_interface.kill(f"no upstream set for {repo_state.current_branch()}")
    cmd_resolve_upstream = [
        "git",
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    ]
    upstream_name = shell_interface.query_cmd(
        cmd=cmd_resolve_upstream,
        error_on_failure=True,
    )
    shell_interface.bind_var(
        var_name="upstream_name",
        var_value=upstream_name,
    )
    shell_interface.log_step("fetching latest refs from remote")
    ## stay on the superproject; this only compares HEAD to its upstream.
    cmd_fetch_quiet = [
        "git",
        "fetch",
        "--no-recurse-submodules",
        "--quiet",
    ]
    shell_interface.run_cmd(
        config=config,
        cmd=cmd_fetch_quiet,
    )
    shell_interface.log_step("computing ahead/behind vs upstream")
    ## `rev-list --left-right HEAD...<upstream>` lists commits reachable from
    ## either side but not both (the symmetric difference). `--count` collapses
    ## that to two numbers: commits only in HEAD (ahead) and only in upstream (behind).
    ## the `...` (three dots) means symmetric difference; `..` (two dots) would
    ## only show one direction.
    cmd_count_ahead_behind = [
        "git",
        "rev-list",
        "--left-right",
        "--count",
        f"HEAD...{upstream_name}",
    ]
    ahead_behind_counts = shell_interface.query_cmd(
        cmd=cmd_count_ahead_behind,
        error_on_failure=True,
    )
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
    cmd_resolve_upstream = [
        "git",
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    ]
    upstream_name = shell_interface.query_cmd(
        cmd=cmd_resolve_upstream,
        error_on_failure=True,
    )
    shell_interface.bind_var(
        var_name="upstream_name",
        var_value=upstream_name,
    )
    shell_interface.log_step("fetching latest from remote")
    ## stay on the superproject; this only lists commits missing on HEAD.
    cmd_fetch_quiet = [
        "git",
        "fetch",
        "--no-recurse-submodules",
        "--quiet",
    ]
    shell_interface.run_cmd(
        config=config,
        cmd=cmd_fetch_quiet,
    )
    shell_interface.log_step("listing commits present upstream but missing locally")
    ## `HEAD..upstream` (two dots) = commits reachable from upstream but NOT
    ## from HEAD (commits that exist on the remote but haven't been pulled yet).
    cmd_show_unpulled = [
        "git",
        "log",
        "--oneline",
        f"HEAD..{upstream_name}",
    ]
    shell_interface.run_cmd(
        config=config,
        cmd=cmd_show_unpulled,
    )


def show_local_remotes(
    _config: shell_interface.Config,
) -> None:
    """List all configured remotes and their fetch/push URLs."""
    repo_state.require_repo()
    ## `-v` prints both fetch and push URLs for each remote; deduplicate with
    ## a set in case fetch == push (the common case), then sort for stable output.
    cmd_list_remotes = [
        "git",
        "remote",
        "-v",
    ]
    remotes_output = shell_interface.query_cmd(
        cmd=cmd_list_remotes,
        error_on_failure=True,
    )
    for line in sorted(set(remotes_output.splitlines())):
        shell_interface.log_result(line)


def show_commits_on_branch(
    config: shell_interface.Config,
    base: str | None = None,
    show_files_changed: bool = False,
    no_fetch: bool = False,
) -> None:
    """Show commits on the current branch that are not on the base branch; fetches first by default."""
    repo_state.require_repo()
    remote = repo_state.get_default_remote_name()
    if not no_fetch:
        shell_interface.log_step(f"fetching from {remote}")
        shell_interface.run_cmd(
            config=config,
            cmd=["git", "fetch", "--no-recurse-submodules", "--quiet", remote],
        )
    if base:
        if "/" not in base:
            shell_interface.kill("base must be remote-qualified, e.g. origin/main")
        remote_base = base
    else:
        inferred = repo_state.get_default_branch_name()
        if not inferred:
            shell_interface.kill("could not infer default branch; pass base explicitly, e.g. origin/main")
        remote_base = f"{remote}/{inferred}"
    branch = repo_state.current_branch()
    base_branch = remote_base.split("/", 1)[-1]
    if branch == base_branch:
        shell_interface.kill(
            f"already on '{base_branch}'; show-commits-on-branch compares a feature branch to its base"
        )
    shell_interface.log_step(f"showing commits on '{branch}' not in '{remote_base}'")
    cmd = ["git", "log", f"{remote_base}..HEAD", "--oneline", "--decorate"]
    if show_files_changed:
        cmd.append("--stat")
    shell_interface.run_cmd(config=config, cmd=cmd)


def show_recent_commits(
    config: shell_interface.Config,
    max_entries: int = 20,
    show_files_changed: bool = False,
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
    ## `--stat` = list files changed and insertion/deletion counts per commit.
    ## `-n` = limit to the most recent N entries.
    cmd_show_recent_commits = [
        "git",
        "log",
        "--oneline",
        "--decorate",
        "-n",
        str(max_entries),
    ]
    if show_files_changed:
        cmd_show_recent_commits.append("--stat")
    shell_interface.run_cmd(
        config=config,
        cmd=cmd_show_recent_commits,
    )


def show_diff(
    config: shell_interface.Config,
    path: str | None = None,
) -> None:
    """Show all local changes vs HEAD (staged, unstaged, and uncommitted)."""
    repo_state.require_repo()
    shell_interface.log_step("showing local changes vs HEAD")
    cmd = ["git", "diff", "HEAD"]
    if path:
        cmd += ["--", path]
    shell_interface.run_cmd(config=config, cmd=cmd)


def show_diff_committed(
    config: shell_interface.Config,
    base: str | None = None,
    name_only: bool = False,
    no_fetch: bool = False,
    path: str | None = None,
) -> None:
    """Show all committed changes on the current branch vs a base branch; fetches first by default."""
    repo_state.require_repo()
    remote = repo_state.get_default_remote_name()
    if not no_fetch:
        shell_interface.log_step(f"fetching from {remote}")
        shell_interface.run_cmd(
            config=config,
            cmd=["git", "fetch", "--no-recurse-submodules", "--quiet", remote],
        )
    if base:
        if "/" not in base:
            shell_interface.kill("base must be remote-qualified, e.g. origin/main")
        remote_base = base
    else:
        inferred = repo_state.get_default_branch_name()
        if not inferred:
            shell_interface.kill("could not infer default branch; pass base explicitly, e.g. origin/main")
        remote_base = f"{remote}/{inferred}"
    branch = repo_state.current_branch()
    base_branch = remote_base.split("/", 1)[-1]
    if branch == base_branch:
        shell_interface.kill(
            f"already on '{base_branch}'; show-diff-committed compares a feature branch to its base"
            "; use show-diff-last N for commit-range diffs"
        )
    shell_interface.log_step(f"showing committed changes vs '{remote_base}'")
    cmd = ["git", "diff", f"{remote_base}...HEAD"]
    if name_only:
        cmd.append("--name-only")
    if path:
        cmd += ["--", path]
    shell_interface.run_cmd(config=config, cmd=cmd)


def show_commit(
    config: shell_interface.Config,
    commit: str,
) -> None:
    """Show the message and diff introduced by a specific commit."""
    repo_state.require_repo()
    shell_interface.log_step(f"showing changes introduced by {commit}")
    shell_interface.run_cmd(config=config, cmd=["git", "show", commit])


def show_diff_last(
    config: shell_interface.Config,
    num_commits: int,
    include_uncommitted: bool = False,
    path: str | None = None,
) -> None:
    """Show changes over the last N commits, optionally including uncommitted local changes."""
    repo_state.require_repo()
    if num_commits < 1:
        shell_interface.kill("num_commits must be at least 1")
    shell_interface.bind_var(
        var_name="num_commits",
        var_value=str(num_commits),
    )
    if include_uncommitted:
        shell_interface.log_step(f"showing changes over last {num_commits} commits including local changes")
        cmd = ["git", "diff", f"HEAD~{num_commits}"]
    else:
        shell_interface.log_step(f"showing committed changes over last {num_commits} commits")
        cmd = ["git", "diff", f"HEAD~{num_commits}", "HEAD"]
    if path:
        cmd += ["--", path]
    shell_interface.run_cmd(config=config, cmd=cmd)


def show_submodules_status(
    _config: shell_interface.Config,
) -> None:
    """Print the SHA and initialisation status of each submodule, if any."""
    repo_state.require_repo()
    ## `submodule status` prints one line per submodule:
    ##   <SHA> <path> (<describe>)
    ## A leading `-` means not initialized; `+` means the checked-out SHA
    ## differs from what the parent repo recorded; ` ` means up to date.
    cmd_submodule_status = [
        "git",
        "submodule",
        "status",
    ]
    submodules_output = shell_interface.query_cmd(
        cmd=cmd_submodule_status,
        error_on_failure=False,
    )
    if submodules_output:
        submodule_lines = submodules_output.splitlines()
    else:
        submodule_lines = [
            "no submodules or not initialized",
        ]
    for line in submodule_lines:
        shell_interface.log_result(line)


## } MODULE
