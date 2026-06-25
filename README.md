# Git Helpers

`git_helpers` is a command line tool that packages up common `git` workflows into single commands. Each command operates on the `git` repo in your current directory, narrates what it's doing, and prints the underlying `git` commands it runs; that way you learn the mechanics while getting the job done.

---

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

`uv` places installed tools in `~/.local/bin`, so if `git_helpers` isn't found after the install, add the following to your shell config (`~/.zshrc` for zsh, `~/.bashrc` for bash):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## Update

From your local GitHelpers clone, pull the latest changes and reinstall:

```bash
git pull
uv tool install . --reinstall
```

---

## Uninstall

```bash
uv tool uninstall git_helpers
```

---

## Available commands

Run any command from inside a git repo. Use `git_helpers --help` to see all available commands, or `git_helpers <command> --help` for details on a specific one.

In the listings below, `<arg>` means a required positional argument, `[arg]` means optional, and `[--flag]` means an optional flag.

**Inspecting tracking state**
```bash
git_helpers show-local-remotes                                                          # list all configured remotes and their URLs
git_helpers show-upstream-state                                                         # show which remote branch the current branch is tracking and its latest commit
git_helpers show-branches-status                                                        # see all local branches and whether they're ahead or behind their remote (fetches first)
git_helpers count-ahead-behind                                                          # show how many commits the current branch is ahead of and behind its upstream
git_helpers show-unpulled-commits                                                       # list commits on the remote that haven't been pulled yet
git_helpers show-recent-commits [--max-entries N] [--show-files-changed]                # show the last N commits on the current branch (default: 20); add --show-files-changed to list files changed per commit
git_helpers show-commits-on-branch [--base branch] [--show-files-changed] [--no-fetch]  # show commits on the current branch not in the base; fetches first (--base must be remote-qualified, e.g. origin/main; default: remote default)
```

**Inspecting changes**
```bash
git_helpers show-commit <commit>                                                          # show the message and diff introduced by a specific commit
git_helpers show-diff-uncommitted [--path path]                                                  # show all uncommitted local changes vs HEAD (staged and unstaged)
git_helpers show-diff-n-commits --num-commits N [--include-uncommitted] [--path path]           # show changes over the last N commits; add --include-uncommitted to include local changes
git_helpers show-diff-committed [--base branch] [--name-only] [--no-fetch] [--path path]  # show committed changes on the current branch vs a base; fetches first (--base must be remote-qualified, e.g. origin/main; default: remote default)
```

**Stashing work**
```bash
git_helpers stash-work [name]    # temporarily save uncommitted work so you can switch context; optionally label it
git_helpers unstash-work [name]  # restore the most recently stashed work, or a specific stash by name
```

**Editing the last commit**
```bash
git_helpers amend-last-commit [msg]   # fold staged changes into the last commit; optionally update the message too
git_helpers rename-last-commit <msg>  # update the message of the last commit without changing its content (rewrites history)
```

**Syncing with the remote**
```bash
git_helpers push                         # push the current branch; sets the upstream automatically if it's a new branch
git_helpers sync-branch [remote/branch]  # bring the current branch up to date with its upstream (or an explicit remote branch)
```

**Managing branches**
```bash
git_helpers create-branch-from-default <name>                 # create and push a new branch from the remote default (e.g. origin/main)
git_helpers create-branch-from-remote <name> <remote/branch>  # create and push a new branch from a specific remote branch
git_helpers track-remote-branch <remote/branch> [name]        # create a local tracking branch for an existing remote branch and check it out
git_helpers delete-local-branch <name>                        # delete a local branch safely (refuses if it has unmerged commits)
git_helpers prune-gone-locals                                 # delete local branches whose remote counterpart has been deleted; skips branches with unmerged commits and reports them
git_helpers force-delete-gone                                 # force-delete [gone] local branches regardless of merge status (use for squash-merged branches)
git_helpers prune-merged-locals [remote/branch]               # delete local branches whose commits are already in the base branch
git_helpers cleanup-local-branches [remote/branch]            # delete all gone and merged local branches in one step
```

**Managing worktrees**
```bash
git_helpers remove-worktree <branch>  # remove a worktree and delete its local branch in one step
git_helpers prune-worktrees           # remove all worktrees whose upstream branch has been deleted and delete their local branches
```

**Submodules**
```bash
git_helpers show-submodules-status               # show the current state of each submodule (commit SHA and init status)
git_helpers update-submodules                    # update all submodules to their latest commit on the tracked branch
git_helpers fix-submodule <path> [branch]        # repair a submodule in detached HEAD state (auto-detects branch, pulls, updates parent pointer)
git_helpers add-submodule <url> <name> [branch]  # add a new submodule tracking its default branch and commit the result
```

**Summary**
```bash
git_helpers scan-repos [--depth N] [--since DAYS]  # scan below CWD for dirty, unpushed, and recently active git repos
```

`--depth N` (default: 3) controls how many directory levels to descend. `--since DAYS` filters to repos with a commit in the last N days and counts commits per repo within that window; without it, only repos needing attention (dirty or unpushed) are shown.

By default, `scan-repos` does not descend into git submodules. Submodule scanning is opt-in per repo; upstream codebases often use submodules for build dependencies rather than active working trees. To opt a repo in, run this once inside it:

```bash
git config --local git-helpers.scan-submodules true
```

> **Note:** this setting is stored in `.git/config`, which git does not track, so it is not committed or pushed. Re-run it after a fresh clone.

Within an opted-in repo, individual submodules can still be excluded by adding `ignore = all` to their entry in `.gitmodules`.

**Global git configuration**
```bash
git_helpers set-global-config   # set pull.rebase=true, FF-first merge defaults, and rerere in ~/.gitconfig
git_helpers show-global-config  # show the current values of the git settings this tool manages
```

---

## Global flags

These flags apply to any command and are placed before the subcommand:

```bash
git_helpers --dry-run <cmd>      # print commands without executing them
git_helpers --allow-dirty <cmd>  # skip the clean worktree check
```

`--dry-run` is useful for previewing what a command will do before committing to it.

---

## Output legend

| Symbol | Color | Meaning |
|---|---|---|
| `○` | white | action starting |
| `●` | green | action outcome |
| `●` | red | error |
| `→` | blue | command being run |
| `→` | orange | skipped command (dry-run) |
| `→` | gray | read-only lookup command |
| `·` | gray | resolved value / context |

---

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

---

## File structure

```text
GitHelpers/
├── src/
│   └── git_helpers/
│       ├── user_interface.py      # [entrypoint] argparse wiring and main()
│       ├── repo_state.py          # [internal] repo state queries and guards
│       ├── shell_interface.py     # [internal] config, logging, subprocess wrappers
│       ├── commands/
│       │   ├── git_config.py      # global git config commands
│       │   ├── git_inspection.py  # read-only inspection commands
│       │   ├── git_branches.py    # branch management commands
│       │   ├── git_submodules.py  # submodule commands
│       │   └── git_sync.py        # push, sync, stash, and history commands
│       └── summary/
│           └── git_scan.py        # cross-repo scan command
├── utests/                        # unit tests (no real git repos)
├── vtests/
│   ├── commands/                  # validation tests for commands/
│   └── summary/                   # validation tests for summary/
├── pyproject.toml                 # package metadata; registers the git_helpers command
├── uv.lock                        # pinned dependency versions
├── .gitignore
└── README.md
```

---

## License

See [LICENSE](./LICENSE).
