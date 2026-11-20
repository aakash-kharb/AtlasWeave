import hashlib
import json
import sqlite3
from copy import deepcopy

import pytest

from atlasweave.adapters import adapter_for, sqlite_snapshot
from atlasweave.cli import main
from atlasweave.exporters import agent_brief, export_mapping
from atlasweave.models import AtlasWeaveError, ReadOptions
from atlasweave.project import decide, discover, validate_document, verify_project


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "customers ?#.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE "Customer lookup" ("Customer ID" TEXT, name TEXT)')
        connection.executemany(
            'INSERT INTO "Customer lookup" VALUES (?, ?)',
            [("001", "Ada"), ("002", "Lin"), ("003", "Sam")],
        )
        connection.execute("CREATE TABLE empty_table (id TEXT)")
    connection.close()
    return path


def test_table_discovery_values_and_no_source_writes(database):
    before = database.read_bytes()
    reader = adapter_for(str(database))
    assert reader.discover(str(database)) == ["Customer lookup", "empty_table"]
    data = reader.read(str(database), ReadOptions(table="Customer lookup"))
    assert data.fields == ("Customer ID", "name")
    assert data.rows[0] == ("001", "Ada")
    assert data.complete
    assert reader.read(str(database), ReadOptions(table="empty_table")).rows == ()
    assert database.read_bytes() == before
    assert not list(database.parent.glob("*-journal"))


def test_requires_explicit_known_table(database):
    reader = adapter_for(str(database))
    with pytest.raises(AtlasWeaveError, match="Select a SQLite table"):
        reader.read(str(database), ReadOptions())
    with pytest.raises(AtlasWeaveError, match="Unknown or unsupported"):
        reader.read(str(database), ReadOptions(table='Customer lookup"; DROP TABLE empty_table;--'))
    assert "empty_table" in reader.discover(str(database))


def test_quoted_table_and_column_names_are_literals(database):
    table = 'x"; DROP TABLE empty_table;--'
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE "x""; DROP TABLE empty_table;--" ("id""code" TEXT)')
        connection.execute('INSERT INTO "x""; DROP TABLE empty_table;--" VALUES (?)', ("007",))
    connection.close()
    reader = adapter_for(str(database))
    data = reader.read(str(database), ReadOptions(table=table))
    assert data.fields == ('id"code',) and data.rows == (("007",),)
    assert "empty_table" in reader.discover(str(database))


def test_text_identifiers_nulls_and_stored_numeric_values(database):
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE typed (code TEXT, stored INTEGER, nullable TEXT)")
        connection.executemany(
            "INSERT INTO typed VALUES (?, ?, ?)", [("001", 1, None), ("1", 2, "")]
        )
    connection.close()
    data = adapter_for(str(database)).read(str(database), ReadOptions(table="typed"))
    assert data.rows == (("001", "1", None), ("1", "2", None))


def test_views_virtual_shadow_and_generated_columns_are_not_executed(database):
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE VIEW danger AS SELECT load_extension('not-a-library')")
        connection.execute("CREATE VIRTUAL TABLE search USING fts5(text)")
        connection.execute("CREATE TABLE generated (id TEXT, derived TEXT AS (upper(id)))")
    connection.close()
    reader = adapter_for(str(database))
    assert reader.discover(str(database)) == ["Customer lookup", "empty_table", "generated"]
    for table in ("danger", "search", "search_data"):
        with pytest.raises(AtlasWeaveError, match="Unknown or unsupported"):
            reader.read(str(database), ReadOptions(table=table))
    with pytest.raises(AtlasWeaveError, match="generated/hidden"):
        reader.read(str(database), ReadOptions(table="generated"))


def test_blob_cells_fail_instead_of_becoming_string_keys(database):
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE blobs (id BLOB)")
        connection.execute("INSERT INTO blobs VALUES (?)", (b"001",))
    connection.close()
    with pytest.raises(AtlasWeaveError, match="BLOB"):
        adapter_for(str(database)).read(str(database), ReadOptions(table="blobs"))


@pytest.mark.parametrize(
    "statement", ["DELETE FROM empty_table", "ATTACH ':memory:' AS other", "SELECT random()"]
)
def test_snapshot_connection_denies_writes_attachments_and_functions(database, statement):
    with pytest.raises(AtlasWeaveError, match="Could not read SQLite"):
        with sqlite_snapshot(str(database)) as connection:
            connection.execute(statement)


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sidecars_are_rejected(database, suffix):
    database.with_name(database.name + suffix).write_bytes(b"sidecar")
    with pytest.raises(AtlasWeaveError, match="standalone"):
        adapter_for(str(database)).discover(str(database))


def test_wal_database_rejected_even_after_closing(database):
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
    connection.close()
    with pytest.raises(AtlasWeaveError, match="standalone"):
        adapter_for(str(database)).discover(str(database))


def test_invalid_database_and_empty_catalog(tmp_path):
    path = tmp_path / "broken.db"
    path.write_bytes(b"not a SQLite file")
    with pytest.raises(AtlasWeaveError, match="Invalid SQLite"):
        adapter_for(str(path)).discover(str(path))
    path.unlink()
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE x (id)")
        connection.execute("DROP TABLE x")
    connection.close()
    with pytest.raises(AtlasWeaveError, match="no supported"):
        adapter_for(str(path)).discover(str(path))


@pytest.mark.parametrize(
    "options",
    [
        ReadOptions(sheet="x", table="empty_table"),
        ReadOptions(header_row=2, table="empty_table"),
        ReadOptions(delimiter=";", table="empty_table"),
    ],
)
def test_file_parser_settings_do_not_apply_to_sqlite(database, options):
    with pytest.raises(AtlasWeaveError, match="do not apply"):
        adapter_for(str(database)).read(str(database), options)


def test_table_option_rejected_for_csv_and_xlsx(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text("id\n001\n")
    for path in (csv, tmp_path / "x.xlsx"):
        with pytest.raises(AtlasWeaveError, match="only to SQLite"):
            adapter_for(str(path)).read(str(path), ReadOptions(table="x"))


def test_mixed_workflow_sample_freshness_and_export(database, tmp_path):
    csv = tmp_path / "orders.csv"
    csv.write_text('cust_id\n001\n001\n002\n999\n""\n')
    rules = {"join": "left", "require_unique_right": True, "require_non_null_right": True}
    project = discover(csv, database, tmp_path, right_options=ReadOptions(table="Customer lookup"))
    candidate = project["candidates"][0]
    assert candidate["evidence"]["left_join_rows"] == 5
    assert candidate["evidence"]["inner_join_rows"] == 3
    assert candidate["evidence"]["left_nulls"] == 1
    decide(project, candidate["id"], "approved", rules)
    verify_project(project, tmp_path)
    mapping = export_mapping(project)
    assert mapping["sources"]["right"]["format"] == "sqlite"
    assert mapping["sources"]["right"]["options"]["table"] == "Customer lookup"
    assert "Ada" not in json.dumps(mapping)
    assert str(tmp_path) not in agent_brief(mapping)
    invalid = deepcopy(mapping)
    del invalid["sources"]["right"]["options"]["table"]
    with pytest.raises(AtlasWeaveError, match="Invalid mapping"):
        validate_document(invalid, "mapping-v1.json")
    sampled = discover(
        csv, database, tmp_path, right_options=ReadOptions(table="Customer lookup", max_rows=1)
    )
    with pytest.raises(AtlasWeaveError, match="Sampled"):
        decide(sampled, sampled["candidates"][0]["id"], "approved", rules)
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO \"Customer lookup\" VALUES ('004', 'New')")
    connection.close()
    with pytest.raises(AtlasWeaveError, match="source changed"):
        verify_project(project, tmp_path)


def test_cli_sqlite_tables_and_discovery(database, tmp_path, capsys):
    csv = tmp_path / "orders.csv"
    csv.write_text("cust_id\n001\n002\n")
    assert main(["tables", str(database)]) == 0
    assert "Customer lookup" in capsys.readouterr().out
    output = tmp_path / "project.json"
    assert (
        main(
            [
                "discover",
                str(csv),
                str(database),
                "--right-table",
                "Customer lookup",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    project = json.loads(output.read_text())
    assert (
        project["sources"]["right"]["sha256"] == hashlib.sha256(database.read_bytes()).hexdigest()
    )
    assert main(["review", str(output), "left.f1--right.f1", "--status", "approved"]) == 0
    assert main(["export", str(output), "--out-dir", str(tmp_path / "export")]) == 0


def test_two_tables_in_one_database_do_not_coerce_identifiers(database, tmp_path):
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE orders ("Customer ID" TEXT)')
        connection.executemany("INSERT INTO orders VALUES (?)", [("1",), (None,)])
    connection.close()
    project = discover(
        database,
        database,
        tmp_path,
        ReadOptions(table="orders"),
        ReadOptions(table="Customer lookup", max_rows=3),
        manual_pairs=[{"left_field": "f1", "right_field": "f1"}],
    )
    candidate = project["candidates"][0]
    assert candidate["scope"] == "full"  # Exactly the row limit is still complete.
    assert candidate["evidence"]["shared_distinct"] == 0  # "1" is not "001".
    assert candidate["evidence"]["left_nulls"] == 1
    with pytest.raises(AtlasWeaveError, match="No shared"):
        decide(
            project,
            candidate["id"],
            "approved",
            {
                "join": "left",
                "require_unique_right": True,
                "require_non_null_right": True,
            },
        )
