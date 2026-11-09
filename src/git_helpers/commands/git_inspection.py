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


def _diff_color_args(
    word_diff: bool,
) -> list[str]:
    """Return the color-related flags shared by all `git diff` commands.

    `--color-words` highlights only the changed tokens inline rather than
    re-flowing the whole line as removed+added; useful for paragraph-per-line
    prose (e.g. LaTeX) where line-based diffs bury the actual edit in noise.
    """
    args = ["--color=always"]
    if word_diff:
        args.append("--color-words")
    return args


##
## === PROBING COMMANDS
##


def _describe(
    value: object,
    *,
    none_text: str,
) -> str:
    if value is None:
        return none_text
    else:
        return str(value)


def show_repo_state() -> None:
    """Print every fact git_helpers reads about the repo in the current directory."""
    manage_log.log_task("reading the repo state")
    repo_state_snapshot = repo_state.collect_repo_state()
    if repo_state_snapshot.remote_names:
        remotes_text = ", ".join(repo_state_snapshot.remote_names)
    else:
        remotes_text = "none"
    if repo_state_snapshot.upstream is None:
        upstream_text = "none"
    else:
        upstream_text = repo_state_snapshot.upstream.ref_name
    if repo_state_snapshot.worktree_is_clean:
        worktree_text = "clean"
    else:
        worktree_text = "has uncommitted changes"
    rows = {
        "repo root": str(repo_state_snapshot.repo_root),
        "git dir": str(repo_state_snapshot.git_dir),
        "remotes": remotes_text,
        "default remote": _describe(repo_state_snapshot.default_remote_name, none_text="none"),
        "remote default branch": _describe(repo_state_snapshot.remote_default_branch_name, none_text="not advertised"),
        "current branch": _describe(repo_state_snapshot.current_branch_name, none_text="none (HEAD is detached)"),
        "HEAD commit": _describe(repo_state_snapshot.head_commit_hash, none_text="none (no commits yet)"),
        "upstream": upstream_text,
        "worktree": worktree_text,
        "in-progress operation": _describe(repo_state_snapshot.in_progress_operation, none_text="none"),
        "worktrees": " ".join(repo_state_snapshot.worktree_paths),
    }
    label_width = max(len(_label) for _label in rows) + 1
    for _label, _value_text in rows.items():
        manage_log.log_return(f"{_label + ':':<{label_width}} {_value_text}")


def show_current_commit_hash() -> None:
    """Print the full commit hash that HEAD currently points to."""
    repo_state.require_repo()
    cmd_show_current_commit_hash = [
        "git",
        "rev-parse",
        "HEAD",
    ]
    current_commit_hash = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_show_current_commit_hash,
        raise_error=True,
    )
    manage_log.log_return(current_commit_hash)


def show_upstream_state() -> None:
    """Print the current branch name, its upstream ref, and the upstream's latest commit."""
    repo_state.require_repo()
    manage_log.log_task("identifying current branch")
    branch_name = repo_state.find_current_branch_name()
    if branch_name is None:
        manage_log.log_outcome(
            "HEAD is detached, so there is no upstream",
            status=manage_log.OutcomeStatus.WARNING,
        )
        return
    manage_log.log_outcome(
        f"on branch '{branch_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    manage_log.log_task("resolving upstream (if any)")
    upstream = repo_state.find_upstream(branch_name=branch_name)
    if upstream is not None:
        upstream_name = upstream.ref_name
        manage_log.log_return(f"upstream:     {upstream_name}")
        manage_log.log_task("showing the latest commit on the upstream")
        ## `-1` limits to one commit; `--format` prints it on one line with its branch and tag labels.
        cmd_show_upstream_commit = [
            "git",
            "log",
            "--format=%C(auto)%h %C(cyan)%as (%ar)%C(reset) %s%C(auto)%d",
            "-1",
            upstream_name,
        ]
        manage_shell.query_cmd_and_show_output(cmd_parts=cmd_show_upstream_commit)
    else:
        manage_log.log_outcome(
            "no upstream configured for current branch",
            status=manage_log.OutcomeStatus.WARNING,
        )


def show_branches_status() -> None:
    """Fetch from remote, then list all local branches with their upstream and ahead/behind counts."""
    repo_state.require_repo()
    manage_log.log_task("refreshing remote-tracking information")
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
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_fetch_prune)
    manage_log.log_task("showing local branches with upstream and ahead/behind")
    ## `-vv` (very verbose) shows the upstream ref and ahead/behind counts
    ## for each branch. `--no-abbrev` prints full hashes so nothing is truncated.
    cmd_show_branch_verbose = [
        "git",
        "branch",
        "-vv",
        "--no-abbrev",
    ]
    manage_shell.query_cmd_and_show_output(cmd_parts=cmd_show_branch_verbose)


def count_ahead_behind() -> None:
    """Print how many commits the current branch is ahead of and behind its upstream."""
    repo_state.require_repo()
    branch_name = repo_state.get_attached_branch_name()
    manage_log.log_task("determining upstream for current branch")
    upstream = repo_state.find_upstream(branch_name=branch_name)
    if upstream is None:
        manage_log.exit_with_error(f"no upstream set for {branch_name}")
    upstream_name = upstream.ref_name
    manage_log.log_outcome(
        f"upstream is '{upstream_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    manage_log.log_task("fetching latest refs from remote")
    ## stay on the superproject; this only compares HEAD to its upstream.
    cmd_fetch_quiet = [
        "git",
        "fetch",
        "--no-recurse-submodules",
        "--quiet",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_fetch_quiet)
    manage_log.log_task("computing ahead/behind vs upstream")
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
    ahead_behind_counts = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_count_ahead_behind,
        raise_error=True,
    )
    ahead_count, behind_count = ahead_behind_counts.split()
    manage_log.log_return(f"ahead: {ahead_count}; behind: {behind_count}")


def show_unpulled_commits() -> None:
    """List commits that exist on the upstream but have not yet been pulled locally."""
    repo_state.require_repo()
    branch_name = repo_state.get_attached_branch_name()
    manage_log.log_task("determining upstream")
    upstream = repo_state.find_upstream(branch_name=branch_name)
    if upstream is None:
        manage_log.exit_with_error(f"no upstream set for {branch_name}")
    upstream_name = upstream.ref_name
    manage_log.log_outcome(
        f"upstream is '{upstream_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    manage_log.log_task("fetching latest from remote")
    ## stay on the superproject; this only lists commits missing on HEAD.
    cmd_fetch_quiet = [
        "git",
        "fetch",
        "--no-recurse-submodules",
        "--quiet",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_fetch_quiet)
    manage_log.log_task("listing commits present upstream but missing locally")
    ## `HEAD..upstream` (two dots) = commits reachable from upstream but NOT
    ## from HEAD (commits that exist on the remote but haven't been pulled yet).
    cmd_show_unpulled = [
        "git",
        "log",
        "--format=%C(auto)%h %C(cyan)%as (%ar)%C(reset) %s%C(auto)%d",
        f"HEAD..{upstream_name}",
    ]
    manage_shell.query_cmd_and_show_output(cmd_parts=cmd_show_unpulled)


def show_local_remotes() -> None:
    """List all configured remotes and their fetch/push URLs."""
    repo_state.require_repo()
    ## `-v` prints both fetch and push URLs for each remote; deduplicate with
    ## a set in case fetch == push (the common case), then sort for stable output.
    cmd_list_remotes = [
        "git",
        "remote",
        "-v",
    ]
    remotes_output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_list_remotes,
        raise_error=True,
    )
    for line in sorted(set(remotes_output.splitlines())):
        manage_log.log_return(line)


def show_commits_on_branch(
    *,
    base: str | None = None,
    show_files_changed: bool = False,
    no_fetch: bool = False,
) -> None:
    """Show commits on the current branch that are not on the base branch; fetches first by default."""
    repo_state.require_repo()
    remote = repo_state.get_default_remote_name()
    if not no_fetch:
        manage_log.log_task(f"fetching from {remote}")
        manage_shell.run_cmd_and_show_output(
            cmd_parts=["git", "fetch", "--no-recurse-submodules", "--quiet", remote],
        )
    if base:
        if "/" not in base:
            manage_log.exit_with_error("base must be remote-qualified, e.g. origin/main")
        remote_base = base
    else:
        inferred = repo_state.get_default_branch_name(remote_name=remote)
        if not inferred:
            manage_log.exit_with_error(
                "could not infer default branch; pass base explicitly, e.g. origin/main",
            )
        remote_base = f"{remote}/{inferred}"
    branch_name = repo_state.find_current_branch_name()
    base_branch = remote_base.split("/", 1)[-1]
    if branch_name == base_branch:
        manage_log.exit_with_error(
            f"already on '{base_branch}'; show-commits-on-branch compares a feature branch to its base",
        )
    if branch_name is None:
        head_label = "detached HEAD"
    else:
        head_label = f"'{branch_name}'"
    manage_log.log_task(f"showing commits on {head_label} not in '{remote_base}'")
    cmd = [
        "git",
        "log",
        f"{remote_base}..HEAD",
        "--format=%C(auto)%h %C(cyan)%as (%ar)%C(reset) %s%C(auto)%d",
    ]
    if show_files_changed:
        cmd.append("--stat")
    manage_shell.query_cmd_and_show_output(cmd_parts=cmd)


def show_recent_commits(
    *,
    max_entries: int = 20,
    show_files_changed: bool = False,
) -> None:
    """Print the most recent N commits on the current branch (default 20)."""
    repo_state.require_repo()
    manage_log.log_task("showing recent commits on current branch")
    ## `--format` = custom one-line format: short commit hash, date, relative age, subject, decorations.
    ## `--stat` = list files changed and insertion/deletion counts per commit.
    ## `-n` = limit to the most recent N entries.
    cmd_show_recent_commits = [
        "git",
        "log",
        "--format=%C(auto)%h %C(cyan)%as (%ar)%C(reset) %s%C(auto)%d",
        "-n",
        str(max_entries),
    ]
    if show_files_changed:
        cmd_show_recent_commits.append("--stat")
    manage_shell.query_cmd_and_show_output(cmd_parts=cmd_show_recent_commits)


def show_diff(
    *,
    path: str | None = None,
    word_diff: bool = False,
) -> None:
    """Show all local changes vs HEAD (staged, unstaged, and uncommitted)."""
    repo_state.require_repo()
    manage_log.log_task("showing local changes vs HEAD")
    cmd = ["git", "diff", *_diff_color_args(word_diff), "HEAD"]
    if path:
        cmd += ["--", path]
    manage_shell.query_cmd_and_show_output(cmd_parts=cmd)


def show_diff_untracked(
    *,
    path: str,
    word_diff: bool = False,
) -> None:
    """Show the diff for an untracked file, as if it were newly added (untracked files have no history to diff)."""
    repo_state.require_repo()
    manage_log.log_task(f"showing diff for untracked file '{path}'")
    ## `--no-index` diffs two paths directly, bypassing git's index, so it works
    ## on files with no history; diffing against /dev/null shows the whole file
    ## as an addition. It exits 1 when a difference is found (the expected
    ## outcome here), so pass `raise_error=False` to avoid treating that as a
    ## command failure.
    cmd = ["git", "diff", *_diff_color_args(word_diff), "--no-index", "/dev/null", path]
    manage_shell.query_cmd_and_show_output(
        cmd_parts=cmd,
        raise_error=False,
    )


def show_diff_committed(
    *,
    base: str | None = None,
    name_only: bool = False,
    no_fetch: bool = False,
    path: str | None = None,
    word_diff: bool = False,
) -> None:
    """Show all committed changes on the current branch vs a base branch; fetches first by default."""
    repo_state.require_repo()
    remote = repo_state.get_default_remote_name()
    if not no_fetch:
        manage_log.log_task(f"fetching from {remote}")
        manage_shell.run_cmd_and_show_output(
            cmd_parts=["git", "fetch", "--no-recurse-submodules", "--quiet", remote],
        )
    if base:
        if "/" not in base:
            manage_log.exit_with_error("base must be remote-qualified, e.g. origin/main")
        remote_base = base
    else:
        inferred = repo_state.get_default_branch_name(remote_name=remote)
        if not inferred:
            manage_log.exit_with_error(
                "could not infer default branch; pass base explicitly, e.g. origin/main",
            )
        remote_base = f"{remote}/{inferred}"
    branch_name = repo_state.find_current_branch_name()
    base_branch = remote_base.split("/", 1)[-1]
    if branch_name == base_branch:
        manage_log.exit_with_error(
            f"already on '{base_branch}'; show-diff-committed compares a feature branch to its base"
            "; use show-diff-n-commits N for commit-range diffs",
        )
    manage_log.log_task(f"showing committed changes vs '{remote_base}'")
    cmd = ["git", "diff", *_diff_color_args(word_diff), f"{remote_base}...HEAD"]
    if name_only:
        cmd.append("--name-only")
    if path:
        cmd += ["--", path]
    manage_shell.query_cmd_and_show_output(cmd_parts=cmd)


def show_commit(
    *,
    commit: str,
    word_diff: bool = False,
) -> None:
    """Show the message and diff introduced by a specific commit."""
    repo_state.require_repo()
    manage_log.log_task(f"showing changes introduced by {commit}")
    cmd = ["git", "show", *_diff_color_args(word_diff), commit]
    manage_shell.query_cmd_and_show_output(cmd_parts=cmd)


def show_commit_info(
    *,
    commit: str,
) -> None:
    """Show the full hash, author date, and subject for a commit; fetches it first if not already local."""
    repo_state.require_repo()
    manage_log.log_task(f"checking whether '{commit}' is available locally")
    cmd_check_local = ["git", "cat-file", "-e", f"{commit}^{{commit}}"]
    if manage_shell.query_cmd_and_discard_output(cmd_parts=cmd_check_local) != 0:
        remote = repo_state.get_default_remote_name()
        manage_log.log_task(f"not found locally; fetching '{commit}' from {remote}")
        manage_shell.run_cmd_and_show_output(cmd_parts=["git", "fetch", remote, commit])
    manage_log.log_task(f"showing info for '{commit}'")
    cmd_show_commit_info = [
        "git",
        "log",
        "-1",
        "--format=%C(auto)%H %C(cyan)%as (%ar)%C(reset) %s%C(auto)%d",
        commit,
    ]
    manage_shell.query_cmd_and_show_output(cmd_parts=cmd_show_commit_info)


def show_diff_last(
    *,
    num_commits: int,
    include_uncommitted: bool = False,
    path: str | None = None,
    word_diff: bool = False,
) -> None:
    """Show changes over the last N commits, optionally including uncommitted local changes."""
    repo_state.require_repo()
    if num_commits < 1:
        manage_log.exit_with_error("num_commits must be at least 1")
    if include_uncommitted:
        manage_log.log_task(f"showing changes over last {num_commits} commits including local changes")
        cmd = ["git", "diff", *_diff_color_args(word_diff), f"HEAD~{num_commits}"]
    else:
        manage_log.log_task(f"showing committed changes over last {num_commits} commits")
        cmd = ["git", "diff", *_diff_color_args(word_diff), f"HEAD~{num_commits}", "HEAD"]
    if path:
        cmd += ["--", path]
    manage_shell.query_cmd_and_show_output(cmd_parts=cmd)


def show_submodules_status() -> None:
    """Print the commit hash and initialisation status of each submodule, if any."""
    repo_state.require_repo()
    ## `submodule status` prints one line per submodule:
    ##   <hash> <path> (<describe>)
    ## A leading `-` means not initialized; `+` means the checked-out commit hash
    ## differs from what the parent repo recorded; ` ` means up to date.
    cmd_submodule_status = [
        "git",
        "submodule",
        "status",
    ]
    submodules_output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_submodule_status,
        raise_error=False,
    )
    if submodules_output:
        submodule_lines = submodules_output.splitlines()
    else:
        submodule_lines = [
            "no submodules or not initialized",
        ]
    for line in submodule_lines:
        manage_log.log_return(line)


## } MODULE
