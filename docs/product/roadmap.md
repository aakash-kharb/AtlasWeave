# Roadmap

## Milestone 1 — foundation published

- Import two CSV/XLSX tables with explicit parsing options.
- Preserve text identifiers and distinguish nulls from actual values.
- Rank candidate fields with attributable heuristic components.
- Show duplicates, unmatched rows, nulls, and projected output counts.
- Require deliberate review; block sampled/stale evidence from approval/export.
- Save/load a versioned project and export approved decisions without raw records.
- Provide synthetic regression tests and an open-source contribution baseline.

Acceptance example: `cust_id → Customer ID`, two shared keys, two unmatched left rows, three inner-join rows, five left-join rows. Mixed XLSX/CSV workflow has a generated synthetic test fixture.

## Milestone 2 — interaction implemented locally

A local browser interface now provides import/review/export, native keyboard controls, manual field pairs, error states, project save/reopen, and comparison of up to three candidates. Static HTML/CSS/JavaScript is served by the Python package without a frontend build. The user-supplied emblem and navy/ivory palette keep the presentation symbolic and direct.

The browser and CLI share evidence and approval logic. There is no canvas, model-provider integration, hosted deployment, or database connector. Wider accessibility testing and larger-workload benchmarks remain future work.

## Milestone 3 — extension

Introduce SQLite/PostgreSQL adapters, query pushdown, cancellation/progress, and benchmarks. Model storage, format, and shape separately. Nested documents and arrays need an explicit interpretation contract before NoSQL adapters are presented as supported.

## Before broader release

Branch protection, private vulnerability reporting, and Dependabot security updates are configured on GitHub. Choose a private community contact, review dependency licenses, and evaluate matching quality on a published synthetic corpus before broader release. Do not advertise performance numbers before measuring them.
