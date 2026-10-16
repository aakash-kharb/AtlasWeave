# Working with GitHub

The workspace was cloned from `https://github.com/aakash-kharb/AtlasWeave`; `origin` and the original MIT-license commit are already present. Do not run `git init` or force-push over that history. Implementation files are uncommitted for your review.

## Publish the first implementation

Run from the existing checkout:

```bash
cd "$HOME/Downloads/AtlasWeave"
source .venv/bin/activate
git status --short --branch
git remote -v
git switch -c feat/mapping-foundation
python -m pytest && ruff check . && ruff format --check .
```

After the checks pass, review the files, then commit and publish the branch:

```bash
git add .
git diff --cached --stat
git diff --cached --check
git commit -m "Build AtlasWeave CSV and Excel mapping foundation"
git push -u origin feat/mapping-foundation
gh pr create --base main --head feat/mapping-foundation \
  --title "Build CSV and Excel mapping foundation" \
  --body "Add local import, evidence-backed suggestions, explicit review, versioned mapping and agent exports, documentation, and CI. Includes synthetic parser and workflow tests. Visualization remains deferred."
```

If `gh` needs authentication, run `gh auth login` and `gh auth setup-git`. If the branch already exists, use `git switch feat/mapping-foundation`. These commands publish only when you run them. Inspect CI and the PR before merging.

## Future work

```bash
git switch main
git pull --ff-only
git switch -c feat/describe-your-change
# Edit and run the documented checks.
git add path/to/changed-files
git commit -m "Describe the user-facing change"
git push -u origin HEAD
gh pr create
```

## Repository settings to configure

- Enable private vulnerability reporting before inviting security reports.
- Enable Issues and retain the bug/feature/connector/strategy templates.
- After the first CI run, require its Python matrix checks on `main` using a ruleset.
- Choose review requirements practical for a solo maintainer; do not require an unavailable second reviewer.
- Limit default Actions permissions to read access and enable dependency alerts/updates.
- Add a private conduct-reporting contact to the community policy.

No repository settings, remote branches, PRs, or releases are changed by the implementation itself. A hosting/deployment workflow is deferred until there is a web application to deploy.
