# Data handling and AI boundaries

The mapping engine performs no external network requests, telemetry, crash uploads, model calls, or agent execution. Browser mode sends selected files to the loopback server on the same computer; it does not upload them to a cloud service. Dependency installation and GitHub commands use the network separately.

Source rows exist in process memory during parsing/profiling. Browser mode additionally stores uploaded file copies in a private OS temporary directory for revalidation. AtlasWeave never writes back to originals. Local projects contain relative source paths, file hashes, filenames, column names, import options, aggregate statistics, candidates, and review decisions. Project downloads and handoff exports contain no raw records or sample values.

Exports remove source directory paths and omit source records. Filenames, field names, sheet names, hashes, and counts can still reveal sensitive information. Review them before sharing. A file hash can correlate an export with a known file. No credential fields are supported.

Put private input files under ignored `local-data/`, and projects/exports under ignored `outputs/`. The application cannot prevent you from writing sensitive metadata elsewhere. Delete generated files to remove saved state. Browser mode stores only its session token in sessionStorage; project state remains in server memory. Clear workspace or graceful shutdown removes temporary upload copies. A forced kill/crash may leave them behind in the OS temporary directory. There is no background database or secure-erasure guarantee.

Spreadsheet text is untrusted. The app never evaluates formulas, runs SQL, calls URLs embedded in cells, or creates spreadsheet-compatible CSV exports. Formula-injection handling will be required if a future feature writes CSV intended for spreadsheet use.

Agent briefs separate instructions from quoted JSON metadata, explicitly tell the recipient to ignore instruction-like cell/header content, and include only reviewed mappings. This is a boundary description, not a guarantee against prompt injection in an external model. Users choose whether to share the brief and must separately authorize any production changes.
