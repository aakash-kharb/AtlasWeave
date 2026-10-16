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
