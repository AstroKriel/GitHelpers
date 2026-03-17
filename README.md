# Git Helpers

`git_helpers` is a command line tool that collects and packages up common `git` workflows into single commands (see the list of commands below). Each command operates on the `git`-repo in your current directory, narrates what it's doing, and prints the `git` commands it's running internally, so you can learn about the underlying mechanics while getting the job done.

## Getting setup

### Clone and install `git_helpers`'s dependencies

```bash
git clone git@github.com:AstroKriel/GitHelpers.git
cd GitHelpers
uv sync
```

### Run `git_helpers` locally (without installing globally)

From inside the repo, run commands through the `uv`-managed environment:

```bash
uv run git_helpers <subcommand> [args]
```

### Install `git_helpers` globally

To make `git_helpers` callable from any directory, run the following from the repo root:

```bash
cd /path/to/GitHelpers  # repo root
uv tool install .
```

`uv` places installed tools in `~/.local/bin`. Verify it's on your PATH:

```bash
which git_helpers  # prints the path if found, errors if not
```

If it's missing, add it to your shell config (`~/.zshrc` for zsh, `~/.bashrc` for bash):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Verify the installation

```bash
uv tool list            # should show git_helpers
git_helpers self-check  # verify git is on your PATH
git_helpers --help      # list all available commands
```

### Update `git_helpers`

From the repo root:

```bash
cd /path/to/GitHelpers
git pull
uv tool install . --reinstall
```

### Uninstall `git_helpers`

From the repo root:

```bash
cd /path/to/GitHelpers
uv tool uninstall git_helpers
```

## Commands

**Global git configuration**
```bash
git_helpers set-global-config   # write FF-first merge defaults + rerere to ~/.gitconfig
git_helpers show-global-config  # print current values of those settings
```

**Inspecting repo state**
```bash
git_helpers branches-status          # fetch, then show all branches with upstream + ahead/behind
git_helpers ahead-behind             # how many commits ahead/behind the current branch is
git_helpers show-upstream            # show the upstream ref and its latest commit
git_helpers unpulled-commits         # list commits on upstream not yet pulled
git_helpers show-recent-commits [N]  # last N commits on current branch (default: 20)
git_helpers local-remotes            # list all remotes and their URLs
git_helpers submodules-status        # show SHA and init status of each submodule
git_helpers is-detached              # exit 0 if HEAD is detached (usable in shell conditionals)
```

**Managing branches**
```bash
git_helpers create-branch-from-default <name>           # cut from remote default branch + push
git_helpers create-branch-from-remote <name> <ref>      # cut from explicit remote ref + push
git_helpers track-remote-branch <remote/branch> [name]  # create local branch tracking a remote one
git_helpers delete-local-branch <name>                  # safe delete (refuses if unmerged)
git_helpers prune-gone-locals                           # delete branches whose remote was deleted
git_helpers prune-merged-locals [base]                  # delete branches merged into base
git_helpers cleanup-local-branches [base]               # run both prune steps in sequence
```

**Syncing and rewriting history**
```bash
git_helpers push                      # push current branch; sets upstream automatically if needed
git_helpers sync-branch [base]        # pull/merge with --ff; merge explicit base if provided
git_helpers rename-last-commit <msg>  # amend the most recent commit message
```

## Global flags

These flags apply to any command and are placed before the subcommand:

```bash
git_helpers --dry-run <cmd>      # print commands without executing them
git_helpers --allow-dirty <cmd>  # skip the clean worktree check
```

## Running tests

Run the suite of unit tests (pure Python, no git required):

```bash
uv run pytest utests/
```

Run the suite of validation tests (spins up real temporary git repos):

```bash
uv run vtests/run.py
```

## File structure

```
GitHelpers/
├── src/
│   └── git_helpers/
│       ├── cli_utils.py        # [entrypoint] argparse wiring and main()
│       ├── git_utils.py         # [commands] all user-facing git commands
│       ├── repo_utils.py       # [internal] read-only git helpers
│       └── shell_utils.py      # [internal] config, logging, subprocess wrappers
├── utests/                     # unit tests
├── vtests/                     # validation tests
├── pyproject.toml              # package metadata; registers the git_helpers command
├── uv.lock                     # pinned dependency versions
├── .gitignore
└── README.md
```

## License

See [LICENSE](./LICENSE).
