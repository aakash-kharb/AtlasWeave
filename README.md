# AtlasWeave

**Find the threads connecting your data.**

AtlasWeave discovers possible relationships between CSV and Excel files, explains the evidence, and exports reviewed decisions for an AI agent to implement.

**Status: local browser workspace and CLI alpha.** Import two files, inspect and compare relationships, approve the rules, then download a reusable `mapping.json` and an agent brief. SQL/NoSQL connectors and pipeline execution remain future work.

## Try it

Requires Python 3.11 or later. Run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

atlasweave serve
```

The command opens the local workspace. Choose your CSV/XLSX files, or click **Explore sample data**. The app uses the same engine as the CLI. No Node build, account, cloud upload, or model API is required. Stop the server with Ctrl+C to remove its temporary upload copies. See the [browser workspace guide](docs/getting-started/browser-workspace.md) for saving and reopening a project.

For the command-line workflow:

```bash

atlasweave discover examples/orders.csv examples/customers.csv \
  --out outputs/first-project.json
atlasweave inspect outputs/first-project.json --search cust
atlasweave review outputs/first-project.json left.f1--right.f1 \
  --status approved --join left
atlasweave export outputs/first-project.json --out-dir outputs/first-handoff
```

The example suggests `cust_id → Customer ID`, with two shared distinct keys, two unmatched order rows (including one null key), and a projected five-row left join. `001` stays `001`. Read `outputs/first-handoff/agent-brief.md` and `mapping.json` before sharing them with an agent. Re-running discovery/export requires a new destination; existing outputs are not overwritten.

For Excel:

```bash
atlasweave sheets local-data/customers.xlsx
atlasweave discover local-data/orders.csv local-data/customers.xlsx \
  --right-sheet Customers --out outputs/excel-project.json
```

Use your own files in the ignored `local-data/` directory. XLSX parsing is covered by synthetic automated fixtures; no private workbook is bundled.

## Implemented

- UTF-8 CSV and XLSX readers, sheet/header selection, and explicit delimiters.
- Field-name search, profiles, aliases, type comparison, value overlap, and uniqueness ranking.
- Full-scan versus sampled evidence, duplicate/null keys, unmatched rows, and join expansion counts.
- Approval, rejection, reset, left/inner join rules, and optional trim/casefold normalization.
- Responsive browser workspace with file selection/drop zones, sheet selection, search, candidate comparison, and manual pairs.
- Browser project save/reopen and downloadable mapping JSON/agent briefs.
- Versioned project/export schemas, source fingerprints, and revalidation before review/export.
- Local processing with no external network calls, telemetry, model calls, or automatic agent execution. The browser talks only to the loopback server.

Scores rank candidates; they are **not probabilities**. Similar column names alone do not establish a valid join. Approval requires shared values and a complete scan. Right-hand keys must be unique and non-null by default; explicit review flags can relax those requirements.

## Boundaries

This alpha handles two tabular sources and single-column relationships. Defaults scan up to 10,000 records per source; the configurable cap is 100,000. File size is limited to 32 MiB, expanded XLSX archives to 64 MiB, and tables to 100 fields. These are safety bounds, not benchmark claims. Selected rows are held in memory, and all field pairs are scored.

Formula/error cells and merged Excel cells are rejected; AtlasWeave does not recalculate workbooks. Hidden rows are included. Text identifiers and simple numeric zero-padding formats are preserved; other numeric formats use underlying values. See [import behavior](docs/reference/importing-files.md).

Saved projects retain source references, field names, hashes, review decisions, and aggregate evidence. Exports omit directory paths and raw records, but metadata can still be sensitive. See [data handling](docs/trust/data-handling.md).

## Develop and contribute

```bash
python -m pytest
ruff check .
ruff format --check .
python scripts/generate_schemas.py
python -m build
```

See [CONTRIBUTING.md](CONTRIBUTING.md), the [documentation index](docs/README.md), and [GitHub setup](docs/development/github.md). Small fixes are welcome; discuss new connectors, dependencies, and mapping-format changes first.

MIT © 2026 Aakash Kharb. Contributors retain copyright in their contributions.
