from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from data_converter.parser.models import to_json_string


def write_per_sheet_outputs(
    results: list[dict[str, Any]],
    output_dir: Path,
    indent: int,
    include_nulls: bool,
) -> None:
    for result in results:
        sheet_name = result["sheet"]
        out_path = output_dir / f"{sheet_name}.json"
        if result["ok"]:
            payload: Any = result["data"]
        else:
            payload = {
                "sheet": sheet_name,
                "ok": False,
                "error": result["error"],
            }
        out_path.write_text(
            to_json_string(payload, indent=indent, include_nulls=include_nulls),
            encoding="utf-8",
        )


def write_combined_output(
    results: list[dict[str, Any]],
    output_dir: Path,
    combined_name: str,
    indent: int,
    include_nulls: bool,
) -> None:
    combined_payload = {
        "sheets": {
            item["sheet"]: (
                item["data"]
                if item["ok"]
                else {
                    "ok": False,
                    "error": item.get("error"),
                    "parser_config": item.get("parser_config"),
                }
            )
            for item in results
        }
    }
    out_path = output_dir / combined_name
    out_path.write_text(
        to_json_string(combined_payload, indent=indent, include_nulls=include_nulls),
        encoding="utf-8",
    )


def build_manifest(
    *,
    source_kind: str,
    source_value: str,
    started_at: datetime,
    finished_at: datetime,
    output_dir: Path,
    base_output_dir: Path,
    output_version: str | None,
    output_version_template: str,
    output_versioning_enabled: bool,
    results: list[dict[str, Any]],
    summary_only: bool,
    write_sheet_json: bool,
    write_combined_json: bool,
    write_manifest: bool,
    combined_name: str,
    in_memory_tables: bool,
    table_representation: str,
    keep_split_csv: bool,
    delete_split_csv: bool,
    omit_nulls: bool,
    transform_enabled: bool,
    transform_output_path: str | None,
    transform_metadata_path: str | None,
    transform_index_updated: bool,
) -> dict[str, Any]:
    succeeded = sum(1 for item in results if item["ok"])
    failed = len(results) - succeeded
    return {
        "source": {
            "kind": source_kind,
            "value": source_value,
        },
        "run": {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        },
        "settings": {
            "summary_only": summary_only,
            "write_sheet_json": write_sheet_json,
            "write_combined_json": write_combined_json,
            "write_manifest": write_manifest,
            "combined_name": combined_name,
            "in_memory_tables": in_memory_tables,
            "table_representation": table_representation,
            "keep_split_csv": keep_split_csv,
            "delete_split_csv": delete_split_csv,
            "omit_nulls": omit_nulls,
            "output_versioning_enabled": output_versioning_enabled,
            "output_version_template": output_version_template,
            "output_version": output_version,
            "transform_enabled": transform_enabled,
            "transform_output_path": transform_output_path,
            "transform_metadata_path": transform_metadata_path,
            "transform_index_updated": transform_index_updated,
        },
        "base_output_dir": str(base_output_dir),
        "output_dir": str(output_dir),
        "counts": {
            "total_sheets": len(results),
            "succeeded": succeeded,
            "failed": failed,
        },
        "sheets": [
            {
                "sheet": item["sheet"],
                "ok": item["ok"],
                "parser_config": item["parser_config"],
                "error": item.get("error"),
            }
            for item in results
        ],
    }


def write_manifest_file(
    manifest: dict[str, Any],
    output_dir: Path,
    manifest_name: str,
    indent: int,
    include_nulls: bool,
) -> None:
    manifest_path = output_dir / manifest_name
    manifest_path.write_text(
        to_json_string(manifest, indent=indent, include_nulls=include_nulls),
        encoding="utf-8",
    )
