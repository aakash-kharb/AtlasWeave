# Working with GitHub

The foundation, local browser workspace, and dependency PRs #2–#5 are merged. SQLite snapshot support is on `codex/sqlite-sources`, with uncommitted changes ready for review. `origin` already points at `https://github.com/aakash-kharb/AtlasWeave`; do not run `git init` or force-push.

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
git commit -m "Add read-only SQLite snapshot sources"
git push -u origin codex/sqlite-sources
gh pr create --base main --head codex/sqlite-sources \
  --title "Add read-only SQLite snapshot sources" \
  --body "Add ordinary-table selection for standalone SQLite snapshots in CLI and browser, preserve text identifiers, bind table metadata to reviewed exports, and test import boundaries. Refresh the pytest lock and document SQLite limits."
```

These publishing commands have not been run for you. If authentication is needed, use `gh auth login` and `gh auth setup-git`. Resolve any main-branch changes through a normal merge or rebase and re-run checks; never bypass the ruleset. Once the PR exists, use `gh pr checks --required --watch` and review it before merging.

## Repository maintenance

Main now requires PRs and the two Python CI jobs; force pushes and deletion are blocked. Review approvals remain optional for the solo maintainer. Security alerts and private vulnerability reporting are enabled. See [repository maintenance](repository-maintenance.md) for the active ruleset, the merged Dependabot PRs, merge commands, and lock-file policy.

The Dependabot schedule/grouping and CI compatibility check are active on main. No automatic merging is configured. A private conduct-reporting contact remains an owner decision.

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
