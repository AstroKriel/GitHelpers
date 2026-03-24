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

In the usage lines below: `<arg>` is required, `[arg]` is optional.

**Global git configuration**
```bash
git_helpers set-global-config   # write FF-first merge defaults + rerere to ~/.gitconfig
git_helpers show-global-config  # print current values of those settings
```

**Inspecting repo state**
```bash
git_helpers show-branches-status          # fetch, then show all branches with upstream + ahead/behind
git_helpers count-ahead-behind            # how many commits ahead/behind the current branch is
git_helpers show-upstream-state           # show the upstream ref and its latest commit
git_helpers show-unpulled-commits         # list commits on upstream not yet pulled
git_helpers show-recent-commits [N]       # last N commits on current branch (default: 20)
git_helpers show-local-remotes            # list all remotes and their URLs
git_helpers show-submodules-status        # show SHA and init status of each submodule
```

**Managing branches**
```bash
git_helpers create-branch-from-default <name>           # cut from remote default branch + push
git_helpers create-branch-from-remote <name> <remote/branch>  # cut from explicit remote ref + push
git_helpers track-remote-branch <remote/branch> [name]        # create local branch tracking a remote one
git_helpers delete-local-branch <name>                        # safe delete (refuses if unmerged)
git_helpers prune-gone-locals                                 # delete branches whose remote was deleted
git_helpers prune-merged-locals [remote/branch]               # delete branches merged into base
git_helpers cleanup-local-branches [remote/branch]            # run both prune steps in sequence
```

**Managing submodules**
```bash
git_helpers update-submodules              # pull latest commits for all submodules
git_helpers fix-submodule <path>           # repair detached HEAD: checkout main, pull, bump pointer
git_helpers add-submodule <url> <name>     # add submodule tracking main and commit
```

**Syncing and rewriting history**
```bash
git_helpers push                           # push current branch; sets upstream automatically if needed
git_helpers sync-branch [remote/branch]    # pull/merge with --ff; merge explicit base if provided
git_helpers stash-work [name]              # stash uncommitted work; optionally label it
git_helpers unstash-work [name]            # pop most recent stash, or find one by name
git_helpers amend-last-commit [msg]        # amend staged changes into last commit; optionally update message
git_helpers rename-last-commit <msg>       # replace the most recent commit message
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
