# Git Helpers

`git_helpers` is a command line tool that packages up common `git` workflows into single commands. Each command operates on the `git` repo in your current directory, narrates what it's doing, and prints the underlying `git` commands it runs; that way you'll learn the mechanics while getting the job done.

## Getting setup

Before you start, you'll need [uv](https://docs.astral.sh/uv/).

Once you have `uv` installed, clone this repo and install `git_helpers` as a globally accessible tool:

```bash
git clone git@github.com:AstroKriel/GitHelpers.git
cd GitHelpers
uv tool install .
```

Verify everything is working:

```bash
git_helpers self-check  # verify git is on your PATH
git_helpers --help      # list all available commands
```

`uv` places installed tools in `~/.local/bin`, so if `git_helpers` isn't found after the install, add the following to your shell config (`~/.zshrc` for zsh, and `~/.bashrc` for bash):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Update GitHelpers

From your local GitHelpers clone, pull the latest changes and reinstall:

```bash
git pull
uv tool install . --reinstall
```

## Uninstall GitHelpers

```bash
uv tool uninstall git_helpers
```

## Available commands

Run any command from inside a git repo. Use `git_helpers --help` to see all available commands, or `git_helpers <command> --help` for details on a specific one.

Note that below `<arg>` means required, and `[arg]` means optional.

**Global git configuration**
```bash
git_helpers set-global-config   # set sensible merge defaults in ~/.gitconfig (fast-forward preferred, rerere enabled)
git_helpers show-global-config  # show the current values of the git settings this tool manages
```

**Inspecting repo state**
```bash
git_helpers show-branches-status     # see all local branches and whether they're ahead or behind their remote (fetches first)
git_helpers count-ahead-behind       # show how many commits the current branch is ahead of and behind its upstream
git_helpers show-upstream-state      # show which remote branch the current branch is tracking and its latest commit
git_helpers show-unpulled-commits    # list commits on the remote that haven't been pulled yet
git_helpers show-recent-commits [N]  # show the last N commits on the current branch (default: 20)
git_helpers show-local-remotes       # list all configured remotes and their URLs
git_helpers show-submodules-status   # show the current state of each submodule (commit SHA and init status)
```

**Managing branches**
```bash
git_helpers create-branch-from-default <name>                 # create and push a new branch from the remote default (e.g. origin/main)
git_helpers create-branch-from-remote <name> <remote/branch>  # create and push a new branch from a specific remote branch
git_helpers track-remote-branch <remote/branch> [name]        # create a local tracking branch for an existing remote branch and check it out
git_helpers delete-local-branch <name>                        # delete a local branch safely (refuses if it has unmerged commits)
git_helpers prune-gone-locals                                 # delete local branches whose remote counterpart has been deleted
git_helpers prune-merged-locals [remote/branch]               # delete local branches whose commits are already in the base branch
git_helpers cleanup-local-branches [remote/branch]            # delete all gone and merged local branches in one step
```

**Managing submodules**
```bash
git_helpers update-submodules           # update all submodules to their latest commit on the tracked branch
git_helpers fix-submodule <path>        # repair a submodule in detached HEAD state (checks out main, pulls, updates parent pointer)
git_helpers add-submodule <url> <name>  # add a new submodule tracking main and commit the result
```

**Syncing and rewriting history**
```bash
git_helpers push                         # push the current branch; sets the upstream automatically if it's a new branch
git_helpers sync-branch [remote/branch]  # bring the current branch up to date with its upstream (or an explicit remote branch)
git_helpers stash-work [name]            # temporarily save uncommitted work so you can switch context; optionally label it
git_helpers unstash-work [name]          # restore the most recently stashed work, or a specific stash by name
git_helpers amend-last-commit [msg]      # fold staged changes into the last commit; optionally update the message too
git_helpers rename-last-commit <msg>     # update the message of the last commit without changing its content (rewrites history)
```

## Global flags

These flags apply to any command and are placed before the subcommand:

```bash
git_helpers --dry-run <cmd>      # print commands without executing them
git_helpers --allow-dirty <cmd>  # skip the clean worktree check
```

`--dry-run` is useful for previewing what a command will do before committing to it.

## Run test suites

Tests are run with `pytest`, and are broken into two categories. `utests/` tests the Python logic (argument parsing, config handling) without executing any git commands, and `vtests/` tests that the actual git operations produce the expected repo state.

Run the full suite from the repo root:

```bash
uv run pytest
```

To run either suite in isolation:

```bash
uv run pytest utests/
uv run pytest vtests/
```

## File structure

```
GitHelpers/
├── src/
│   └── git_helpers/
│       ├── user_interface.py   # [entrypoint] argparse wiring and main()
│       ├── git_config.py       # [commands] global git config commands
│       ├── git_inspection.py   # [commands] read-only inspection commands
│       ├── git_branches.py     # [commands] branch management commands
│       ├── git_submodules.py   # [commands] submodule commands
│       ├── git_sync.py         # [commands] push, sync, stash, and history commands
│       ├── repo_state.py       # [internal] repo state queries and guards
│       └── shell_interface.py  # [internal] config, logging, subprocess wrappers
├── utests/                     # unit tests
├── vtests/                     # validation tests
├── pyproject.toml              # package metadata; registers the git_helpers command
├── uv.lock                     # pinned dependency versions
├── .gitignore
└── README.md
```

## License

See [LICENSE](./LICENSE).
