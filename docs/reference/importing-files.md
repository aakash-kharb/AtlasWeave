# Import behavior

## CSV

UTF-8 with an optional BOM, comma by default, standard double-quote escaping and multiline quoted values. Set `--left-delimiter` or `--right-delimiter` for another one-character delimiter. There is no delimiter or encoding guessing. `--left-header-row` / `--right-header-row` select a one-based record number; for multiline CSV a record can span physical lines.

All values remain strings. An empty field is null; literal `NULL`, `NA`, and `0` remain values. Whitespace is significant unless trim is explicitly enabled. Physical blank lines are skipped. Nonempty records with the wrong field count, malformed quoting, blank headers, and case-insensitive duplicate headers are rejected. Header names are trimmed. A header-only table is valid but cannot establish a join.

## XLSX

Use `sheets` to discover sheet names. A multi-sheet workbook requires explicit selection. `.xls`, `.xlsm`, password-encrypted workbooks, merged cells, formula cells, and Excel error cells are unsupported. Merged cells anywhere in the workbook are rejected; formulas/errors in the selected scanned data are rejected. Use a values-only, unmerged export. Formula caches are not used, and formulas are not recalculated. This follows [openpyxl's distinction between formulas and cached values](https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/reader/excel.html).

Headers must be complete and unique. Trailing blank header cells are removed; data extending past them is rejected. Blank data rows are skipped, shorter rows padded with nulls, and hidden rows included. Sheet dimension hints are ignored so incorrect metadata cannot silently truncate a scan.

Text identifiers retain leading zeros. Numeric cells with simple formats such as `00000` are zero-padded. Other number formats (currency, percentages, custom sections) use underlying numeric values and emit a general warning. Date/time objects become ISO strings; booleans become `true`/`false`. Numeric precision already lost in Excel cannot be recovered.

## Bounds and scan scope

32 MiB per input file; 64 MiB expanded XLSX contents; at most 2000 ZIP entries, 100 fields, and 100000 selected data rows. Default row limit: 10000. Header selection is bounded to 10000. CSV cells also inherit Python's CSV field-size limit. These limits bound ordinary inputs; there is no hard CPU/time sandbox.

The reader checks for a further record to distinguish an exact-limit full scan from a truncated sample. Rows after the sample are not validated. Approval is blocked for samples. File SHA-256 hashes cover the full bytes even when profiling is sampled. Parsed selected rows are held in memory. These are engineering limits, not measured throughput claims.

## SQLite snapshots

Use a closed standalone `.sqlite`, `.sqlite3`, or `.db` file in DELETE journal mode, up to 32 MiB. This release imports snapshots, not live database connections. Export a standalone copy through your database application's backup/export facility; do not change the journal mode of a production database just to import it. WAL-mode headers and local `-wal`, `-shm`, or `-journal` sidecars are rejected. Uploading only the main file of a WAL database can omit recent data.

```bash
# Create a synthetic snapshot without overwriting an existing file.
python scripts/create_sqlite_example.py --out local-data/demo.sqlite
atlasweave tables local-data/demo.sqlite
atlasweave discover local-data/demo.sqlite local-data/demo.sqlite \
  --left-table orders --right-table customers --out outputs/sqlite-project.json
atlasweave review outputs/sqlite-project.json left.f1--right.f1 --status approved
atlasweave export outputs/sqlite-project.json --out-dir outputs/sqlite-handoff
```

A SQLite source always requires explicit table selection, even with one table. Combine it with CSV/XLSX on either side. In the browser, upload the snapshot and choose **Table**. Table selection is saved and exported. Changing it resets decisions on rediscovery. SQLite column names replace spreadsheet headers; sheet/header/delimiter overrides are rejected.

Only ordinary tables are supported. Views and virtual/shadow tables are excluded from the list; generated/hidden columns and BLOB cells fail explicitly. TEXT is preserved exactly, including leading zeros. Integers and real values use their stored value rendered as text; formatting already lost through SQLite numeric affinity cannot be reconstructed. Empty text and SQL NULL become null keys, which never match. A scan that exceeds the row limit remains sampled and cannot be approved. There is no promise about which rows a partial scan includes.

The reader copies bounded file bytes into an in-memory connection; it never opens the source with SQLite. It requires SQLite 3.37+ and Python's `Connection.deserialize`. It disables trusted schema, sets query-only mode, quotes catalog-verified identifiers, and blocks attachments/functions/writes through an authorizer. At most 1000 catalog entries, 100 columns, and 100000 selected rows are accepted; a 10-million-instruction VM budget bounds database work. This is not query pushdown for profiling: matching still runs in Python.

References: [Python SQLite serialization and authorization](https://docs.python.org/3/library/sqlite3.html), [SQLite trusted schema](https://www.sqlite.org/pragma.html#pragma_trusted_schema), and [SQLite WAL file lifecycle](https://www.sqlite.org/wal.html).
