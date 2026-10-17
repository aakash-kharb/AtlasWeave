"""Generate the two self-contained, packaged JSON Schema contracts."""

import json
from pathlib import Path


def obj(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def array(items):
    return {"type": "array", "items": items}


def enum(*values):
    return {"enum": list(values)}


def ref(name):
    return {"$ref": f"#/$defs/{name}"}


text = {"type": "string"}
boolean = {"type": "boolean"}
count = {"type": "integer", "minimum": 0}
score = {"type": "number", "minimum": 0, "maximum": 1}
sha = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
strategies = ("name", "type", "overlap", "uniqueness")
definitions = {
    "options": obj(
        {
            "sheet": {"type": ["string", "null"]},
            "delimiter": {"type": "string", "minLength": 1, "maxLength": 1},
            "header_row": {"type": "integer", "minimum": 1, "maximum": 10000},
            "max_rows": {"type": "integer", "minimum": 1, "maximum": 100000},
        }
    ),
    "field": obj(
        {
            "id": {"type": "string", "pattern": "^f[1-9][0-9]*$"},
            "name": text,
            "kind": enum("number", "boolean", "text", "mixed", "empty"),
            **{k: count for k in ("row_count", "null_count", "distinct_count", "duplicate_count")},
        }
    ),
    "rules": obj(
        {
            "join": enum("left", "inner"),
            "require_unique_right": boolean,
            "require_non_null_right": boolean,
        }
    ),
    "evidence": obj(
        {
            **{
                k: count
                for k in (
                    "shared_distinct",
                    "unmatched_left_rows",
                    "unmatched_right_rows",
                    "inner_join_rows",
                    "left_join_rows",
                    "left_nulls",
                    "right_nulls",
                    "left_duplicates",
                    "right_duplicates",
                )
            },
            "cardinality": enum(
                "one-to-one", "one-to-many", "many-to-one", "many-to-many", "no-overlap"
            ),
        }
    ),
    "config": obj(
        {
            "aliases": {"type": "object", "additionalProperties": text},
            "weights": obj({k: {"type": "number", "minimum": 0} for k in strategies}),
            "trim": boolean,
            "casefold": boolean,
            "min_score": score,
        }
    ),
}
definitions["candidate"] = obj(
    {
        "id": text,
        "left_field": text,
        "right_field": text,
        "score": score,
        "scores": obj({key: score for key in strategies}),
        "evidence": ref("evidence"),
        "scope": enum("full", "sample"),
        "status": enum("pending", "approved", "rejected"),
        "rules": {"anyOf": [ref("rules"), {"type": "null"}]},
    }
)
source = {
    "name": text,
    "sha256": sha,
    "storage": enum("file"),
    "format": enum("csv", "xlsx"),
    "shape": enum("table"),
    "options": ref("options"),
    "row_count": count,
    "warnings": array(text),
}
definitions["source"] = obj({**source, "path": text, "complete": boolean})
definitions["export_source"] = obj({**source, "fields": array(ref("field"))})
definitions["approved"] = {
    "allOf": [
        ref("candidate"),
        {
            "properties": {
                "status": {"const": "approved"},
                "scope": {"const": "full"},
                "rules": ref("rules"),
            }
        },
    ],
}
common = {"schema_version": {"const": 1}, "engine_version": text}
schemas = {
    "project-v1": obj(
        {
            **common,
            "config": ref("config"),
            "discovery_fingerprint": sha,
            "sources": obj({side: ref("source") for side in ("left", "right")}),
            "profiles": obj({side: array(ref("field")) for side in ("left", "right")}),
            "candidates": array(ref("candidate")),
        }
    ),
    "mapping-v1": obj(
        {
            **common,
            "sources": obj({side: ref("export_source") for side in ("left", "right")}),
            "normalization": obj(
                {
                    "trim": boolean,
                    "casefold": boolean,
                    "preserve_leading_zeros": {"const": True},
                    "nulls_match": {"const": False},
                }
            ),
            "mappings": {**array(ref("approved")), "minItems": 1},
            "unresolved_candidates": array(text),
        }
    ),
}
schemas["project-v1"]["properties"]["manual_pairs"] = {
    **array(obj({"left_field": text, "right_field": text})),
    "uniqueItems": True,
    "maxItems": 10000,
}

if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "src/atlasweave/schemas"
    target.mkdir(exist_ok=True)
    for name, schema in schemas.items():
        schema.update(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": f"https://github.com/aakash-kharb/AtlasWeave/schemas/{name}",
                "$defs": definitions,
            }
        )
        (target / f"{name}.json").write_text(json.dumps(schema, indent=2) + "\n")
