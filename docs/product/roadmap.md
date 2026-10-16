# Roadmap

## Milestone 1 — implemented locally, awaiting first publication

- Import two CSV/XLSX tables with explicit parsing options.
- Preserve text identifiers and distinguish nulls from actual values.
- Rank candidate fields with attributable heuristic components.
- Show duplicates, unmatched rows, nulls, and projected output counts.
- Require deliberate review; block sampled/stale evidence from approval/export.
- Save/load a versioned project and export approved decisions without raw records.
- Provide synthetic regression tests and an open-source contribution baseline.

Acceptance example: `cust_id → Customer ID`, two shared keys, two unmatched left rows, three inner-join rows, five left-join rows. Mixed XLSX/CSV workflow has a generated synthetic test fixture.

## Milestone 2 — interaction

A practical import/review/export interface with keyboard access, manual mappings, understandable failure states, and comparison of competing candidates. Keep visuals symbolic and direct. UI technology and branding are not chosen by the CLI implementation.

## Milestone 3 — extension

Introduce SQLite/PostgreSQL adapters, query pushdown, cancellation/progress, and benchmarks. Model storage, format, and shape separately. Nested documents and arrays need an explicit interpretation contract before NoSQL adapters are presented as supported.

## Before broader release

Enable private vulnerability reporting, choose a private community contact, configure branch protections, review dependency licenses, and evaluate matching quality on a published synthetic corpus. Do not advertise performance numbers before measuring them.
