"""Create a small standalone SQLite snapshot from the packaged synthetic demo."""

import argparse
import csv
import sqlite3
from importlib.resources import files
from io import StringIO
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("local-data/demo.sqlite"))
    args = parser.parse_args()
    connection = sqlite3.connect(":memory:")
    try:
        for table in ("orders", "customers"):
            rows = csv.reader(
                StringIO(files("atlasweave").joinpath("web", f"{table}.csv").read_text())
            )
            names = next(rows)
            columns = ", ".join('"' + name.replace('"', '""') + '" TEXT' for name in names)
            connection.execute(f'CREATE TABLE "{table}" ({columns})')
            placeholders = ", ".join("?" for _ in names)
            connection.executemany(
                f'INSERT INTO "{table}" VALUES ({placeholders})',
                [tuple(value if value else None for value in row) for row in rows],
            )
        connection.commit()
        content = connection.serialize()
    finally:
        connection.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("xb") as stream:
        stream.write(content)
    print(f"Created synthetic SQLite snapshot: {args.out}")


if __name__ == "__main__":
    main()
