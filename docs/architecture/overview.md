# Architecture

The first implementation is one Python package with explicit module boundaries. Split distribution packages only when independent ownership or deployment requires them.

| Module | Responsibility |
| --- | --- |
| `models.py` | `ReadOptions`, `Dataset`, `SourceAdapter` protocol |
| `adapters.py` | File checks, CSV/XLSX discovery and reading |
| `strategies.py` | Column profiles, `MatchStrategy` protocol/registry, ranking, join evidence |
| `project.py` | Schema validation, snapshots, persistence, review rules, freshness checks |
| `exporters.py` | Mapping JSON and deterministic agent brief |
| `cli.py` | Argument parsing and workflow orchestration |

Data flows from adapter → bounded dataset → profiles/candidates → saved review → validated export. Core modules do not depend on a GUI, web framework, model provider, or canvas state.

## Adapter contract

Adapters declare storage, format, and shape separately; implement `discover(path)` and `read(path, ReadOptions)`; and return immutable dataset rows, field names, completeness, and warnings. File registration is currently by suffix. SQL/NoSQL source locators and credential handling do not yet exist. Future connectors need a richer source specification and schema update rather than pretending a database is a local path.

Nested documents must preserve their paths/arrays until the user explicitly selects a tabular interpretation. Adding a connector must not change strategy semantics. Contract tests should cover empty sources, nulls, stable field identity, read limits, malformed input, and resource cleanup.

## Strategy contract

Strategies receive two column profiles, normalized non-null value counters, and validated configuration. Return a score in [0,1] without I/O. Register a name, document settings/weights, and add positive cases and counterexamples. Evidence lives alongside ranking and must remain interpretable. Extending the registry currently also requires updating configuration validation, schemas, and docs; there is no third-party plugin loader.

## Export contract

The CLI calls `verify_project` before review/export. Library callers must do the same before using `decide`/`export_mapping`. Export checks approval constraints but does not locate sources on its own. Consumers validate the versioned schema and treat imported text as data. No adapter credentials, raw values, or inferred executable transformations enter the handoff.

## Scaling path

Current datasets and distinct counters are in memory; scoring considers all field pairs. Later work can introduce streaming profiles, candidate filtering, selective full validation, cancellation/progress, and database pushdown. A browser can call a local service or a separately packaged engine while retaining the mapping contract. There is no claim of browser-only processing today.
