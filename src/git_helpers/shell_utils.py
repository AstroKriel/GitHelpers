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
class _Style:
    color: _Colors
    marker: _Markers


class _Theme:
    STEP = _Style(
        color=_Colors.WHITE,
        marker=_Markers.CIRCLE_OPEN,
    )  # narrating a major decision point
    SUCCESS = _Style(
        color=_Colors.GREEN,
        marker=_Markers.CIRCLE_CLOSED,
    )  # positive outcome or result
    ACTION = _Style(
        color=_Colors.BLUE,
        marker=_Markers.ARROW,
    )  # executing a mutating command
    SKIPPED = _Style(
        color=_Colors.ORANGE,
        marker=_Markers.ARROW,
    )  # skipped in dry-run mode
    ERROR = _Style(
        color=_Colors.RED,
        marker=_Markers.CIRCLE_CLOSED,
    )  # fatal error
    CONTEXT = _Style(
        color=_Colors.GRAY,
        marker=_Markers.ARROW,
    )  # metadata, bindings, read-only commands


def log_msg(
    msg: str,
) -> None:
    """Print msg to stderr; all diagnostic output goes here to keep stdout clean."""
    _CONSOLE.print(msg)


def log_step(
    msg: str,
) -> None:
    """Narrate a major decision point within a command."""
    style = _Theme.STEP
    _CONSOLE.print(f"[{style.color.value}]{style.marker.value}[/] {msg}")


def log_outcome(
    msg: str,
) -> None:
    """Record which path was taken after a branch or decision."""
    style = _Theme.SUCCESS
    _CONSOLE.print(f"[{style.color.value}]{style.marker.value} {msg}[/]")


def bind_var(
    var_name: str,
    var_value: str,
) -> None:
    """Log a variable name alongside the value it was resolved to."""
    style = _Theme.CONTEXT
    _CONSOLE.print(f"[{style.color.value}]{style.marker.value} {var_name} = {var_value}[/]")


def log_result(
    msg: str,
) -> None:
    """Print a user-facing result to stdout."""
    style = _Theme.SUCCESS
    _CONSOLE_OUT.print(f"[{style.color.value}]{style.marker.value} {msg}[/]")


def kill(
    msg: str,
) -> NoReturn:
    """Print an error message to stderr and exit the process immediately."""
    style = _Theme.ERROR
    _CONSOLE.print(f"[{style.color.value}]{style.marker.value}[/] error: {msg}")
    sys.exit(1)


##
## === EXECUTION
##


def run_cmd(
    config: Config,
    *args: str,
) -> None:
    """Run a mutating git command; skipped entirely in dry-run mode."""
    if config.dry_run:
        style = _Theme.SKIPPED
        _CONSOLE.print(f"[{style.color.value}]{style.marker.value} (dryrun) skipped: {' '.join(args)}[/]")
        return
    style = _Theme.ACTION
    _CONSOLE.print(f"[{style.color.value}]{style.marker.value} {' '.join(args)}[/]")
    ## `check=True` raises CalledProcessError on non-zero exit, caught in main().
    subprocess.run(
        args,
        check=True,
    )


def run_cmd_and_capture_output(
    config: Config,
    *args: str,
) -> str:
    """Run a mutating git command and return its stdout; empty string in dry-run."""
    if config.dry_run:
        style = _Theme.SKIPPED
        _CONSOLE.print(f"[{style.color.value}]{style.marker.value} (dryrun) skipped: {' '.join(args)}[/]")
        return ""
    style = _Theme.ACTION
    _CONSOLE.print(f"[{style.color.value}]{style.marker.value} {' '.join(args)}[/]")
    ## `capture_output=True` redirects both stdout and stderr so they don't
    ## print to the terminal; `text=True` decodes bytes to str automatically.
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def query_cmd(
    *args: str,
) -> str:
    """Run a read-only git command and return its stdout; always executes, even in dry-run."""
    style = _Theme.CONTEXT
    _CONSOLE.print(f"[{style.color.value}]{style.marker.value} {' '.join(args)}[/]")
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def probe_cmd(
    *args: str,
) -> int:
    """Run a command silently and return its exit code; used for boolean existence checks."""
    ## output is suppressed entirely — callers only care whether the command succeeded or failed.
    result = subprocess.run(
        args,
        capture_output=True,
    )
    return result.returncode


def query_cmd_or_empty(
    *args: str,
) -> str:
    """Run a read-only git command and return stdout, or empty string if the command fails."""
    ## unlike query_cmd(), no check=True — used when failure is a valid outcome (e.g. -q flag commands
    ## that exit non-zero to signal "not found" rather than an actual error).
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


## } MODULE
