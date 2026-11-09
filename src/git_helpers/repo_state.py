## { MODULE

##
## === DEPENDENCIES
##

## personal
from huginn import manage_log, manage_shell

##
## === INTERNAL HELPERS
##


def list_worktrees() -> list[dict[str, str]]:
    """Parse `git worktree list --porcelain` into a list of dicts with path, head, and branch keys.

    Detached and bare worktrees omit the branch key. Index 0 is always the main (non-linked) worktree.
    """
    cmd_list_worktrees = [
        "git",
        "worktree",
        "list",
        "--porcelain",
    ]
    output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_list_worktrees,
        raise_error=True,
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


def branches_with_worktrees() -> set[str]:
    """Return branch names currently checked out in any worktree, including the main one.

    A branch checked out in a worktree may have real, uncommitted or untracked work sitting
    in that worktree that no commit-ancestry check (e.g. `git branch --merged`) can see.
    """
    return {worktree["branch"] for worktree in list_worktrees() if "branch" in worktree}


def require_repo() -> None:
    """Exit with an error if the cwd is not inside a git repository."""
    ## `rev-parse --is-inside-work-tree` is the canonical way to test whether
    ## the cwd is anywhere inside a git repo (works from any subdirectory).
    cmd_check_repo = [
        "git",
        "rev-parse",
        "--is-inside-work-tree",
    ]
    if manage_shell.query_cmd_and_discard_output(cmd_parts=cmd_check_repo) != 0:
        manage_log.exit_with_error("not inside a git repo")


def has_remote() -> bool:
    """Return True if at least one remote is configured."""
    require_repo()
    cmd_list_remotes = [
        "git",
        "remote",
    ]
    remotes = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_list_remotes,
        raise_error=False,
    )
    return bool(remotes.strip())


def require_remote() -> None:
    """Exit with an error if no remotes are configured."""
    if not has_remote():
        manage_log.exit_with_error("no remotes configured (try: git remote add origin <url>)")


def get_default_remote_name() -> str:
    """Return the name of the default remote, preferring 'origin' if it exists."""
    require_remote()
    ## prefer 'origin': it's the conventional name git uses when you clone.
    ## `remote get-url` succeeds only if the remote actually exists.
    cmd_check_origin = [
        "git",
        "remote",
        "get-url",
        "origin",
    ]
    if manage_shell.query_cmd_and_discard_output(cmd_parts=cmd_check_origin) == 0:
        manage_log.log_outcome(
            "selecting 'origin' as default remote",
            status=manage_log.OutcomeStatus.SUCCESS,
        )
        return "origin"
    ## no 'origin'; fall back to whatever remote was configured first.
    cmd_list_remotes = [
        "git",
        "remote",
    ]
    remotes = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_list_remotes,
        raise_error=True,
    ).splitlines()
    if remotes:
        manage_log.log_outcome(
            f"selecting first configured remote: {remotes[0]}",
            status=manage_log.OutcomeStatus.SUCCESS,
        )
        return remotes[0]
    manage_log.exit_with_error("no remotes configured (try: git remote add origin <url>)")


def get_default_branch_name() -> str:
    """Return the remote's advertised default branch name, or an empty string if unknown."""
    require_remote()
    default_remote_name = get_default_remote_name()
    ## `refs/remotes/<remote>/HEAD` is a symbolic ref that the remote sets to
    ## point at its default branch (e.g. refs/remotes/origin/HEAD -> origin/main).
    ## It's populated by `git remote set-head` or automatically on clone.
    ## `-q` suppresses the error if the ref doesn't exist; we check stdout instead.
    ## raise_error=False returns "" when the ref doesn't exist; -q suppresses git's own error output.
    cmd_read_remote_head = [
        "git",
        "symbolic-ref",
        "-q",
        f"refs/remotes/{default_remote_name}/HEAD",
    ]
    ref_value = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_read_remote_head,
        raise_error=False,
    )
    if not ref_value:
        manage_log.log_outcome(
            "no remote default branch advertised",
            status=manage_log.OutcomeStatus.WARNING,
        )
        return ""
    ## strip the leading "refs/remotes/<remote>/" to get just the branch name.
    default_branch_name = ref_value.removeprefix(f"refs/remotes/{default_remote_name}/")
    manage_log.log_outcome(
        f"remote default branch is '{default_branch_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    return default_branch_name


def has_upstream() -> bool:
    """Return True if the current branch has a configured upstream tracking ref."""
    require_repo()
    ## `@{u}` is git shorthand for the upstream of the current branch.
    ## `--abbrev-ref --symbolic-full-name` prints it as e.g. "origin/main".
    ## The command exits non-zero if no upstream is configured.
    cmd_check_upstream = [
        "git",
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    ]
    return manage_shell.query_cmd_and_discard_output(cmd_parts=cmd_check_upstream) == 0


def get_upstream_branch_name() -> str:
    """Return the branch portion of the upstream ref (e.g. 'main' from 'origin/main')."""
    require_repo()
    manage_log.log_task("reading upstream branch name")
    ## `@{u}` resolves to the full upstream ref, e.g. 'origin/development'.
    ## split on the first '/' and take the remainder to get just the branch name;
    ## this handles branch names that themselves contain slashes (e.g. 'fix/my-bug').
    cmd_get_upstream = [
        "git",
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    ]
    upstream_ref = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_get_upstream,
        raise_error=True,
    )
    branch_name = upstream_ref.split("/", 1)[1]
    manage_log.log_outcome(
        f"upstream branch is '{branch_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    return branch_name


def current_branch() -> str:
    """Return the current branch name, or 'DETACHED@<hash>' in detached HEAD state."""
    require_repo()
    ## `rev-parse --abbrev-ref HEAD` prints the branch name, or the literal
    ## string "HEAD" when in detached HEAD state (i.e. checked out to a commit
    ## rather than a branch).
    cmd_get_branch_name = [
        "git",
        "rev-parse",
        "--abbrev-ref",
        "HEAD",
    ]
    current_branch_name = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_get_branch_name,
        raise_error=True,
    )
    if current_branch_name == "HEAD":
        ## detached HEAD: no branch name is available, so use the commit hash prefix instead.
        ## a commit hash is the unique 40-character hex fingerprint git assigns to every
        ## commit; `--short` trims it to a 7-character prefix for readability.
        cmd_get_commit_hash_prefix = [
            "git",
            "rev-parse",
            "--short",
            "HEAD",
        ]
        commit_hash_prefix = manage_shell.query_cmd_and_capture_output(
            cmd_parts=cmd_get_commit_hash_prefix,
            raise_error=True,
        )
        manage_log.log_outcome(
            f"detached HEAD at {commit_hash_prefix}",
            status=manage_log.OutcomeStatus.SUCCESS,
        )
        return f"DETACHED@{commit_hash_prefix}"
    manage_log.log_outcome(
        f"on branch '{current_branch_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    return current_branch_name


def ensure_clean_worktree(
    *,
    allow_dirty: bool,
) -> None:
    """Exit with an error if the worktree has uncommitted or unstaged changes, unless `allow_dirty`."""
    require_repo()
    if allow_dirty:
        manage_log.log_outcome(
            "clean worktree check skipped (--allow-dirty)",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
        return
    ## `git diff --quiet` exits non-zero if there are unstaged changes.
    ## `git diff --cached --quiet` exits non-zero if there are staged-but-uncommitted changes.
    ## both must pass for the worktree to be considered clean.
    cmd_check_unstaged = [
        "git",
        "diff",
        "--quiet",
    ]
    cmd_check_staged = [
        "git",
        "diff",
        "--cached",
        "--quiet",
    ]
    has_unstaged_changes = manage_shell.query_cmd_and_discard_output(cmd_parts=cmd_check_unstaged) != 0
    has_staged_changes = manage_shell.query_cmd_and_discard_output(cmd_parts=cmd_check_staged) != 0
    is_dirty = has_unstaged_changes or has_staged_changes
    if is_dirty:
        manage_log.exit_with_error("working tree not clean (stash/commit first). Try: git status --short")
    manage_log.log_outcome(
        "worktree is clean",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


def remote_branch_exists(
    remote_name: str,
    branch_name: str,
) -> bool:
    """Return True if branch_name exists on remote_name."""
    ## `ls-remote --exit-code --heads` exits non-zero when the ref is absent,
    ## so we can use its exit code directly without parsing output.
    cmd_check_remote_branch = [
        "git",
        "ls-remote",
        "--exit-code",
        "--heads",
        remote_name,
        branch_name,
    ]
    return manage_shell.query_cmd_and_discard_output(cmd_parts=cmd_check_remote_branch) == 0


def is_detached() -> bool:
    """Return True if HEAD is not pointing at a branch (detached HEAD state)."""
    require_repo()
    manage_log.log_task("checking whether HEAD is attached to a branch")
    ## `symbolic-ref HEAD` prints the full ref name (e.g. refs/heads/main) when
    ## on a branch, and exits non-zero (printing nothing) in detached HEAD state.
    ## `-q` suppresses the error message so we can check stdout cleanly.
    cmd_get_head_ref = [
        "git",
        "symbolic-ref",
        "-q",
        "HEAD",
    ]
    head_ref = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_get_head_ref,
        raise_error=False,
    )
    if not head_ref:
        manage_log.log_outcome(
            "HEAD is detached (not on any branch)",
            status=manage_log.OutcomeStatus.SUCCESS,
        )
        return True
    manage_log.log_outcome(
        f"HEAD is attached to branch '{head_ref.removeprefix('refs/heads/')}'",
        status=manage_log.OutcomeStatus.SUCCESS,
        items={"head ref": head_ref},
    )
    return False


def require_attached() -> None:
    """Exit with an error if HEAD is in detached state."""
    ## many operations (push, sync, branch deletion) don't make sense without
    ## a named branch to act on; detached HEAD is a commit-only state.
    if is_detached():
        manage_log.exit_with_error("operation not valid in detached HEAD state")


## } MODULE
