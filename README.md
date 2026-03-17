# Git Helpers

`git_helpers` is a CLI tool that collects and packages up common `git` workflows into single commands. Each command narrates what it's doing and prints the `git` commands it's running internally, so you can learn the underlying mechanics while getting the job done.

## Getting setup

```bash
git clone git@github.com:AstroKriel/GitHelpers.git
cd GitHelpers
uv sync
```

After installing, run commands through the managed environment:

```bash
uv run git_helpers <subcommand> [args]
```

## Commands

**Configuration**
```bash
git_helpers set-global-config       # write FF-first merge defaults + rerere to ~/.gitconfig
git_helpers show-global-config      # print current values of those settings
```

**Inspection**
```bash
git_helpers branches-status         # fetch, then show all branches with upstream + ahead/behind
git_helpers ahead-behind            # how many commits ahead/behind the current branch is
git_helpers show-upstream           # show the upstream ref and its latest commit
git_helpers unpulled-commits        # list commits on upstream not yet pulled
git_helpers show-recent-commits [N] # last N commits on current branch (default: 20)
git_helpers local-remotes           # list all remotes and their URLs
git_helpers submodules-status       # show SHA and init status of each submodule
git_helpers is-detached             # exit 0 if HEAD is detached (usable in shell conditionals)
```

**Branches**
```bash
git_helpers create-branch-from-default <name>          # cut from remote default branch + push
git_helpers create-branch-from-remote <name> <ref>     # cut from explicit remote ref + push
git_helpers track-remote-branch <remote/branch> [name] # create local branch tracking a remote one
git_helpers delete-local-branch <name>                 # safe delete (refuses if unmerged)
git_helpers prune-gone-locals                          # delete branches whose remote was deleted
git_helpers prune-merged-locals [base]                 # delete branches merged into base
git_helpers cleanup-local-branches [base]              # run both prune steps in sequence
```

**Syncing**
```bash
git_helpers push                     # push current branch; sets upstream automatically if needed
git_helpers sync-branch [base]       # pull/merge with --ff; merge explicit base if provided
git_helpers rename-last-commit <msg> # amend the most recent commit message
```

## Toggles

Behaviour can be adjusted at runtime via environment variables:

```bash
GIT_VERBOSE=0   git_helpers <cmd>   # suppress narration (default: on)
GIT_DRYRUN=1    git_helpers <cmd>   # print commands without executing them
GIT_ALLOW_DIRTY=1 git_helpers <cmd> # skip the clean worktree check
```

## File structure

```
GitHelpers/
├── src/
│   └── git_helpers/
│       ├── shell_utils.py   # toggles, logging, subprocess wrappers
│       ├── inspect_repo.py  # read-only git state helpers (branch, upstream, remote)
│       ├── run_cmds.py      # all user-facing git commands
│       └── cli_utils.py     # argparse wiring and entry point
├── pyproject.toml           # package metadata; registers the git_helpers command
├── uv.lock                  # pinned dependency versions
├── .gitignore
└── README.md
```

## License

See [LICENSE](./LICENSE).
