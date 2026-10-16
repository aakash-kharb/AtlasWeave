"""The initial non-visual import → review → export workflow."""

import argparse
import json
import sys
from pathlib import Path
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from defusedxml.common import DefusedXmlException

from atlasweave import __version__
from atlasweave.adapters import adapter_for
from atlasweave.exporters import agent_brief, export_mapping
from atlasweave.models import AtlasWeaveError, ReadOptions
from atlasweave.project import (
    decide,
    discover,
    load_project,
    read_json,
    verify_project,
    write_json,
    write_text,
)
from atlasweave.strategies import StrategyConfig


def parser():
    root = argparse.ArgumentParser(
        prog="atlasweave", description="Find the threads connecting your data."
    )
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    sheets = commands.add_parser("sheets", help="List available datasets/worksheets")
    sheets.add_argument("source", type=Path)
    find = commands.add_parser("discover", help="Profile two files and suggest joins")
    find.add_argument(
        "left", type=Path, help="Records to preserve for a left join, e.g. orders.csv"
    )
    find.add_argument("right", type=Path, help="Lookup table, e.g. customers.xlsx")
    find.add_argument("--out", type=Path, required=True, help="New local project JSON file")
    find.add_argument("--config", type=Path, help="Strategy configuration JSON")
    find.add_argument("--max-rows", type=int, default=10_000)
    for side in ("left", "right"):
        find.add_argument(f"--{side}-sheet")
        find.add_argument(f"--{side}-delimiter", default=",")
        find.add_argument(f"--{side}-header-row", type=int, default=1)
    inspect = commands.add_parser("inspect", help="Read evidence and search field names")
    inspect.add_argument("project", type=Path)
    inspect.add_argument("--search", default="", help="Filter by field name or candidate ID")
    inspect.add_argument("--json", action="store_true", help="Print the full saved project")
    review = commands.add_parser("review", help="Approve, reject, or reset a candidate")
    review.add_argument("project", type=Path)
    review.add_argument("candidate")
    review.add_argument("--status", required=True, choices=["approved", "rejected", "pending"])
    review.add_argument("--join", choices=["left", "inner"], default="left")
    review.add_argument("--allow-duplicate-right", action="store_true")
    review.add_argument("--allow-null-right", action="store_true")
    export = commands.add_parser("export", help="Revalidate and export approved decisions")
    export.add_argument("project", type=Path)
    export.add_argument("--out-dir", type=Path, required=True)
    return root


def show(project, query=""):
    print("Saved evidence; review/export re-read the sources to check freshness.")
    for side, source in project["sources"].items():
        scope = "full scan" if source["complete"] else "SAMPLE — approval blocked"
        print(f"{side}: {json.dumps(source['name'])}, {source['row_count']} rows, {scope}")
        for warning in source["warnings"]:
            print(f"  Note: {warning}")
    fields = {
        side: {p["id"]: p["name"] for p in profiles}
        for side, profiles in project["profiles"].items()
    }
    count = 0
    for candidate in project["candidates"]:
        a = fields["left"][candidate["left_field"]]
        b = fields["right"][candidate["right_field"]]
        if query.casefold() not in f"{a} {b} {candidate['id']}".casefold():
            continue
        count += 1
        evidence = candidate["evidence"]
        print(f"\n{candidate['id']}  [{candidate['status']}]  score={candidate['score']:.3f}")
        print(f"  {json.dumps(a)} → {json.dumps(b)} ({evidence['cardinality']})")
        print("  strategy scores: " + json.dumps(candidate["scores"]))
        print(
            f"  shared keys={evidence['shared_distinct']}; "
            f"unmatched left rows={evidence['unmatched_left_rows']}; "
            f"unmatched right rows={evidence['unmatched_right_rows']}"
        )
        print(
            f"  right duplicates={evidence['right_duplicates']}; "
            f"right nulls={evidence['right_nulls']}; "
            f"projected rows: inner={evidence['inner_join_rows']}, "
            f"left={evidence['left_join_rows']}"
        )
    if not count:
        print("No matching candidates. Check names, configuration, and selected columns.")


def run(args):
    if args.command == "sheets":
        print(json.dumps(adapter_for(str(args.source)).discover(str(args.source)), indent=2))
    elif args.command == "discover":
        raw = read_json(args.config) if args.config else {}
        if not isinstance(raw, dict) or set(raw) - {
            "aliases",
            "weights",
            "trim",
            "casefold",
            "min_score",
        }:
            raise AtlasWeaveError("Config must be an object with supported strategy settings.")
        config = StrategyConfig(**raw)
        options = {
            side: ReadOptions(
                sheet=getattr(args, f"{side}_sheet"),
                delimiter=getattr(args, f"{side}_delimiter"),
                header_row=getattr(args, f"{side}_header_row"),
                max_rows=args.max_rows,
            )
            for side in ("left", "right")
        }
        project = discover(
            args.left, args.right, args.out.parent, options["left"], options["right"], config
        )
        write_json(args.out, project)
        show(project)
        print(f"\nSaved project: {args.out}")
    else:
        project = load_project(args.project)
        if args.command == "inspect":
            if args.json:
                print(json.dumps(project, indent=2, ensure_ascii=True))
            else:
                show(project, args.search)
        elif args.command == "review":
            verify_project(project, args.project.parent)
            rules = {
                "join": args.join,
                "require_unique_right": not args.allow_duplicate_right,
                "require_non_null_right": not args.allow_null_right,
            }
            decide(project, args.candidate, args.status, rules)
            write_json(args.project, project, replace=True)
            print(f"{args.candidate}: {args.status}")
        elif args.command == "export":
            verify_project(project, args.project.parent)
            mapping = export_mapping(project)
            mapping_path, brief_path = (
                args.out_dir / "mapping.json",
                args.out_dir / "agent-brief.md",
            )
            if mapping_path.exists() or brief_path.exists():
                raise AtlasWeaveError("Export files already exist; choose a new output directory.")
            write_json(mapping_path, mapping)
            try:
                write_text(brief_path, agent_brief(mapping))
            except OSError:
                mapping_path.unlink()
                raise
            print(f"Exported {len(mapping['mappings'])} approved mapping(s) to {args.out_dir}")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        run(args)
    except (AtlasWeaveError, OSError, BadZipFile, DefusedXmlException, ParseError) as exc:
        print(f"atlasweave: {exc}", file=sys.stderr)
        return 2
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        print(
            f"atlasweave: malformed file or unsupported content ({type(exc).__name__}).",
            file=sys.stderr,
        )
        return 2
    return 0
