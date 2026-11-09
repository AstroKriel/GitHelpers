## { MODULE

##
## === DEPENDENCIES
##

## stdlib
from dataclasses import dataclass
from pathlib import Path

## personal
from huginn import manage_log, manage_shell

##
## === CACHED FACTS
## facts about the repo in the current directory that no command changes during a run; each is queried on
## first use and reused after that. Facts that commands do change (branch, upstream, worktrees) are queried
## every time they are asked for.
##


@dataclass
class _CachedFacts:
    directory: Path
    repo_root: Path
    git_dir: Path
    remote_names: list[str] | None = None


_cached_facts: _CachedFacts | None = None


def reset_state() -> None:
    """Forget every cached fact, so the next lookup queries git again."""
    global _cached_facts
    _cached_facts = None


def _get_cached_facts() -> _CachedFacts:
    """Return the cached facts for the current directory; exit with an error if it is not inside a git repo."""
    global _cached_facts
    directory = Path.cwd()
    if (_cached_facts is not None) and (_cached_facts.directory == directory):
        return _cached_facts
    ## both paths come back absolute, one per line; `--absolute-git-dir` is the worktree's own git dir,
    ## which is where an in-progress merge or rebase leaves its marker files.
    cmd_find_repo = [
        "git",
        "rev-parse",
        "--show-toplevel",
        "--absolute-git-dir",
    ]
    output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_find_repo,
        raise_error=False,
    )
    repo_paths = output.splitlines()
    if len(repo_paths) != 2:
        manage_log.exit_with_error("not inside a git repo")
    _cached_facts = _CachedFacts(
        directory=directory,
        repo_root=Path(repo_paths[0]),
        git_dir=Path(repo_paths[1]),
    )
    return _cached_facts


def require_repo() -> None:
    """Exit with an error if the current directory is not inside a git repo."""
    _get_cached_facts()


def get_remote_names() -> list[str]:
    """Return the names of the configured remotes, in the order git lists them."""
    cached_facts = _get_cached_facts()
    if cached_facts.remote_names is None:
        cmd_list_remotes = [
            "git",
            "remote",
        ]
        output = manage_shell.query_cmd_and_capture_output(
            cmd_parts=cmd_list_remotes,
            raise_error=True,
        )
        cached_facts.remote_names = output.splitlines()
    return cached_facts.remote_names


##
## === LIVE FACTS
##


def list_worktrees() -> list[dict[str, str]]:
    """Parse `git worktree list --porcelain` into a list of dicts with path, head, and branch keys.

    Detached and bare worktrees omit the branch key. Index 0 is always the main (non-linked) worktree.
    """
    require_repo()
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
    current_worktree: dict[str, str] = {}
    for line in output.splitlines():
        if line.startswith("worktree "):
            current_worktree = {"path": line[len("worktree "):]}
        elif line.startswith("HEAD "):
            current_worktree["head"] = line[len("HEAD "):]
        elif line.startswith("branch "):
            branch_ref = line[len("branch "):]
            current_worktree["branch"] = branch_ref.removeprefix("refs/heads/")
        elif (line == "") and current_worktree:
            worktrees.append(current_worktree)
            current_worktree = {}
    if current_worktree:
        worktrees.append(current_worktree)
    return worktrees


def branches_with_worktrees() -> set[str]:
    """Return branch names currently checked out in any worktree, including the main one.

    A branch checked out in a worktree may have real, uncommitted or untracked work sitting
    in that worktree that no commit-ancestry check (e.g. `git branch --merged`) can see.
    """
    return {_worktree["branch"] for _worktree in list_worktrees() if "branch" in _worktree}


def find_default_remote_name() -> str | None:
    """Return 'origin' if it exists, otherwise the first remote, or None if no remote is configured."""
    ## prefer 'origin': it's the conventional name git uses when you clone.
    remote_names = get_remote_names()
    if "origin" in remote_names:
        return "origin"
    elif remote_names:
        return remote_names[0]
    else:
        return None


def get_default_remote_name() -> str:
    """Return 'origin' if it exists, otherwise the first remote; exit with an error if no remote is configured."""
    default_remote_name = find_default_remote_name()
    if default_remote_name is None:
        manage_log.exit_with_error("no remotes configured (try: git remote add origin <url>)")
    manage_log.log_outcome(
        f"using '{default_remote_name}' as the default remote",
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    return default_remote_name


def get_default_branch_name(
    *,
    remote_name: str,
) -> str | None:
    """Return the default branch the remote advertises, or None if it advertises none."""
    require_repo()
    ## `refs/remotes/<remote>/HEAD` is a symbolic ref that the remote sets to
    ## point at its default branch (e.g. refs/remotes/origin/HEAD -> origin/main).
    ## It's populated by `git remote set-head` or automatically on clone.
    ## raise_error=False returns "" when the ref doesn't exist; -q suppresses git's own error output.
    cmd_read_remote_head = [
        "git",
        "symbolic-ref",
        "-q",
        f"refs/remotes/{remote_name}/HEAD",
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
        return None
    ## strip the leading "refs/remotes/<remote>/" to get just the branch name.
    default_branch_name = ref_value.removeprefix(f"refs/remotes/{remote_name}/")
    manage_log.log_outcome(
        f"remote default branch is '{default_branch_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    return default_branch_name


@dataclass(frozen=True)
class Upstream:
    """The branch a local branch pulls from and pushes to; `remote_name` is '.' when it is another local branch."""
    remote_name: str
    branch_name: str

    @property
    def is_local(
        self,
    ) -> bool:
        return self.remote_name == "."

    @property
    def ref_name(
        self,
    ) -> str:
        """The name git commands take for the upstream: 'origin/main', or just 'main' for a local branch."""
        if self.is_local:
            return self.branch_name
        else:
            return f"{self.remote_name}/{self.branch_name}"


def find_upstream(
    *,
    branch_name: str,
) -> Upstream | None:
    """Return the upstream of a local branch, or None if it has none."""
    require_repo()
    ## git stores the upstream as two separate settings, the remote and the branch on it, so reading them
    ## directly avoids splitting 'origin/fix/my-bug' at a guessed slash; `%00` separates them in the output.
    cmd_read_upstream = [
        "git",
        "for-each-ref",
        "--format=%(upstream:remotename)%00%(upstream:remoteref)",
        f"refs/heads/{branch_name}",
    ]
    output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_read_upstream,
        raise_error=True,
    )
    remote_name, _, remote_ref = output.partition("\0")
    if not remote_name:
        return None
    return Upstream(
        remote_name=remote_name,
        branch_name=remote_ref.removeprefix("refs/heads/"),
    )


def find_current_branch_name() -> str | None:
    """Return the current branch name, or None if HEAD is detached."""
    require_repo()
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
        return None
    return head_ref.removeprefix("refs/heads/")


def find_head_commit_hash() -> str | None:
    """Return the full hash of the commit HEAD points to, or None in a repo with no commits yet."""
    require_repo()
    cmd_get_head_commit_hash = [
        "git",
        "rev-parse",
        "--verify",
        "--quiet",
        "HEAD",
    ]
    head_commit_hash = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_get_head_commit_hash,
        raise_error=False,
    )
    if not head_commit_hash:
        return None
    return head_commit_hash


def find_in_progress_operation() -> str | None:
    """Return the git operation stopped part-way in this worktree (e.g. 'rebase'), or None if there is none."""
    ## git marks each stopped operation with a file or folder in the worktree's git dir; reading the
    ## folder needs no query.
    git_dir = _get_cached_facts().git_dir
    operation_markers = {
        "merge": ["MERGE_HEAD"],
        "rebase": ["rebase-merge", "rebase-apply"],
        "cherry-pick": ["CHERRY_PICK_HEAD"],
        "revert": ["REVERT_HEAD"],
        "bisect": ["BISECT_LOG"],
    }
    for _operation_name, _marker_names in operation_markers.items():
        if any((git_dir / _marker_name).exists() for _marker_name in _marker_names):
            return _operation_name
    return None


def check_worktree_is_clean() -> bool:
    """Return True if the worktree has no staged or unstaged changes to tracked files."""
    require_repo()
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
    unstaged_changes_exist = manage_shell.query_cmd_and_discard_output(cmd_parts=cmd_check_unstaged) != 0
    staged_changes_exist = manage_shell.query_cmd_and_discard_output(cmd_parts=cmd_check_staged) != 0
    return (not unstaged_changes_exist) and (not staged_changes_exist)


def ensure_clean_worktree(
    *,
    allow_dirty: bool,
) -> None:
    """Exit with an error if the worktree has uncommitted or unstaged changes, unless `allow_dirty`."""
    if allow_dirty:
        manage_log.log_outcome(
            "clean worktree check skipped (--allow-dirty)",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
        return
    if not check_worktree_is_clean():
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
    require_repo()
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


def get_attached_branch_name() -> str:
    """Return the current branch name; exit with an error if HEAD is detached."""
    manage_log.log_task("checking whether HEAD is attached to a branch")
    branch_name = find_current_branch_name()
    if branch_name is None:
        manage_log.exit_with_error("operation not valid in detached HEAD state")
    manage_log.log_outcome(
        f"on branch '{branch_name}'",
        status=manage_log.OutcomeStatus.SUCCESS,
    )
    return branch_name


##
## === SNAPSHOT
##


@dataclass(frozen=True)
class RepoStateSnapshot:
    """Every fact git_helpers reads about the repo in the current directory, collected at one moment."""
    repo_root: Path
    git_dir: Path
    remote_names: list[str]
    default_remote_name: str | None
    remote_default_branch_name: str | None
    current_branch_name: str | None
    head_commit_hash: str | None
    upstream: Upstream | None
    worktree_is_clean: bool
    in_progress_operation: str | None
    worktree_paths: list[str]


def collect_repo_state() -> RepoStateSnapshot:
    """Read every fact about the repo in the current directory; never exits on what it finds."""
    cached_facts = _get_cached_facts()
    default_remote_name = find_default_remote_name()
    if default_remote_name is None:
        remote_default_branch_name = None
    else:
        remote_default_branch_name = get_default_branch_name(remote_name=default_remote_name)
    current_branch_name = find_current_branch_name()
    if current_branch_name is None:
        upstream = None
    else:
        upstream = find_upstream(branch_name=current_branch_name)
    return RepoStateSnapshot(
        repo_root=cached_facts.repo_root,
        git_dir=cached_facts.git_dir,
        remote_names=get_remote_names(),
        default_remote_name=default_remote_name,
        remote_default_branch_name=remote_default_branch_name,
        current_branch_name=current_branch_name,
        head_commit_hash=find_head_commit_hash(),
        upstream=upstream,
        worktree_is_clean=check_worktree_is_clean(),
        in_progress_operation=find_in_progress_operation(),
        worktree_paths=[_worktree["path"] for _worktree in list_worktrees()],
    )


## } MODULE
