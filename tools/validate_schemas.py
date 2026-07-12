#!/usr/bin/env python3
"""Validate repository JSON artifacts against schemas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlparse


try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:  # pragma: no cover - import guard behavior
    print("ERROR: Missing dependency 'jsonschema'. Install with: pip install jsonschema")
    raise SystemExit(2) from exc


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _is_absolute_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


def _collect_local_json_paths(index: dict, repo_root: Path) -> list[Path]:
    found: set[Path] = set()
    for election in index.get("elections", []):
        candidates = []
        for key in ["dataUrl", "areasUrl", "metadataUrl"]:
            url = election.get(key)
            if url:
                candidates.append(url)

        for snapshot in election.get("snapshots", []):
            for key in ["dataUrl", "areasUrl", "gisUrl", "metadataUrl"]:
                url = snapshot.get(key)
                if url:
                    candidates.append(url)

            for layer in snapshot.get("layers", []):
                for key in ["dataUrl", "gisUrl", "metadataUrl"]:
                    url = layer.get(key)
                    if url:
                        candidates.append(url)

        for raw_path in candidates:
            if not isinstance(raw_path, str):
                continue
            if _is_absolute_url(raw_path):
                continue
            if not raw_path.endswith(".json"):
                continue
            found.add(repo_root / raw_path)

    return sorted(found)


def _schema_for_json_path(path: Path, schemas: dict[str, dict]) -> tuple[str, dict] | tuple[None, None]:
    name = path.name
    if name == "elections.index.json":
        return "elections.index.schema.json", schemas["elections.index.schema.json"]
    if name == "metadata.json":
        return "metadata.schema.json", schemas["metadata.schema.json"]
    if name.endswith(".gis.json"):
        return "precincts.gis.schema.json", schemas["precincts.gis.schema.json"]
    if name.endswith(".json"):
        return "election.schema.json", schemas["election.schema.json"]
    return None, None


def _validate_file(path: Path, schema_name: str, schema: dict) -> list[str]:
    if not path.exists():
        return [f"ERROR: File does not exist for schema validation: {path}"]

    try:
        payload = _load_json(path)
    except json.JSONDecodeError as exc:
        return [f"ERROR: Invalid JSON in {path}: {exc}"]

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda err: (list(err.path), err.message))

    rendered: list[str] = []
    for err in errors:
        location = "/".join(str(part) for part in err.path) or "<root>"
        rendered.append(f"ERROR: {path} against {schema_name} at {location}: {err.message}")
    return rendered


def validate_schemas(repo_root: Path | None = None, index_file: str = "elections.index.json") -> bool:
    if repo_root is None:
        repo_root = Path(__file__).parent.parent

    schema_dir = repo_root / "schemas"
    index_path = repo_root / index_file

    schema_files = [
        "elections.index.schema.json",
        "election.schema.json",
        "precincts.gis.schema.json",
        "metadata.schema.json",
    ]
    schemas = {name: _load_json(schema_dir / name) for name in schema_files}

    all_errors: list[str] = []

    if not index_path.exists():
        print(f"ERROR: Index file not found: {index_path}")
        return False

    all_errors.extend(_validate_file(index_path, "elections.index.schema.json", schemas["elections.index.schema.json"]))

    try:
        index_payload = _load_json(index_path)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in {index_path}: {exc}")
        return False

    referenced = _collect_local_json_paths(index_payload, repo_root)

    for file_path in referenced:
        schema_name, schema = _schema_for_json_path(file_path, schemas)
        if schema_name is None or schema is None:
            continue
        all_errors.extend(_validate_file(file_path, schema_name, schema))

    if all_errors:
        for line in all_errors:
            print(line)
        print(f"\nSchema validation failed with {len(all_errors)} error(s)")
        return False

    print(f"Schema validation passed for {1 + len(referenced)} file(s)")
    return True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate index and referenced JSON files against repository schemas.")
    parser.add_argument("--index", default="elections.index.json", help="Index file path relative to repo root.")
    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()
    ok = validate_schemas(index_file=args.index)
    sys.exit(0 if ok else 1)