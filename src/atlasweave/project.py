"""Versioned projects, explicit review, and evidence freshness checks."""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator

from atlasweave import __version__
from atlasweave.adapters import adapter_for, check_file
from atlasweave.models import AtlasWeaveError, ReadOptions
from atlasweave.strategies import StrategyConfig, suggest


def read_json(path: Path):
    if path.stat().st_size > 16 * 1024 * 1024:
        raise AtlasWeaveError("JSON document exceeds 16 MiB.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise AtlasWeaveError("Invalid JSON document.") from exc


def validate_document(document, schema_name="project-v1.json"):
    schema = json.loads(files("atlasweave").joinpath("schemas", schema_name).read_text())
    errors = list(Draft202012Validator(schema).iter_errors(document))
    if errors:
        error = errors[0]
        location = ".".join(str(p) for p in error.absolute_path) or "document"
        # Avoid echoing sensitive values from a malformed document.
        raise AtlasWeaveError(f"Invalid {schema_name} at {location} ({error.validator}).")


def write_json(path: Path, value, *, replace=False):
    content = json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    write_text(path, content, replace=replace)


def write_text(path: Path, content: str, *, replace=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not replace:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(content)
        return
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def fingerprint(path: Path) -> str:
    check_file(str(path))
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_source(path: Path, options: ReadOptions, project_dir: Path):
    digest = fingerprint(path)
    adapter = adapter_for(str(path))
    dataset = adapter.read(str(path), options)
    if fingerprint(path) != digest:
        raise AtlasWeaveError("Source changed during reading; retry discovery.")
    metadata = {
        "path": os.path.relpath(path.resolve(), project_dir.resolve()),
        "name": path.name,
        "sha256": digest,
        "storage": adapter.storage,
        "format": adapter.format,
        "shape": adapter.shape,
        "options": asdict(options),
        "complete": dataset.complete,
        "row_count": len(dataset.rows),
        "warnings": list(dataset.warnings),
    }
    return metadata, dataset


def discover(
    left: Path,
    right: Path,
    project_dir: Path,
    left_options=None,
    right_options=None,
    config=None,
    manual_pairs=(),
):
    config = config or StrategyConfig()
    lm, ld = read_source(left, left_options or ReadOptions(), project_dir)
    rm, rd = read_source(right, right_options or ReadOptions(), project_dir)
    lp, rp, candidates = suggest(ld, rd, config, manual_pairs)
    document = {
        "schema_version": 1,
        "engine_version": __version__,
        "config": asdict(config),
        "sources": {"left": lm, "right": rm},
        "profiles": {"left": lp, "right": rp},
        "candidates": candidates,
    }
    if manual_pairs:
        for pair in manual_pairs:
            for side, profiles in (("left", lp), ("right", rp)):
                if pair[f"{side}_field"] not in {field["id"] for field in profiles}:
                    raise AtlasWeaveError("Unknown field in manual mapping.")
        document["manual_pairs"] = list(manual_pairs)
    document["discovery_fingerprint"] = discovery_fingerprint(document)
    validate_document(document)
    return document


def discovery_fingerprint(project):
    content = {key: value for key, value in project.items() if key != "discovery_fingerprint"}
    content["candidates"] = [
        {key: value for key, value in candidate.items() if key not in ("status", "rules")}
        for candidate in project["candidates"]
    ]
    encoded = json.dumps(content, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_project(path: Path):
    project = read_json(path)
    validate_project(project)
    return project


def validate_project(project):
    validate_document(project)
    StrategyConfig(**project["config"])
    if discovery_fingerprint(project) != project["discovery_fingerprint"]:
        raise AtlasWeaveError(
            "Discovery settings or evidence changed; rediscover and review again."
        )
    ids = [c["id"] for c in project["candidates"]]
    if len(ids) != len(set(ids)):
        raise AtlasWeaveError("Duplicate candidate identifiers.")
    for candidate in project["candidates"]:
        if (candidate["status"] == "approved") != (candidate["rules"] is not None):
            raise AtlasWeaveError("Only approved candidates may have join rules.")
    return project


def verify_project(project, project_dir: Path):
    if discovery_fingerprint(project) != project["discovery_fingerprint"]:
        raise AtlasWeaveError(
            "Discovery settings or evidence changed; rediscover and review again."
        )
    if project["engine_version"] != __version__:
        raise AtlasWeaveError("Engine version changed; rediscover and review the project.")
    sources = project["sources"]
    paths = {side: project_dir / source["path"] for side, source in sources.items()}
    for side, source in sources.items():
        if fingerprint(paths[side]) != source["sha256"]:
            raise AtlasWeaveError(f"The {side} source changed; rediscover and review again.")
    fresh = discover(
        paths["left"],
        paths["right"],
        project_dir,
        ReadOptions(**sources["left"]["options"]),
        ReadOptions(**sources["right"]["options"]),
        StrategyConfig(**project["config"]),
        project.get("manual_pairs", ()),
    )
    actual = [{**c, "status": "pending", "rules": None} for c in project["candidates"]]
    if (
        actual != fresh["candidates"]
        or project["profiles"] != fresh["profiles"]
        or project["sources"] != fresh["sources"]
    ):
        raise AtlasWeaveError("Evidence or settings changed; rediscover and review again.")


def add_manual_pair(project, project_dir: Path, left_field: str, right_field: str):
    """Add one inspected pair without relaxing approval rules or losing existing decisions."""
    verify_project(project, project_dir)
    pair = {"left_field": left_field, "right_field": right_field}
    pairs = list(project.get("manual_pairs", ()))
    if pair in pairs:
        return project
    pairs.append(pair)
    sources = project["sources"]
    fresh = discover(
        project_dir / sources["left"]["path"],
        project_dir / sources["right"]["path"],
        project_dir,
        ReadOptions(**sources["left"]["options"]),
        ReadOptions(**sources["right"]["options"]),
        StrategyConfig(**project["config"]),
        pairs,
    )
    old = {candidate["id"]: candidate for candidate in project["candidates"]}
    for candidate in fresh["candidates"]:
        previous = old.get(candidate["id"])
        if previous:
            candidate.update(status=previous["status"], rules=previous["rules"])
    return fresh


def validate_approval(candidate, rules):
    if candidate["scope"] != "full":
        raise AtlasWeaveError(
            "Sampled evidence cannot be approved. Rediscover with a larger limit."
        )
    evidence = candidate["evidence"]
    if not evidence["shared_distinct"]:
        raise AtlasWeaveError("No shared values; this candidate cannot be approved as a join.")
    if rules["require_unique_right"] and evidence["right_duplicates"]:
        raise AtlasWeaveError(
            "Right key contains duplicates. Review row expansion, then explicitly "
            "use --allow-duplicate-right if intended."
        )
    if rules["require_non_null_right"] and evidence["right_nulls"]:
        raise AtlasWeaveError(
            "Right key contains nulls. Clean the source or explicitly use --allow-null-right."
        )


def decide(project, candidate_id: str, status: str, rules=None):
    if status not in ("approved", "rejected", "pending"):
        raise AtlasWeaveError("Unknown review status.")
    candidate = next((c for c in project["candidates"] if c["id"] == candidate_id), None)
    if candidate is None:
        raise AtlasWeaveError("Unknown candidate ID; run inspect to list candidates.")
    if status == "approved":
        if rules is None:
            raise AtlasWeaveError("Approval requires explicit join rules.")
        validate_approval(candidate, rules)
    candidate.update(status=status, rules=rules if status == "approved" else None)
    validate_document(project)
