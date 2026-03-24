## { MODULE

##
## === DEPENDENCIES
##

## local
from git_helpers import shell_interface, repo_state

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
    shell_interface.run_cmd(config, "git", "submodule", "update", "--remote", "--recursive")
    shell_interface.log_outcome("all submodules updated to latest")


def cmd_fix_submodule(
    config: shell_interface.Config,
    submodule_path: str,
) -> None:
    """Repair a submodule stuck in detached HEAD: checkout main, pull, bump parent pointer."""
    repo_state.require_repo()
    shell_interface.bind_var(
        var_name="submodule_path",
        var_value=submodule_path,
    )
    shell_interface.log_step("checking out main inside the submodule")
    ## `git -C <path>` runs the command as if cwd were <path> — avoids needing
    ## to actually cd in and out of the submodule directory.
    shell_interface.run_cmd(config, "git", "-C", submodule_path, "checkout", "main")
    shell_interface.log_step("pulling latest commits inside the submodule")
    shell_interface.run_cmd(config, "git", "-C", submodule_path, "pull")
    shell_interface.log_step("staging updated submodule pointer in parent repo")
    ## staging the submodule path tells the parent to record the new HEAD SHA.
    shell_interface.run_cmd(config, "git", "add", submodule_path)
    shell_interface.log_step("committing updated pointer in parent repo")
    shell_interface.run_cmd(
        config,
        "git",
        "commit",
        "-m",
        f"fix: update {submodule_path} pointer after repair",
    )
    shell_interface.log_outcome(f"repaired '{submodule_path}' and bumped parent pointer")


def cmd_add_submodule(
    config: shell_interface.Config,
    url: str,
    local_name: str,
) -> None:
    """Add a new submodule, pin it to track main, and commit .gitmodules + pointer."""
    repo_state.require_repo()
    shell_interface.bind_var(
        var_name="url",
        var_value=url,
    )
    shell_interface.bind_var(
        var_name="local_name",
        var_value=local_name,
    )
    shell_interface.log_step("adding submodule")
    ## `submodule add` clones the remote into <local_name> and registers it in .gitmodules.
    shell_interface.run_cmd(config, "git", "submodule", "add", url, local_name)
    shell_interface.log_step("setting tracked branch to main in .gitmodules")
    ## record `branch = main` so `git submodule update --remote` knows which
    ## branch to follow when pulling new commits.
    shell_interface.run_cmd(
        config,
        "git",
        "config",
        "-f",
        ".gitmodules",
        f"submodule.{local_name}.branch",
        "main",
    )
    shell_interface.log_step("staging .gitmodules and submodule pointer")
    shell_interface.run_cmd(config, "git", "add", ".gitmodules", local_name)
    shell_interface.log_step("committing")
    shell_interface.run_cmd(config, "git", "commit", "-m", f"add {local_name} submodule")
    shell_interface.log_outcome(f"added submodule '{local_name}' tracking main")


## } MODULE
