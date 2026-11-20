# Changelog

## 0.3.0a1 — unreleased

- Add read-only SQLite snapshot imports, explicit table selection in CLI/browser, and table-aware saved projects/agent exports.
- Reject live/WAL databases, sidecars, views, virtual tables, generated columns, and BLOB cells; preserve TEXT identifiers without numeric coercion.
- Add synthetic adapter, CLI, HTTP, and installed-wheel coverage plus a SQLite example generator.
- Refresh the pytest lock to 9.1.1 after the merged dependency-range update.
- Existing 0.2 projects require rediscovery; remote database connections and background processing remain deferred.

## 0.2.0a1 — browser milestone (merged 17 October 2026)

- Add `atlasweave serve`: local browser workspace for CSV/XLSX import, review, and export.
- Add sheet/settings controls, search, candidate comparison, manual pairs, and save/reopen.
- Add a navy/ivory interface using the supplied logo unchanged.
- Add loopback Host/Origin/token checks, bounded uploads, safe project reopening, and stale-tab revisions.
- Extend project-v1 with optional manual pairs; keep mapping-v1 unchanged. Old engine snapshots require rediscovery.
- Add server/workspace regression tests and test allowed dependency versions in CI.
- Document main-branch protections and group routine Dependabot updates without auto-merging.

## 0.1.0a1 — foundation

- Add a local CSV/XLSX discovery, inspection, review, and export CLI.
- Add deterministic name/alias, type, overlap, and uniqueness strategies.
- Add null/duplicate/unmatched evidence and projected join sizes.
- Add version 1 project/export schemas and source freshness checks.
- Add synthetic regression tests, contribution guidance, and Python CI.
- Defer browser UI, visualization, SQL/NoSQL connectors, and execution.
