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


def _detect_default_branch_from_local(
    path: str,
) -> str | None:
    """Detect the default branch of a cloned repo via origin/HEAD; returns None if not set."""
    ## symbolic-ref gives e.g. "origin/main"; strip the remote prefix to get just "main".
    cmd_detect_local_branch = [
        "git",
        "-C",
        path,
        "symbolic-ref",
        "--short",
        "refs/remotes/origin/HEAD",
    ]
    output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_detect_local_branch,
        raise_error=False,
    )
    if not output:
        return None
    _, _, branch_name = output.partition("/")
    return branch_name or None


def _read_gitmodules_branch(
    submodule_path: str,
) -> str | None:
    """Read the tracked branch for a submodule from .gitmodules; returns None if not configured."""
    ## .gitmodules keys submodules by name, not path; find the name whose path matches first.
    ## `--get-regexp` output format: "submodule.<name>.path <value>" (one entry per line).
    cmd_read_gitmodules_paths = [
        "git",
        "config",
        "-f",
        ".gitmodules",
        "--get-regexp",
        r"submodule\..*\.path",
    ]
    path_entries = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_read_gitmodules_paths,
        raise_error=False,
    )
    for line in path_entries.splitlines():
        key, _, value = line.partition(" ")
        if value.strip() != submodule_path:
            continue
        ## key is "submodule.<name>.path"; strip prefix and suffix to extract <name>.
        ## avoids splitting on "." so names containing dots are handled correctly.
        submodule_name = key.removeprefix("submodule.").removesuffix(".path")
        cmd_read_gitmodules_branch = [
            "git",
            "config",
            "-f",
            ".gitmodules",
            f"submodule.{submodule_name}.branch",
        ]
        branch_name = manage_shell.query_cmd_and_capture_output(
            cmd_parts=cmd_read_gitmodules_branch,
            raise_error=False,
        )
        return branch_name or None
    return None


def _detect_default_branch_from_url(
    url: str,
) -> str | None:
    """Query a remote URL for its default branch without cloning; returns None if undetectable."""
    ## `git ls-remote --symref <url> HEAD` prints "ref: refs/heads/<branch>\tHEAD" on the first
    ## line when the remote has HEAD pointing to a branch, which most hosted repos do.
    cmd_detect_remote_branch = [
        "git",
        "ls-remote",
        "--symref",
        url,
        "HEAD",
    ]
    output = manage_shell.query_cmd_and_capture_output(
        cmd_parts=cmd_detect_remote_branch,
        raise_error=False,
    )
    for line in output.splitlines():
        if line.startswith("ref:") and ("HEAD" in line):
            ## format: "ref: refs/heads/main\tHEAD"
            ref_part = line.split("\t")[0].replace("ref:", "").strip()
            _, _, branch_name = ref_part.rpartition("/")
            return branch_name or None
    return None


##
## === SUBMODULE COMMANDS
##


def cmd_update_submodules() -> None:
    """Pull the latest commits for all submodules from their tracked branches."""
    repo_state.require_repo()
    manage_log.log_task("updating all submodules to latest on their tracked branch")
    ## `--remote` fetches from each submodule's remote and checks out the latest
    ## commit on the tracked branch (set in .gitmodules via `branch = main`).
    ## `--recursive` handles nested submodules.
    cmd_pull_submodule = [
        "git",
        "submodule",
        "update",
        "--remote",
        "--recursive",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_pull_submodule)
    manage_log.log_outcome(
        "all submodules updated to latest",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


def cmd_fix_submodule(
    *,
    submodule_path: str,
    branch_name: str | None = None,
) -> None:
    """Repair a submodule stuck in detached HEAD: checkout default branch, pull, bump parent pointer."""
    repo_state.require_repo()
    if branch_name is None:
        manage_log.log_task("reading tracked branch from .gitmodules")
        branch_name = _read_gitmodules_branch(submodule_path)
    if branch_name is None:
        manage_log.log_task("detecting default branch of the submodule")
        branch_name = _detect_default_branch_from_local(submodule_path)
    if branch_name is None:
        manage_log.exit_with_error(
            f"could not detect tracked branch for '{submodule_path}'; "
            "pass it explicitly: fix-submodule <path> <branch>",
        )
    manage_log.log_task(f"checking out {branch_name} inside the submodule")
    ## `git -C <path>` runs the command as if cwd were <path>; avoids needing
    ## to actually cd in and out of the submodule directory.
    cmd_checkout_branch = [
        "git",
        "-C",
        submodule_path,
        "checkout",
        branch_name,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_checkout_branch)
    manage_log.log_task("pulling latest commits inside the submodule")
    cmd_pull_submodule = [
        "git",
        "-C",
        submodule_path,
        "pull",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_pull_submodule)
    manage_log.log_task("staging updated submodule pointer in parent repo")
    ## staging the submodule path tells the parent to record the new HEAD commit hash.
    cmd_stage_submodule = [
        "git",
        "add",
        submodule_path,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_stage_submodule)
    manage_log.log_task("committing updated pointer in parent repo")
    cmd_commit_pointer = [
        "git",
        "commit",
        "-m",
        f"fix: update {submodule_path} pointer after repair",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_commit_pointer)
    manage_log.log_outcome(
        f"repaired '{submodule_path}' and bumped parent pointer",
        status=manage_log.OutcomeStatus.SUCCESS,
        items={"branch": branch_name},
    )


def cmd_add_submodule(
    *,
    url: str,
    local_name: str,
    branch_name: str | None = None,
) -> None:
    """Add a new submodule, pin it to track its default branch, and commit .gitmodules + pointer."""
    repo_state.require_repo()
    if branch_name is None:
        manage_log.log_task("detecting default branch from remote")
        branch_name = _detect_default_branch_from_url(url)
        if branch_name is None:
            manage_log.exit_with_error(
                f"could not detect default branch for '{url}'; "
                "pass it explicitly: add-submodule <url> <name> <branch>",
            )
    manage_log.log_task("adding submodule")
    ## `submodule add` clones the remote into <local_name> and registers it in .gitmodules.
    cmd_add_submodule = [
        "git",
        "submodule",
        "add",
        url,
        local_name,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_add_submodule)
    manage_log.log_task(f"setting tracked branch to {branch_name} in .gitmodules")
    ## record `branch = <branch>` so `git submodule update --remote` knows which
    ## branch to follow when pulling new commits.
    cmd_set_gitmodules_branch = [
        "git",
        "config",
        "-f",
        ".gitmodules",
        f"submodule.{local_name}.branch",
        branch_name,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_set_gitmodules_branch)
    manage_log.log_task("staging .gitmodules and submodule pointer")
    cmd_stage_gitmodules = [
        "git",
        "add",
        ".gitmodules",
        local_name,
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_stage_gitmodules)
    manage_log.log_task("committing")
    cmd_commit_submodule = [
        "git",
        "commit",
        "-m",
        f"add {local_name} submodule",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_commit_submodule)
    manage_log.log_outcome(
        f"added submodule '{local_name}' tracking {branch_name}",
        status=manage_log.OutcomeStatus.SUCCESS,
        items={"url": url},
    )


## } MODULE
