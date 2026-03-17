"""
Runtime toggles, logging helpers, and subprocess wrappers.

Runtime toggles (env-vars):
  GIT_VERBOSE=1  # default  -> print decisions + the exact git commands
  GIT_VERBOSE=0  #          -> quiet mode

  GIT_DRYRUN=1   #          -> show commands, but DO NOT execute them
  GIT_DRYRUN=0   # default  -> execute normally

  GIT_ALLOW_DIRTY=1  #      -> allow syncs/merges with uncommitted changes
  GIT_ALLOW_DIRTY=0  # default  -> require a clean worktree (safer)
"""

import os
import subprocess
import sys

##
## === TOGGLES
##

verbose = os.environ.get("GIT_VERBOSE", "1") != "0"
dryrun = os.environ.get("GIT_DRYRUN", "0") == "1"
allow_dirty = os.environ.get("GIT_ALLOW_DIRTY", "0") == "1"

##
## === LOGGING
##


def log_msg(msg: str) -> None:
    """Print msg to stderr when GIT_VERBOSE is enabled (the default)."""
    ## all diagnostic output goes to stderr so it doesn't pollute stdout,
    ## which callers may capture (e.g. in scripts using $(...)).
    if verbose:
        print(
            msg,
            file=sys.stderr,
        )


def log_step(msg: str) -> None:
    """Narrate a major decision point within a command."""
    ## helps trace what the function is doing at each stage.
    log_msg(f"STEP: {msg}")


def log_outcome(msg: str) -> None:
    """Record which path was taken after a branch or decision."""
    log_msg(f"OUTCOME: {msg}")


def bind_var(var_name: str, var_value: str) -> None:
    """Log a variable name alongside the value it was resolved to."""
    ## useful when debugging computed values like remote names or branch names.
    log_msg(f"SET: {var_name} = {var_value}")


def kill(msg: str) -> None:
    """Print an error message to stderr and exit the process immediately."""
    print(
        f"error: {msg}",
        file=sys.stderr,
    )
    sys.exit(1)


##
## === EXECUTION
##


def run_cmd(*args: str) -> None:
    """Run a mutating git command; skipped entirely in dry-run mode."""
    if dryrun:
        log_msg(f"+ (dryrun) skipped: {' '.join(args)}")
        return
    log_msg(f"+ {' '.join(args)}")
    ## `check=True` raises CalledProcessError on non-zero exit, caught in main().
    subprocess.run(
        args,
        check=True,
    )


def run_cmd_and_capture_output(*args: str) -> str:
    """Run a mutating git command and return its stdout; empty string in dry-run."""
    if dryrun:
        log_msg(f"+ (dryrun) skipped: {' '.join(args)}")
        return ""
    log_msg(f"+ {' '.join(args)}")
    ## `capture_output=True` redirects both stdout and stderr so they don't
    ## print to the terminal; `text=True` decodes bytes to str automatically.
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def query_cmd(*args: str) -> str:
    """Run a read-only git command and return its stdout; always executes, even in dry-run."""
    log_msg(f"? {' '.join(args)}")
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def probe_cmd(*args: str) -> int:
    """Run a command silently and return its exit code; used for boolean existence checks."""
    ## output is suppressed entirely — callers only care whether the command succeeded or failed.
    result = subprocess.run(
        args,
        capture_output=True,
    )
    return result.returncode


def query_cmd_or_empty(*args: str) -> str:
    """Run a read-only git command and return stdout, or empty string if the command fails."""
    ## unlike query_cmd(), no check=True — used when failure is a valid outcome (e.g. -q flag commands
    ## that exit non-zero to signal "not found" rather than an actual error).
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
