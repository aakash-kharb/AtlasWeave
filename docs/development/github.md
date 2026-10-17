# Working with GitHub

The foundation is merged. The local browser milestone is on `feat/local-browser-workspace`, with uncommitted changes ready for review. `origin` already points at `https://github.com/aakash-kharb/AtlasWeave`; do not run `git init` or force-push.

## Publish this milestone

```bash
cd "$HOME/Downloads/AtlasWeave"
source .venv/bin/activate
git status --short --branch
python -m pytest
ruff check .
ruff format --check .
python -m build
```

Review the changes and staged filenames before committing. `local-data/`, `outputs/`, environments, and build artifacts are ignored; never add private source files elsewhere.

```bash
git diff --stat
git add .
git diff --cached --stat
git diff --cached --check
git commit -m "Add local browser mapping workspace and repository maintenance"
git push -u origin feat/local-browser-workspace
gh pr create --base main --head feat/local-browser-workspace \
  --title "Add local browser mapping workspace" \
  --body "Add authenticated loopback CSV/Excel import, evidence review, manual field pairs, comparison, project persistence, and mapping/agent exports. Include browser boundary tests, packaged assets, dependency compatibility CI, and maintenance documentation."
```

These publishing commands have not been run for you. If authentication is needed, use `gh auth login` and `gh auth setup-git`. Resolve any main-branch changes through a normal merge or rebase and re-run checks; never bypass the ruleset. Once the PR exists, use `gh pr checks --required --watch` and review it before merging.

## Repository maintenance

Main now requires PRs and the two Python CI jobs; force pushes and deletion are blocked. Review approvals remain optional for the solo maintainer. Security alerts and private vulnerability reporting are enabled. See [repository maintenance](repository-maintenance.md) for the active ruleset, the three existing Dependabot PRs, merge commands, and lock-file policy.

The revised Dependabot schedule/grouping and CI compatibility check take effect after this branch is merged. No automatic merging is configured. A private conduct-reporting contact remains an owner decision.

## Start later work

From a clean working tree after the current PR is merged:

```bash
git switch main
git pull --ff-only
git switch -c codex/describe-your-change
# Edit and run the documented checks.
git add path/to/changed-files
git commit -m "Describe the user-facing change"
git push -u origin HEAD
gh pr create
```

AtlasWeave runs locally. No remote hosting or deployment is required.
