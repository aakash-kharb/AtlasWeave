# Contributing

AtlasWeave is an early project maintained by [Aakash Kharb](https://github.com/aakash-kharb). Useful contributions include parser fixes, reproducible matching counterexamples, clearer evidence, and documentation improvements.

## Start locally

Follow the README installation instructions. For the exact dependency snapshot used during initial validation, install `requirements-dev.lock` before the editable package:

```bash
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
python -m pytest
ruff check .
ruff format --check .
```

## Propose a change

Small fixes and documentation improvements can arrive directly as PRs. Open an issue before adding a connector, strategy, dependency, or changing the mapping format. Explain the user problem, an example, failure cases, and alternatives. Avoid adding scaffolding for integrations without a working path to test them.

Branch from current `main`; keep PRs focused. Describe what changes for the user and what validation you ran. Parser and matching changes need synthetic input fixtures and expected evidence, including counterexamples. Future UI changes should include screenshots and keyboard checks. Documentation-only edits do not need artificial tests.

Run the checks above. Contract changes require regenerating schemas with `python scripts/generate_schemas.py`; packaging changes require `python -m build` and an installed-wheel smoke test. CI runs on pull requests with read-only repository permissions.

## Review and attribution

AI-assisted contributions follow the same standards. Check automated review findings yourself; a bot approval does not establish correctness. Preserve original authorship and required notices when adapting others' work. Use only synthetic data or data explicitly licensed for redistribution.

By contributing, you offer your contribution under this repository's MIT license and retain copyright in your work. No separate CLA or DCO is required at this stage. Follow the [code of conduct](CODE_OF_CONDUCT.md); report vulnerabilities through [SECURITY.md](SECURITY.md).
