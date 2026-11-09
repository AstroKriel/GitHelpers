## { MODULE

##
## === DEPENDENCIES
##

## personal
from huginn import manage_log, manage_shell

##
## === GIT CONFIGURATION
##


def cmd_set_global_config() -> None:
    """Write pull-rebase and FF-first merge defaults, enable rerere, and set the default branch to main, in ~/.gitconfig."""
    ## pull.rebase=true: when pulling, replay local commits on top of the
    ## remote instead of creating a merge commit. Keeps history linear and
    ## is the right default for multi-device workflows.
    cmd_set_pull_rebase = [
        "git",
        "config",
        "--global",
        "pull.rebase",
        "true",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_set_pull_rebase)
    ## pull.ff=true + merge.ff=true: prefer fast-forward when the histories
    ## are linear; only create a merge commit when branches have actually diverged.
    cmd_set_pull_ff = [
        "git",
        "config",
        "--global",
        "pull.ff",
        "true",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_set_pull_ff)
    cmd_set_merge_ff = [
        "git",
        "config",
        "--global",
        "merge.ff",
        "true",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_set_merge_ff)
    ## rerere (Reuse Recorded Resolution): git remembers how you resolved a
    ## conflict and re-applies the same resolution automatically next time.
    cmd_set_rerere = [
        "git",
        "config",
        "--global",
        "rerere.enabled",
        "true",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_set_rerere)
    ## init.defaultBranch=main: `git init` and clones of empty remotes start
    ## on `main` instead of the built-in `master`.
    cmd_set_default_branch = [
        "git",
        "config",
        "--global",
        "init.defaultBranch",
        "main",
    ]
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_set_default_branch)
    manage_log.log_outcome(
        "installed pull-rebase, FF-first merge, and default-branch defaults globally in ~/.gitconfig",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


def show_global_config() -> None:
    """Print the current values of the git settings this module relies on."""

    ## inner helper to read one config key; returns "(unset)" rather than
    ## empty string so the display is always meaningful.
    def read_config_value(
        key: str,
    ) -> str:
        cmd_read_global_config = [
            "git",
            "config",
            "--global",
            "--get",
            key,
        ]
        raw_value = manage_shell.query_cmd_and_capture_output(
            cmd_parts=cmd_read_global_config,
            raise_error=False,
        )
        return raw_value or "(unset)"

    manage_log.log_task("global git configuration:")
    for key in [
            "pull.rebase",
            "pull.ff",
            "merge.ff",
            "rerere.enabled",
            "init.defaultBranch",
    ]:
        ## `{key:<18}` left-aligns the key in an 18-char field so values line up.
        manage_log.log_return(f"\t{key:<18} = {read_config_value(key)}")
    manage_log.log_note(
        "to change these settings",
        items={
            "edit by hand": "git config --global --edit",
            "install defaults": "git_helpers set-global-config",
        },
    )


## } MODULE
