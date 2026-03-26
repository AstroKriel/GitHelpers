## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import NoReturn

## third-party
from rich.console import Console

##
## === CONFIG
##


@dataclass
class Config:
    dry_run: bool = False
    allow_dirty: bool = False


##
## === LOGGING
##

_CONSOLE = Console(
    highlight=False,
    stderr=True,
)
_CONSOLE_OUT = Console(
    highlight=False,
    stderr=False,
)


class _Colors(str, Enum):
    WHITE = "#FFFFFF"
    GREEN = "#32CD32"
    BLUE = "#2A71F6"
    ORANGE = "#E48500"
    RED = "#FF4500"
    GRAY = "#818181"


class _Markers(str, Enum):
    CIRCLE_OPEN = "\u25CB"  # ○
    CIRCLE_CLOSED = "\u25CF"  # ●
    ARROW = "\u2192"  # →


@dataclass(frozen=True)
class _Theme:
    color: _Colors
    marker: _Markers


class _Themes:
    STEP = _Theme(
        color=_Colors.WHITE,
        marker=_Markers.CIRCLE_OPEN,
    )
    SUCCESS = _Theme(
        color=_Colors.GREEN,
        marker=_Markers.CIRCLE_CLOSED,
    )
    ACTION = _Theme(
        color=_Colors.BLUE,
        marker=_Markers.ARROW,
    )
    SKIPPED = _Theme(
        color=_Colors.ORANGE,
        marker=_Markers.ARROW,
    )
    ERROR = _Theme(
        color=_Colors.RED,
        marker=_Markers.CIRCLE_CLOSED,
    )
    CONTEXT = _Theme(
        color=_Colors.GRAY,
        marker=_Markers.ARROW,
    )


def _print_cmd(
    theme: _Theme,
    cmd: list[str],
    cmd_prefix: str,
) -> None:
    theme_color = theme.color.value
    theme_marker = theme.marker.value
    cmd_string = " ".join(cmd)
    _CONSOLE.print(f"[{theme_color}]{theme_marker}{cmd_prefix}{cmd_string}[/]")


def log_msg(
    msg: str,
) -> None:
    """Print msg to stderr; all diagnostic output goes here to keep stdout clean."""
    _CONSOLE.print(msg)


def log_step(
    msg: str,
) -> None:
    """Narrate a major decision point within a command."""
    theme = _Themes.STEP
    theme_color = theme.color.value
    theme_marker = theme.marker.value
    _CONSOLE.print(f"[{theme_color}]{theme_marker}[/] {msg}")


def log_outcome(
    msg: str,
) -> None:
    """Record which path was taken after a branch or decision."""
    theme = _Themes.SUCCESS
    theme_color = theme.color.value
    theme_marker = theme.marker.value
    _CONSOLE.print(f"[{theme_color}]{theme_marker} {msg}[/]")


def bind_var(
    var_name: str,
    var_value: str,
) -> None:
    """Log a variable name alongside the value it was resolved to."""
    theme = _Themes.CONTEXT
    theme_color = theme.color.value
    theme_marker = theme.marker.value
    _CONSOLE.print(f"[{theme_color}]{theme_marker} {var_name} = {var_value}[/]")


def log_result(
    msg: str,
) -> None:
    """Print a user-facing result to stdout."""
    theme = _Themes.SUCCESS
    theme_color = theme.color.value
    theme_marker = theme.marker.value
    _CONSOLE_OUT.print(f"[{theme_color}]{theme_marker} {msg}[/]")


def kill(
    msg: str,
) -> NoReturn:
    """Print an error message to stderr and exit the process immediately."""
    theme = _Themes.ERROR
    theme_color = theme.color.value
    theme_marker = theme.marker.value
    _CONSOLE.print(f"[{theme_color}]{theme_marker}[/] error: {msg}")
    sys.exit(1)


##
## === EXECUTION
##


def run_cmd(
    config: Config,
    cmd: list[str],
) -> None:
    """Run a mutating git command; skipped entirely in dry-run mode."""
    if config.dry_run:
        _print_cmd(
            theme=_Themes.SKIPPED,
            cmd=cmd,
            cmd_prefix=" (dryrun) skipped: ",
        )
        return
    _print_cmd(
        theme=_Themes.ACTION,
        cmd=cmd,
        cmd_prefix=" ",
    )
    ## `check=True` raises CalledProcessError on non-zero exit, caught in main().
    subprocess.run(
        cmd,
        check=True,
    )


def run_cmd_and_capture_output(
    config: Config,
    cmd: list[str],
) -> str:
    """Run a mutating git command and return its stdout; empty string in dry-run."""
    if config.dry_run:
        _print_cmd(
            theme=_Themes.SKIPPED,
            cmd=cmd,
            cmd_prefix=" (dryrun) skipped: ",
        )
        return ""
    _print_cmd(
        theme=_Themes.ACTION,
        cmd=cmd,
        cmd_prefix=" ",
    )
    ## `capture_output=True` redirects both stdout and stderr so they don't
    ## print to the terminal; `text=True` decodes bytes to str automatically.
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def query_cmd(
    cmd: list[str],
    error_on_failure: bool = True,
) -> str:
    """Run a read-only git command, log it, and return its stdout; always executes, even in dry-run.

    When error_on_failure=False, a non-zero exit returns an empty string instead of raising.
    Use this for commands where "not found" is a valid outcome rather than an error.
    """
    _print_cmd(
        theme=_Themes.CONTEXT,
        cmd=cmd,
        cmd_prefix=" ",
    )
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if error_on_failure and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result.stdout.strip()


def probe_cmd(
    cmd: list[str],
) -> int:
    """Run a command silently and return its exit code; used for boolean existence checks."""
    ## output is suppressed entirely — callers only care whether the command succeeded or failed.
    result = subprocess.run(
        cmd,
        capture_output=True,
    )
    return result.returncode


## } MODULE
