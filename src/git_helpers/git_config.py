## { MODULE

##
## === DEPENDENCIES
##

## local
from git_helpers import shell_interface

##
## === GIT CONFIGURATION
##


def cmd_set_global_config(
    config: shell_interface.Config,
) -> None:
    """Write FF-first merge defaults and enable rerere to ~/.gitconfig."""
    ## pull.rebase=false: when pulling, merge diverged branches instead of
    ## rebasing them. Safer default — rebase rewrites history.
    shell_interface.run_cmd(config, "git", "config", "--global", "pull.rebase", "false")
    ## pull.ff=true + merge.ff=true: prefer fast-forward when the histories
    ## are linear; only create a merge commit when branches have actually diverged.
    shell_interface.run_cmd(config, "git", "config", "--global", "pull.ff", "true")
    shell_interface.run_cmd(config, "git", "config", "--global", "merge.ff", "true")
    ## rerere (Reuse Recorded Resolution): git remembers how you resolved a
    ## conflict and re-applies the same resolution automatically next time.
    shell_interface.run_cmd(config, "git", "config", "--global", "rerere.enabled", "true")
    shell_interface.log_result("installed FF-first merge defaults globally in ~/.gitconfig")


def show_global_config(
    _config: shell_interface.Config,
) -> None:
    """Print the current values of the git settings this module relies on."""

    ## inner helper to read one config key; returns "(unset)" rather than
    ## empty string so the display is always meaningful.
    def read_config_value(
        key: str,
    ) -> str:
        return shell_interface.query_cmd_or_empty("git", "config", "--global", "--get", key) or "(unset)"

    shell_interface.log_result("global git configuration:")
    for label, key in [
        ("pull.rebase", "pull.rebase"),
        ("pull.ff", "pull.ff"),
        ("merge.ff", "merge.ff"),
        ("rerere.enabled", "rerere.enabled"),
    ]:
        ## `{label:<15}` left-aligns the label in a 15-char field so values line up.
        shell_interface.log_result(f"  {label:<15} = {read_config_value(key)}")
    shell_interface.log_result(
        "tip: edit directly via 'git config --global --edit' or run 'git_helpers set-global-config'",
    )


def check_self(
    _config: shell_interface.Config,
) -> None:
    """Verify that git is available on PATH."""
    ## verify git is on PATH before any other operation that would rely on it.
    if shell_interface.probe_cmd("which", "git") != 0:
        shell_interface.kill("git not found in PATH")
    shell_interface.log_outcome("selfcheck passed")


## } MODULE
