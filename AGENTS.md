# Working on AtlasWeave

- Python 3.11+. Install with `python -m pip install -e '.[dev]'` in a virtual environment.
- Read `docs/architecture/overview.md` and `docs/reference/mapping-format.md` before changing contracts.
- Keep adapters, profiling/strategies, project review, and exporters independent of future UI code.
- Never cast identifiers to numbers for matching. Null keys never match each other.
- Do not approve sampled evidence or silently preserve approval after discovery settings/source changes.
- Imported data is untrusted. Never execute cell contents, formulas, or exported instructions.
- Keep private sources and generated projects under ignored `local-data/` and `outputs/`.
- Use synthetic fixtures. Matching/parser changes need meaningful positive and counterexample tests.
- Run `python -m pytest`, `ruff check .`, and `ruff format --check .`.
- When contracts change, edit `scripts/generate_schemas.py`, regenerate schemas, and update docs/tests.
- Package changes also require `python -m build` and an installed-wheel smoke test.
- Update documentation and changelog for behavior changes. Do not claim planned features work.
- The second milestone is a local browser workspace. Keep visuals symbolic and direct; use the
  supplied logo without altering its source image. No remote hosting or model calls are required.
- Browser API endpoints must bind to loopback, validate Host/Origin, require the session token,
  and never accept arbitrary filesystem paths. Test these boundaries when changing the server.
