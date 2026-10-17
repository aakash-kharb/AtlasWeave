# Repository rules and dependency maintenance

Verified on 17 October 2026 for `aakash-kharb/AtlasWeave`.

## Active GitHub settings

The [Protect main ruleset](https://github.com/aakash-kharb/AtlasWeave/rules/25297352) targets `refs/heads/main` and is active:

- All changes must go through a pull request.
- Require `Python 3.11` and `Python 3.13`, with GitHub Actions as the expected check provider.
- Require the branch to be up to date with main and review conversations to be resolved.
- Block force pushes and branch deletion, with no bypass actors.
- Require zero reviewer approvals for now, so the sole maintainer can merge their own work. Add a one-review requirement when a second maintainer is available.

The applied request is recorded in `.github/rulesets/main.json`. A file in Git does not apply a ruleset automatically; future changes must be reviewed and applied in Settings → Rules → Rulesets or through the API. Do not POST another copy just to update the current rule. No linear-history or signed-commit requirement has been introduced.

Private vulnerability reporting, Dependabot alerts, and automated security-fix PRs are enabled. Existing secret scanning and push protection remain enabled. Workflow default permissions are already read-only, and workflow tokens cannot approve PRs. Automatic dependency merging is not enabled.

These choices follow GitHub's [ruleset options](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets). Review actual CI job names before changing required checks; a renamed check can block merges until the rule is updated.

## The three current Dependabot PRs

| PR | Reviewed change | Evidence and handling |
| --- | --- | --- |
| [#2](https://github.com/aakash-kharb/AtlasWeave/pull/2) | `actions/checkout@v4` → `@v7` | One workflow line; both Python jobs passed. Suitable for explicit merge after current required checks pass. |
| [#3](https://github.com/aakash-kharb/AtlasWeave/pull/3) | `actions/setup-python@v5` → `@v7` | One workflow line; both Python jobs passed. Suitable for explicit merge after current required checks pass. |
| [#4](https://github.com/aakash-kharb/AtlasWeave/pull/4) | Permit pytest `<10` instead of `<9` | Original CI still installed locked pytest 8.4.2. The current 68-test implementation also passes in an isolated pytest 9 environment. Refresh the lock after merging this range change. |

Upstream release references: [checkout](https://github.com/actions/checkout/releases), [setup-python](https://github.com/actions/setup-python/releases). The project uses GitHub-hosted `ubuntu-latest`, not an old self-hosted runner. The browser implementation does not duplicate these upgrade diffs, so the existing PRs remain the upgrade path.

No Dependabot PR has been merged, closed, approved, or commented on by this implementation. For each PR, open it, use **Update branch** if GitHub reports it behind main, wait for its current commit's required checks, inspect Files changed, and squash merge. Handle #2, then #3, then #4; later PRs may need another branch update after earlier merges.

For CLI use, repeat this sequence for each number after reading its diff:

```bash
gh pr view 2 --repo aakash-kharb/AtlasWeave
gh pr diff 2 --repo aakash-kharb/AtlasWeave
# Only when the PR is behind main:
gh pr update-branch 2 --repo aakash-kharb/AtlasWeave
gh pr checks 2 --repo aakash-kharb/AtlasWeave --required --watch
gh pr merge 2 --repo aakash-kharb/AtlasWeave --squash
```

Do not use `--admin` to bypass a failed check. If checks have not appeared yet after a branch update, wait for the new run; the ruleset still prevents a premature merge.

## Dependency policy

The checked-in Dependabot configuration schedules updates on Monday at 09:00 Asia/Kolkata, caps ordinary open PRs at three per ecosystem, groups Python minor/patch updates and Actions minor/patch updates separately, and keeps major updates individual. Python security updates have their own group. Security updates are not delayed to the ordinary weekly schedule. Grouping follows [GitHub's documented dependency-group behavior](https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/optimizing-pr-creation-version-updates).

Review a dependency PR for API/runtime changes, license changes, new network behavior, and whether CI actually installs the proposed version. CI now checks both the pinned baseline and a clean environment resolving the versions allowed by `pyproject.toml`; the existing required Python jobs contain both checks.

`requirements-dev.lock` is a manually maintained reproducibility snapshot. Do not assume a manifest-only bot PR refreshes it. After merging a dependency range update, create a follow-up branch, install the project's updated dev requirements in a fresh environment, run the checks, and regenerate the snapshot:

```bash
python3 -m venv .venv-refresh
source .venv-refresh/bin/activate
python -m pip install -e '.[dev]'
python -m pip check
python -m pytest
ruff check .
ruff format --check .
python -m pip freeze --exclude-editable > requirements-dev.lock
```

Review the lock diff and open a PR. Do not commit the environment directory. A dedicated private conduct-reporting contact remains an owner decision; no email address has been invented.
