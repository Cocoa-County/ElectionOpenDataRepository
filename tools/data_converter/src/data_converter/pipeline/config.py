from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from data_converter.defaults import DEFAULT_OUTPUT_DIR


@dataclass
class RuntimeOptions:
    output_dir: Path
    output_versioning_enabled: bool
    output_version_template: str
    summary_only: bool
    write_sheet_json: bool
    write_combined_json: bool
    write_manifest: bool
    combined_name: str
    in_memory_tables: bool
    table_representation: str
    keep_split_csv: bool
    delete_split_csv: bool
    omit_nulls: bool
    indent: int
    include_warnings: bool
    manifest_name: str
    effective_url: str | None
    effective_xlsx_path: str | None
    timeout_seconds: int


def load_pipeline_config(path: str | Path) -> dict[str, Any]:
    cfg_path = Path(path)
    with cfg_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Pipeline config must be a mapping")
    validate_pipeline_config(config)
    return config


def validate_pipeline_config(config: dict[str, Any]) -> None:
    parse_cfg = config.get("parse", {})
    refs = parse_cfg.get("config_refs", {})
    if not isinstance(refs, dict) or not refs:
        raise ValueError("parse.config_refs is required and must be a mapping")
    for key in ("results", "turnout"):
        if key not in refs:
            raise ValueError(f"parse.config_refs.{key} is required")


def build_runtime_options(
    cfg: dict[str, Any],
    *,
    xlsx_path: str | None = None,
    url: str | None = None,
    output_dir_override: str | None = None,
    summary_only_override: bool | None = None,
    write_sheet_json_override: bool | None = None,
    write_combined_json_override: bool | None = None,
    write_manifest_override: bool | None = None,
    combined_name_override: str | None = None,
    in_memory_tables_override: bool | None = None,
    table_representation_override: str | None = None,
    keep_split_csv_override: bool | None = None,
    delete_split_csv_override: bool | None = None,
    output_versioning_override: bool | None = None,
    output_version_template_override: str | None = None,
    omit_nulls_override: bool | None = None,
    timeout_override: int | None = None,
) -> RuntimeOptions:
    io_cfg = cfg.get("io", {})
    versioning_cfg = io_cfg.get("versioning", {})
    tables_cfg = io_cfg.get("tables", {})
    include_warnings = bool(cfg.get("warnings", {}).get("include", True))
    json_cfg = cfg.get("json", {})
    input_cfg = cfg.get("input", {})

    summary_only = _pick_bool(summary_only_override, io_cfg.get("summary_only", False))
    write_sheet_json = _pick_bool(write_sheet_json_override, io_cfg.get("write_sheet_json", True))
    write_combined_json = _pick_bool(write_combined_json_override, io_cfg.get("write_combined_json", False))
    write_manifest = _pick_bool(write_manifest_override, io_cfg.get("write_manifest", True))
    in_memory_tables = _pick_bool(in_memory_tables_override, tables_cfg.get("in_memory", True))
    keep_split_csv = _pick_bool(keep_split_csv_override, io_cfg.get("keep_split_csv", False))
    delete_split_csv = _pick_bool(delete_split_csv_override, io_cfg.get("delete_split_csv", True))

    if keep_split_csv and delete_split_csv:
        raise ValueError("Conflicting cleanup options: both keep_split_csv and delete_split_csv are true")

    effective_url = url or input_cfg.get("url")
    effective_xlsx_path = xlsx_path or input_cfg.get("xlsx_path")
    if bool(effective_url) == bool(effective_xlsx_path):
        raise ValueError("Provide exactly one XLSX input source: URL or local path")

    output_dir = Path(output_dir_override or io_cfg.get("output_dir", str(DEFAULT_OUTPUT_DIR)))
    if not output_dir.is_absolute():
        output_dir = DEFAULT_OUTPUT_DIR.parent / output_dir
    timeout_seconds = int(timeout_override or input_cfg.get("timeout_seconds", 120))
    table_representation = str(table_representation_override or tables_cfg.get("representation", "rows")).lower()
    if table_representation not in {"rows", "dataframe"}:
        raise ValueError("io.tables.representation must be one of: rows, dataframe")
    output_versioning_enabled = _pick_bool(
        output_versioning_override,
        versioning_cfg.get("enabled", False),
    )
    output_version_template = str(
        output_version_template_override
        or versioning_cfg.get("template", "{run_utc:%Y%m%dT%H%M%SZ}")
    )

    return RuntimeOptions(
        output_dir=output_dir,
        output_versioning_enabled=output_versioning_enabled,
        output_version_template=output_version_template,
        summary_only=summary_only,
        write_sheet_json=write_sheet_json,
        write_combined_json=write_combined_json,
        write_manifest=write_manifest,
        combined_name=str(combined_name_override or io_cfg.get("combined_name", "combined.json")),
        in_memory_tables=in_memory_tables,
        table_representation=table_representation,
        keep_split_csv=keep_split_csv,
        delete_split_csv=delete_split_csv,
        omit_nulls=_pick_bool(omit_nulls_override, json_cfg.get("omit_nulls", False)),
        indent=int(json_cfg.get("indent", 2)),
        include_warnings=include_warnings,
        manifest_name=str(io_cfg.get("manifest_name", "manifest.json")),
        effective_url=effective_url,
        effective_xlsx_path=effective_xlsx_path,
        timeout_seconds=timeout_seconds,
    )


def _pick_bool(cli_value: bool | None, config_value: Any) -> bool:
    if cli_value is None:
        return bool(config_value)
    return cli_value
