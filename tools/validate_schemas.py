#!/usr/bin/env python3
"""Validate repository JSON artifacts against schemas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
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
        for key in ["metadataUrl"]:
            url = election.get(key)
            if url:
                candidates.append(url)

        for snapshot in election.get("snapshots", []):
            for key in ["metadataUrl"]:
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
    if name == "metadata.json" or name.startswith("metadata."):
        return "metadata.schema.json", schemas["metadata.schema.json"]
    if name.endswith(".gis.json"):
        return "gis.schema.json", schemas["gis.schema.json"]
    if name.endswith(".json"):
        return "election.schema.json", schemas["election.schema.json"]
    return None, None


def _vlog(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[validate_schemas] {message}")


def _validate_file(
    path: Path,
    schema_name: str,
    schema: dict,
    *,
    max_errors_per_file: int | None,
) -> list[str]:
    if not path.exists():
        return [f"ERROR: File does not exist for schema validation: {path}"]

    try:
        payload = _load_json(path)
    except json.JSONDecodeError as exc:
        return [f"ERROR: Invalid JSON in {path}: {exc}"]

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    rendered: list[str] = []
    for err in validator.iter_errors(payload):
        location = "/".join(str(part) for part in err.path) or "<root>"
        rendered.append(f"ERROR: {path} against {schema_name} at {location}: {err.message}")

        if max_errors_per_file is not None and len(rendered) >= max_errors_per_file:
            rendered.append(
                f"ERROR: {path} reached max_errors_per_file={max_errors_per_file}; additional errors omitted"
            )
            break
    return rendered


def validate_schemas(
    repo_root: Path | None = None,
    index_file: str = "elections.index.json",
    max_errors_per_file: int | None = 200,
    max_total_errors: int | None = 2000,
    verbose: bool = False,
    files: list[str] | None = None,
) -> bool:
    started = time.perf_counter()
    if repo_root is None:
        repo_root = Path(__file__).parent.parent

    schema_dir = repo_root / "schemas"
    index_path = repo_root / index_file

    _vlog(verbose, f"repo_root={repo_root}")
    _vlog(verbose, f"index_path={index_path}")

    schema_files = [
        "elections.index.schema.json",
        "election.schema.json",
        "gis.schema.json",
        "metadata.schema.json",
    ]
    _vlog(verbose, "loading schemas")
    schemas = {name: _load_json(schema_dir / name) for name in schema_files}
    _vlog(verbose, f"loaded {len(schemas)} schema files")

    all_errors: list[str] = []

    if not index_path.exists():
        print(f"ERROR: Index file not found: {index_path}")
        return False

    selected_paths: list[Path] = []
    include_index_in_count = 0

    if files:
        for raw in files:
            path = Path(raw)
            if not path.is_absolute():
                path = repo_root / path
            selected_paths.append(path)
        _vlog(verbose, f"selected_files={len(selected_paths)}")
    else:
        _vlog(verbose, "validating index schema")
        all_errors.extend(
            _validate_file(
                index_path,
                "elections.index.schema.json",
                schemas["elections.index.schema.json"],
                max_errors_per_file=max_errors_per_file,
            )
        )
        include_index_in_count = 1

        try:
            index_payload = _load_json(index_path)
        except json.JSONDecodeError as exc:
            print(f"ERROR: Invalid JSON in {index_path}: {exc}")
            return False

        selected_paths = _collect_local_json_paths(index_payload, repo_root)
        _vlog(verbose, f"referenced_json_files={len(selected_paths)}")

    for idx, file_path in enumerate(selected_paths, start=1):
        schema_name, schema = _schema_for_json_path(file_path, schemas)
        if schema_name is None or schema is None:
            _vlog(verbose, f"[{idx}/{len(selected_paths)}] skipped {file_path}")
            continue
        size = file_path.stat().st_size if file_path.exists() else 0
        _vlog(verbose, f"[{idx}/{len(selected_paths)}] validating schema={schema_name} bytes={size} path={file_path}")
        all_errors.extend(
            _validate_file(
                file_path,
                schema_name,
                schema,
                max_errors_per_file=max_errors_per_file,
            )
        )
        if max_total_errors is not None and len(all_errors) >= max_total_errors:
            all_errors.append(
                f"ERROR: Reached max_total_errors={max_total_errors}; stopping validation early"
            )
            _vlog(verbose, "stopping early due to max_total_errors")
            break

    if all_errors:
        _vlog(verbose, f"failed with errors={len(all_errors)} elapsed_s={time.perf_counter() - started:.2f}")
        for line in all_errors:
            print(line)
        print(f"\nSchema validation failed with {len(all_errors)} error(s)")
        return False

    _vlog(verbose, f"success elapsed_s={time.perf_counter() - started:.2f}")
    print(f"Schema validation passed for {include_index_in_count + len(selected_paths)} file(s)")
    return True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate index and referenced JSON files against repository schemas.")
    parser.add_argument("--index", default="elections.index.json", help="Index file path relative to repo root.")
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        help="Specific file to validate (repeatable). Paths are relative to repo root unless absolute.",
    )
    parser.add_argument(
        "--max-errors-per-file",
        type=int,
        default=200,
        help="Maximum errors to collect per file before truncation (0 = unlimited).",
    )
    parser.add_argument(
        "--max-total-errors",
        type=int,
        default=2000,
        help="Maximum total errors to collect before stopping validation (0 = unlimited).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose progress logging.",
    )
    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()
    per_file = None if args.max_errors_per_file == 0 else args.max_errors_per_file
    total = None if args.max_total_errors == 0 else args.max_total_errors
    ok = validate_schemas(
        index_file=args.index,
        max_errors_per_file=per_file,
        max_total_errors=total,
        verbose=args.verbose,
        files=args.file or None,
    )
    sys.exit(0 if ok else 1)