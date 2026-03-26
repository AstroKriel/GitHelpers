## { MODULE

##
## === DEPENDENCIES
##

## local
from git_helpers import shell_interface, repo_state

##
## === HELPERS
##


def _detect_default_branch_from_local(
    path: str,
) -> str | None:
    """Detect the default branch of a cloned repo via origin/HEAD; returns None if not set."""
    ## symbolic-ref gives e.g. "origin/main"; strip the remote prefix to get just "main".
    cmd_detect_local_branch = ["git", "-C", path, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"]
    result = shell_interface.query_cmd(
        cmd=cmd_detect_local_branch,
        error_on_failure=False,
    )
    if not result:
        return None
    _, _, branch = result.partition("/")
    return branch or None


def _read_gitmodules_branch(
    submodule_path: str,
) -> str | None:
    """Read the tracked branch for a submodule from .gitmodules; returns None if not configured."""
    ## .gitmodules keys submodules by name, not path — find the name whose path matches first.
    ## `--get-regexp` output format: "submodule.<name>.path <value>" (one entry per line).
    cmd_read_gitmodules_paths = ["git", "config", "-f", ".gitmodules", "--get-regexp", r"submodule\..*\.path"]
    path_entries = shell_interface.query_cmd(
        cmd=cmd_read_gitmodules_paths,
        error_on_failure=False,
    )
    for line in path_entries.splitlines():
        key, _, value = line.partition(" ")
        if value.strip() != submodule_path:
            continue
        ## key is "submodule.<name>.path"; strip prefix and suffix to extract <name>.
        ## avoids splitting on "." so names containing dots are handled correctly.
        name = key.removeprefix("submodule.").removesuffix(".path")
        cmd_read_gitmodules_branch = ["git", "config", "-f", ".gitmodules", f"submodule.{name}.branch"]
        branch = shell_interface.query_cmd(
            cmd=cmd_read_gitmodules_branch,
            error_on_failure=False,
        )
        return branch or None
    return None


def _detect_default_branch_from_url(
    url: str,
) -> str | None:
    """Query a remote URL for its default branch without cloning; returns None if undetectable."""
    ## `git ls-remote --symref <url> HEAD` prints "ref: refs/heads/<branch>\tHEAD" on the first
    ## line when the remote has HEAD pointing to a branch, which most hosted repos do.
    cmd_detect_remote_branch = ["git", "ls-remote", "--symref", url, "HEAD"]
    result = shell_interface.query_cmd(
        cmd=cmd_detect_remote_branch,
        error_on_failure=False,
    )
    for line in result.splitlines():
        if line.startswith("ref:") and "HEAD" in line:
            ## format: "ref: refs/heads/main\tHEAD"
            ref_part = line.split("\t")[0].replace("ref:", "").strip()
            _, _, branch = ref_part.rpartition("/")
            return branch or None
    return None


##
## === SUBMODULE COMMANDS
##


def cmd_update_submodules(
    config: shell_interface.Config,
) -> None:
    """Pull the latest commits for all submodules from their tracked branches."""
    repo_state.require_repo()
    shell_interface.log_step("updating all submodules to latest on their tracked branch")
    ## `--remote` fetches from each submodule's remote and checks out the latest
    ## commit on the tracked branch (set in .gitmodules via `branch = main`).
    ## `--recursive` handles nested submodules.
    cmd_pull_submodule = ["git", "submodule", "update", "--remote", "--recursive"]
    shell_interface.run_cmd(config=config, cmd=cmd_pull_submodule)
    shell_interface.log_outcome("all submodules updated to latest")


def cmd_fix_submodule(
    config: shell_interface.Config,
    submodule_path: str,
    branch: str | None,
) -> None:
    """Repair a submodule stuck in detached HEAD: checkout default branch, pull, bump parent pointer."""
    repo_state.require_repo()
    shell_interface.bind_var(
        var_name="submodule_path",
        var_value=submodule_path,
    )
    if branch is None:
        shell_interface.log_step("reading tracked branch from .gitmodules")
        branch = _read_gitmodules_branch(submodule_path)
    if branch is None:
        shell_interface.log_step("detecting default branch of the submodule")
        branch = _detect_default_branch_from_local(submodule_path)
    if branch is None:
        shell_interface.kill(
            f"could not detect tracked branch for '{submodule_path}'; "
            "pass it explicitly: fix-submodule <path> <branch>",
        )
    shell_interface.bind_var(
        var_name="branch",
        var_value=branch,
    )
    shell_interface.log_step(f"checking out {branch} inside the submodule")
    ## `git -C <path>` runs the command as if cwd were <path> — avoids needing
    ## to actually cd in and out of the submodule directory.
    cmd_checkout_branch = ["git", "-C", submodule_path, "checkout", branch]
    shell_interface.run_cmd(config=config, cmd=cmd_checkout_branch)
    shell_interface.log_step("pulling latest commits inside the submodule")
    cmd_pull_submodule = ["git", "-C", submodule_path, "pull"]
    shell_interface.run_cmd(config=config, cmd=cmd_pull_submodule)
    shell_interface.log_step("staging updated submodule pointer in parent repo")
    ## staging the submodule path tells the parent to record the new HEAD SHA.
    cmd_stage_submodule = ["git", "add", submodule_path]
    shell_interface.run_cmd(config=config, cmd=cmd_stage_submodule)
    shell_interface.log_step("committing updated pointer in parent repo")
    cmd_commit_pointer = ["git", "commit", "-m", f"fix: update {submodule_path} pointer after repair"]
    shell_interface.run_cmd(config=config, cmd=cmd_commit_pointer)
    shell_interface.log_outcome(f"repaired '{submodule_path}' and bumped parent pointer")


def cmd_add_submodule(
    config: shell_interface.Config,
    url: str,
    local_name: str,
    branch: str | None,
) -> None:
    """Add a new submodule, pin it to track its default branch, and commit .gitmodules + pointer."""
    repo_state.require_repo()
    shell_interface.bind_var(
        var_name="url",
        var_value=url,
    )
    shell_interface.bind_var(
        var_name="local_name",
        var_value=local_name,
    )
    if branch is None:
        shell_interface.log_step("detecting default branch from remote")
        branch = _detect_default_branch_from_url(url)
        if branch is None:
            shell_interface.kill(
                f"could not detect default branch for '{url}'; "
                "pass it explicitly: add-submodule <url> <name> <branch>",
            )
    shell_interface.bind_var(
        var_name="branch",
        var_value=branch,
    )
    shell_interface.log_step("adding submodule")
    ## `submodule add` clones the remote into <local_name> and registers it in .gitmodules.
    cmd_add_submodule = ["git", "submodule", "add", url, local_name]
    shell_interface.run_cmd(config=config, cmd=cmd_add_submodule)
    shell_interface.log_step(f"setting tracked branch to {branch} in .gitmodules")
    ## record `branch = <branch>` so `git submodule update --remote` knows which
    ## branch to follow when pulling new commits.
    cmd_set_gitmodules_branch = [
        "git", "config", "-f", ".gitmodules", f"submodule.{local_name}.branch", branch
    ]
    shell_interface.run_cmd(config=config, cmd=cmd_set_gitmodules_branch)
    shell_interface.log_step("staging .gitmodules and submodule pointer")
    cmd_stage_gitmodules = ["git", "add", ".gitmodules", local_name]
    shell_interface.run_cmd(config=config, cmd=cmd_stage_gitmodules)
    shell_interface.log_step("committing")
    cmd_commit_submodule = ["git", "commit", "-m", f"add {local_name} submodule"]
    shell_interface.run_cmd(config=config, cmd=cmd_commit_submodule)
    shell_interface.log_outcome(f"added submodule '{local_name}' tracking {branch}")


## } MODULE
