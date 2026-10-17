# Development

Create a virtual environment and install `.[dev]` as shown in the README. Python 3.11 is the minimum; CI checks 3.11 and 3.13. The initial implementation was validated locally on Python 3.13.

`requirements-dev.lock` pins the runtime/development dependency versions used during local validation. To reproduce them, install that file, then install the package with `python -m pip install --no-deps -e .`. The project metadata permits compatible dependency updates; refresh the lock deliberately and rerun checks. The build backend is resolved separately by build isolation.

```bash
python -m pytest
ruff check .
ruff format --check .
python scripts/generate_schemas.py
git diff --exit-code -- src/atlasweave/schemas
python -m build
```

Run the browser with `atlasweave serve`. The package serves its own static assets; no frontend installation or build step is needed. `node --check src/atlasweave/web/app.js` checks JavaScript syntax if Node is installed. Browser regression coverage includes a real loopback HTTP server, so tests require permission to bind local ports.

CI runs the test suite with both locked dependencies and a fresh resolution of the package's allowed dependency ranges. This prevents a manifest-only dependency PR from appearing validated while CI still runs an older pinned version.

Tests cover CSV quoting/encoding, Excel sheets/number formats, malformed inputs, aliases and normalization, misleading/no-overlap candidates, duplicates/nulls, sample restrictions, stale source/configuration detection, save/load, export privacy, and the actual CLI workflow. Workspace tests cover manual pairs, approval preservation/reset, safe reopening, temporary-file cleanup, stale tabs, binary upload bounds, Host/Origin/token rejection, static-path allowlisting, and HTTP review/export. XLSX fixtures are generated in temporary test directories using synthetic values, never drawn from personal files.

For a package change, install the built wheel in a fresh environment and run discovery/review/export from outside the repository. Also run `python /absolute/path/to/AtlasWeave/scripts/smoke_browser.py` with that environment's interpreter. This verifies packaged JSON schemas, browser assets/demo files, the HTTP workflow, and the console entry point, not just imports from `src/`.

There are no benchmarks yet. Before raising workload limits, publish datasets, hardware, runtime/memory measurements, expected matches, and false-positive/false-negative metrics. Faster ranking alone does not establish mapping quality.
