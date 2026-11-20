"""Local readers. No evaluation, network access, or source-file writes."""

import csv
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from defusedxml.ElementTree import iterparse
from openpyxl import load_workbook

from atlasweave.models import AtlasWeaveError, Dataset, ReadOptions, SourceAdapter

MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_FIELDS = 100


def check_file(path: str) -> Path:
    source = Path(path)
    if not source.is_file():
        raise AtlasWeaveError(f"Source is not a file: {source}")
    if source.stat().st_size > MAX_FILE_BYTES:
        raise AtlasWeaveError("File exceeds the 32 MiB safety limit.")
    return source


def headers(values) -> tuple[str, ...]:
    result = tuple(str(value).strip() if value is not None else "" for value in values)
    if not result or len(result) > MAX_FIELDS:
        raise AtlasWeaveError("Expected between 1 and 100 columns.")
    if any(not name for name in result):
        raise AtlasWeaveError("Blank column names are unsupported; supply a complete header row.")
    if len({name.casefold() for name in result}) != len(result):
        raise AtlasWeaveError("Duplicate column names are ambiguous; rename them before importing.")
    return result


class CsvAdapter:
    storage, format, shape = "file", "csv", "table"

    def discover(self, path: str) -> list[str]:
        return [check_file(path).name]

    def read(self, path: str, options: ReadOptions) -> Dataset:
        source = check_file(path)
        if options.table is not None:
            raise AtlasWeaveError("Table selection applies only to SQLite files.")
        if options.sheet is not None:
            raise AtlasWeaveError("Sheet selection applies only to XLSX files.")
        try:
            with source.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.reader(stream, delimiter=options.delimiter, strict=True)
                for _ in range(options.header_row - 1):
                    next(reader, None)
                names = headers(next(reader, []))
                rows = []
                complete = True
                for values in reader:
                    if not values:  # Physical blank lines, not records of empty fields.
                        continue
                    if len(values) != len(names):
                        raise AtlasWeaveError(
                            f"CSV row near line {reader.line_num} has wrong width."
                        )
                    if len(rows) == options.max_rows:
                        complete = False
                        break
                    rows.append(tuple(value if value != "" else None for value in values))
        except (UnicodeError, csv.Error) as exc:
            raise AtlasWeaveError("Invalid CSV: use UTF-8 and check quoting/delimiter.") from exc
        return Dataset(source.name, names, tuple(rows), complete)


def check_workbook(path: str) -> Path:
    source = check_file(path)
    try:
        with ZipFile(source) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(e.file_size for e in entries) > MAX_EXPANDED_BYTES:
                raise AtlasWeaveError("XLSX exceeds the expanded archive safety limit (64 MiB).")
            # Read-only openpyxl does not expose merged ranges. Reject them explicitly.
            for entry in entries:
                if entry.filename.startswith("xl/worksheets/") and entry.filename.endswith(".xml"):
                    with archive.open(entry) as stream:
                        for _, element in iterparse(stream, events=("end",)):
                            if element.tag.endswith("}mergeCell"):
                                raise AtlasWeaveError("Unmerge workbook cells before importing.")
                            element.clear()
    except BadZipFile as exc:
        raise AtlasWeaveError("Invalid XLSX archive.") from exc
    return source


def cell_text(cell) -> str | None:
    if cell.data_type == "f":
        raise AtlasWeaveError("Formula cells are unsupported; export a values-only sheet first.")
    if cell.data_type == "e":
        raise AtlasWeaveError("Excel error cells are unsupported; correct the source first.")
    value = cell.value
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (int, float)):
        if re.fullmatch(r"0+", cell.number_format) and float(value).is_integer():
            return str(int(value)).zfill(len(cell.number_format))
        return str(int(value)) if float(value).is_integer() else str(value)
    return str(value)


class XlsxAdapter:
    storage, format, shape = "file", "xlsx", "table"

    def discover(self, path: str) -> list[str]:
        workbook = load_workbook(check_workbook(path), read_only=True, keep_links=False)
        try:
            return workbook.sheetnames
        finally:
            workbook.close()

    def read(self, path: str, options: ReadOptions) -> Dataset:
        if options.table is not None:
            raise AtlasWeaveError("Table selection applies only to SQLite files.")
        source = check_workbook(path)
        workbook = load_workbook(source, read_only=True, data_only=False, keep_links=False)
        try:
            if options.sheet is None and len(workbook.sheetnames) != 1:
                raise AtlasWeaveError(
                    "Workbook has multiple sheets; select one with --left-sheet "
                    "or --right-sheet. Use the sheets command to list them."
                )
            name = options.sheet if options.sheet is not None else workbook.sheetnames[0]
            if name not in workbook.sheetnames:
                raise AtlasWeaveError(f"Unknown worksheet: {name!r}")
            sheet = workbook[name]
            # Ignore unreliable dimension metadata; read actual worksheet cells.
            sheet.reset_dimensions()
            iterator = sheet.iter_rows(min_row=options.header_row)
            first = list(next(iterator, ()))
            while first and first[-1].value is None:
                first.pop()
            names = headers([cell_text(cell) for cell in first])
            rows = []
            complete = True
            for cells in iterator:
                if all(cell.value is None for cell in cells):
                    continue
                if len(cells) > len(names) and any(
                    c.value is not None for c in cells[len(names) :]
                ):
                    raise AtlasWeaveError("Worksheet data extends beyond the selected headers.")
                if len(rows) == options.max_rows:
                    complete = False
                    break
                values = [cell_text(cell) for cell in cells[: len(names)]]
                values.extend([None] * (len(names) - len(values)))
                rows.append(tuple(values))
            warnings = (
                "Hidden rows are included. Only simple zero-padding number formats are preserved; "
                "other numeric display formats use underlying values.",
            )
            return Dataset(source.name, names, tuple(rows), complete, warnings)
        finally:
            workbook.close()


@contextmanager
def sqlite_snapshot(path):
    """Read a standalone snapshot into memory; never open the source with SQLite."""
    source = check_file(path)
    with source.open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise AtlasWeaveError("File exceeds the 32 MiB safety limit.")
    if len(data) < 100 or data[:16] != b"SQLite format 3\x00":
        raise AtlasWeaveError("Invalid SQLite database file.")
    if data[18:20] != b"\x01\x01" or any(
        Path(str(source) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")
    ):
        raise AtlasWeaveError(
            "Use a closed, standalone SQLite snapshot in DELETE journal mode. "
            "Live/WAL databases and journal sidecars are not supported."
        )
    connection = sqlite3.connect(":memory:")
    try:
        if not hasattr(connection, "deserialize") or sqlite3.sqlite_version_info < (3, 37, 0):
            raise AtlasWeaveError("SQLite import requires SQLite 3.37+ with deserialize support.")
        connection.deserialize(data)
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA query_only = ON")

        def authorize(action, name, _argument, _database, _trigger):
            if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ):
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_PRAGMA and name in ("table_list", "table_xinfo"):
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        connection.set_authorizer(authorize)
        # Cap SQLite VM work as well as the fetched row count.
        steps = 0

        def bounded_work():
            nonlocal steps
            steps += 1
            return int(steps > 1000)

        connection.set_progress_handler(bounded_work, 10000)
        yield connection
    except sqlite3.Error as exc:
        raise AtlasWeaveError(
            "Could not read SQLite snapshot: invalid/unsupported content or query work limit."
        ) from exc
    finally:
        connection.close()


def sqlite_tables(connection):
    entries = connection.execute("PRAGMA main.table_list").fetchmany(1001)
    if len(entries) > 1000:
        raise AtlasWeaveError("SQLite snapshot exceeds the 1000-table catalog limit.")
    return sorted(
        name
        for schema, name, kind, *_ in entries
        if schema == "main" and kind == "table" and not name.startswith("sqlite_")
    )


def sql_identifier(name):
    # SQLite parameters bind values, not identifiers. Only discovered names reach this.
    return '"' + name.replace('"', '""') + '"'


def sqlite_text(value):
    if isinstance(value, bytes):
        raise AtlasWeaveError("SQLite BLOB cells are unsupported; export text columns first.")
    if value is None or value == "":
        return None
    # Preserve TEXT identifiers exactly; do not apply numeric affinity or SQL casts.
    return value if isinstance(value, str) else str(value)


class SqliteAdapter:
    storage, format, shape = "file", "sqlite", "table"

    def discover(self, path: str) -> list[str]:
        with sqlite_snapshot(path) as connection:
            names = sqlite_tables(connection)
            if not names:
                raise AtlasWeaveError("SQLite snapshot has no supported ordinary tables.")
            return names

    def read(self, path: str, options: ReadOptions) -> Dataset:
        if options.sheet is not None or options.header_row != 1 or options.delimiter != ",":
            raise AtlasWeaveError("SQLite uses table columns; sheet/header/delimiter do not apply.")
        with sqlite_snapshot(path) as connection:
            names = sqlite_tables(connection)
            if options.table is None:
                raise AtlasWeaveError("Select a SQLite table with --left-table or --right-table.")
            if options.table not in names:
                raise AtlasWeaveError("Unknown or unsupported SQLite table; list tables first.")
            table = sql_identifier(options.table)
            columns = connection.execute(f"PRAGMA main.table_xinfo({table})").fetchall()
            if any(column[6] != 0 for column in columns):
                raise AtlasWeaveError("SQLite generated/hidden columns are unsupported.")
            original_names = [column[1] for column in columns]
            names = headers(original_names)
            if tuple(original_names) != names:
                raise AtlasWeaveError("Rename SQLite columns with surrounding whitespace first.")
            selection = ", ".join(sql_identifier(name) for name in names)
            # No user SQL, views, virtual tables, functions, or SQL-side key coercion.
            cursor = connection.execute(
                f"SELECT {selection} FROM main.{table} LIMIT ?", (options.max_rows + 1,)
            )
            rows = cursor.fetchmany(options.max_rows + 1)
            complete = len(rows) <= options.max_rows
            rows = tuple(tuple(sqlite_text(v) for v in row) for row in rows[: options.max_rows])
            return Dataset(
                Path(path).name,
                names,
                rows,
                complete,
                (
                    "SQLite stored values are used. Zeros already lost to numeric affinity cannot "
                    "be recovered. Only ordinary tables from standalone snapshots are supported.",
                ),
            )


ADAPTERS: dict[str, SourceAdapter] = {
    ".csv": CsvAdapter(),
    ".xlsx": XlsxAdapter(),
    **{suffix: SqliteAdapter() for suffix in (".sqlite", ".sqlite3", ".db")},
}


def adapter_for(path: str) -> SourceAdapter:
    try:
        return ADAPTERS[Path(path).suffix.lower()]
    except KeyError as exc:
        raise AtlasWeaveError(
            "Supported file formats: .csv, .xlsx, .sqlite, .sqlite3, and .db."
        ) from exc
