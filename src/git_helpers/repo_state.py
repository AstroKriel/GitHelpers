## { MODULE

##
## === DEPENDENCIES
##

## local
from git_helpers import shell_interface

##
## === INTERNAL HELPERS
##


def require_repo() -> None:
    """Exit with an error if the cwd is not inside a git repository."""
    ## `rev-parse --is-inside-work-tree` is the canonical way to test whether
    ## the cwd is anywhere inside a git repo (works from any subdirectory).
    cmd_check_repo = [
        "git",
        "rev-parse",
        "--is-inside-work-tree",
    ]
    if shell_interface.probe_cmd(cmd_check_repo) != 0:
        shell_interface.kill("not inside a git repo")


def require_remote() -> None:
    """Exit with an error if no remotes are configured."""
    require_repo()
    ## `git remote` with no args prints one remote name per line; empty output
    ## means no remotes have been added yet.
    cmd_list_remotes = [
        "git",
        "remote",
    ]
    remotes = shell_interface.query_cmd(cmd=cmd_list_remotes)
    if not remotes:
        shell_interface.kill("no remotes configured (try: git remote add origin <url>)")


def get_default_remote_name() -> str:
    """Return the name of the default remote, preferring 'origin' if it exists."""
    require_remote()
    ## prefer 'origin' — it's the conventional name git uses when you clone.
    ## `remote get-url` succeeds only if the remote actually exists.
    cmd_check_origin = [
        "git",
        "remote",
        "get-url",
        "origin",
    ]
    if shell_interface.probe_cmd(cmd_check_origin) == 0:
        shell_interface.log_outcome("selecting 'origin' as default remote")
        return "origin"
    ## no 'origin'; fall back to whatever remote was configured first.
    cmd_list_remotes = [
        "git",
        "remote",
    ]
    remotes = shell_interface.query_cmd(cmd=cmd_list_remotes).splitlines()
    if remotes:
        shell_interface.log_outcome(f"selecting first configured remote: {remotes[0]}")
        return remotes[0]
    shell_interface.kill("no remotes configured (try: git remote add origin <url>)")


def get_default_branch_name() -> str:
    """Return the remote's advertised default branch name, or an empty string if unknown."""
    require_remote()
    remote_name = get_default_remote_name()
    ## `refs/remotes/<remote>/HEAD` is a symbolic ref that the remote sets to
    ## point at its default branch (e.g. refs/remotes/origin/HEAD -> origin/main).
    ## It's populated by `git remote set-head` or automatically on clone.
    ## `-q` suppresses the error if the ref doesn't exist; we check stdout instead.
    ## error_on_failure=False returns "" when the ref doesn't exist; -q suppresses git's own error output.
    cmd_read_remote_head = [
        "git",
        "symbolic-ref",
        "-q",
        f"refs/remotes/{remote_name}/HEAD",
    ]
    ref_value = shell_interface.query_cmd(
        cmd=cmd_read_remote_head,
        error_on_failure=False,
    )
    if not ref_value:
        shell_interface.log_outcome("no remote default branch advertised")
        return ""
    ## strip the leading "refs/remotes/<remote>/" to get just the branch name.
    branch_name = ref_value.removeprefix(f"refs/remotes/{remote_name}/")
    shell_interface.log_outcome(f"remote default branch is '{branch_name}'")
    return branch_name


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
    return shell_interface.probe_cmd(cmd_check_upstream) == 0


def current_branch() -> str:
    """Return the current branch name, or 'DETACHED@<sha>' in detached HEAD state."""
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
    branch_name = shell_interface.query_cmd(cmd=cmd_get_branch_name)
    if branch_name == "HEAD":
        ## detached HEAD: no branch name is available, so use the short SHA instead.
        ## a SHA (Secure Hash Algorithm) is the unique 40-hex-character fingerprint
        ## git assigns to every commit; `--short` trims it to 7 chars for readability.
        cmd_get_short_sha = [
            "git",
            "rev-parse",
            "--short",
            "HEAD",
        ]
        short_sha = shell_interface.query_cmd(cmd=cmd_get_short_sha)
        shell_interface.log_outcome(f"detached HEAD at {short_sha}")
        return f"DETACHED@{short_sha}"
    shell_interface.log_outcome(f"on branch '{branch_name}'")
    return branch_name


def ensure_clean_worktree(
    config: shell_interface.Config,
) -> None:
    """Exit with an error if the worktree has uncommitted or unstaged changes."""
    require_repo()
    if config.allow_dirty:
        shell_interface.log_outcome("continuing despite dirty worktree (--allow-dirty)")
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
    has_unstaged_changes = shell_interface.probe_cmd(cmd_check_unstaged) != 0
    has_staged_changes = shell_interface.probe_cmd(cmd_check_staged) != 0
    is_dirty = has_unstaged_changes or has_staged_changes
    if is_dirty:
        shell_interface.kill("working tree not clean (stash/commit first). Try: git status --short")
    shell_interface.log_outcome("worktree is clean")


def is_detached() -> bool:
    """Return True if HEAD is not pointing at a branch (detached HEAD state)."""
    require_repo()
    shell_interface.log_step("checking whether HEAD is attached to a branch")
    ## `symbolic-ref HEAD` prints the full ref name (e.g. refs/heads/main) when
    ## on a branch, and exits non-zero (printing nothing) in detached HEAD state.
    ## `-q` suppresses the error message so we can check stdout cleanly.
    cmd_get_head_ref = [
        "git",
        "symbolic-ref",
        "-q",
        "HEAD",
    ]
    head_ref = shell_interface.query_cmd(cmd=cmd_get_head_ref, error_on_failure=False)
    shell_interface.bind_var(
        var_name="head_ref",
        var_value=head_ref or "<empty>",
    )
    if not head_ref:
        shell_interface.log_outcome("HEAD is detached (not on any branch)")
        return True
    shell_interface.log_outcome(f"HEAD is attached to branch '{head_ref.removeprefix('refs/heads/')}'")
    return False


def require_attached() -> None:
    """Exit with an error if HEAD is in detached state."""
    ## many operations (push, sync, branch deletion) don't make sense without
    ## a named branch to act on; detached HEAD is a commit-only state.
    if is_detached():
        shell_interface.kill("operation not valid in detached HEAD state")


## } MODULE
