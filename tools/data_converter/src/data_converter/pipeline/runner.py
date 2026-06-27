from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any

from data_converter.defaults import PROJECT_ROOT
from data_converter.parser.config_loader import load_config
from data_converter.parser.main import (
    parse_dataframe_with_config,
    parse_file as parse_csv_file,
    parse_rows_with_config,
)
from data_converter.split import split_xlsx_to_csv, split_xlsx_to_dataframes, split_xlsx_to_row_matrices
from data_converter.transform.builder import build_election_data, build_metadata_payload
from data_converter.transform.io import update_elections_index, write_json_file

from .config import RuntimeOptions, build_runtime_options, load_pipeline_config
from .download import download_xlsx
from .outputs import build_manifest, write_combined_output, write_manifest_file, write_per_sheet_outputs
from .routing import pick_parser_config, resolve_config_refs


LOGGER = logging.getLogger(__name__)


def run_pipeline(
    pipeline_config_path: str,
    *,
    xlsx_path: str | None = None,
    url: str | None = None,
    output_dir_override: str | None = None,
    summary_only_override: bool | None = None,
    write_sheet_json_override: bool | None = None,
    write_combined_json_override: bool | None = None,
    write_manifest_override: bool | None = None,
    combined_name_override: str | None = None,
    transform_override: bool | None = None,
    transform_output_path_override: str | None = None,
    transform_metadata_path_override: str | None = None,
    transform_update_index_override: bool | None = None,
    in_memory_tables_override: bool | None = None,
    table_representation_override: str | None = None,
    keep_split_csv_override: bool | None = None,
    delete_split_csv_override: bool | None = None,
    output_versioning_override: bool | None = None,
    output_version_template_override: str | None = None,
    omit_nulls_override: bool | None = None,
    timeout_override: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    cfg = load_pipeline_config(pipeline_config_path)
    opts = build_runtime_options(
        cfg,
        xlsx_path=xlsx_path,
        url=url,
        output_dir_override=output_dir_override,
        summary_only_override=summary_only_override,
        write_sheet_json_override=write_sheet_json_override,
        write_combined_json_override=write_combined_json_override,
        write_manifest_override=write_manifest_override,
        combined_name_override=combined_name_override,
        transform_override=transform_override,
        transform_output_path_override=transform_output_path_override,
        transform_metadata_path_override=transform_metadata_path_override,
        transform_update_index_override=transform_update_index_override,
        in_memory_tables_override=in_memory_tables_override,
        table_representation_override=table_representation_override,
        keep_split_csv_override=keep_split_csv_override,
        delete_split_csv_override=delete_split_csv_override,
        output_versioning_override=output_versioning_override,
        output_version_template_override=output_version_template_override,
        omit_nulls_override=omit_nulls_override,
        timeout_override=timeout_override,
    )

    run_started = datetime.now(timezone.utc)
    total_started = perf_counter()

    def log_timing(stage: str, started_at: float, **fields: Any) -> None:
        if not verbose:
            return
        elapsed = perf_counter() - started_at
        if fields:
            field_text = " ".join(f"{k}={v}" for k, v in fields.items())
            LOGGER.debug("pipeline timing stage=%s elapsed=%.3fs %s", stage, elapsed, field_text)
        else:
            LOGGER.debug("pipeline timing stage=%s elapsed=%.3fs", stage, elapsed)

    with TemporaryDirectory(prefix="election_pipeline_") as temp_root:
        temp_root_path = Path(temp_root)
        split_dir = temp_root_path / "split_csv"
        split_dir.mkdir(parents=True, exist_ok=True)

        started = perf_counter()
        if opts.effective_url:
            xlsx_source = download_xlsx(opts.effective_url, temp_root_path, opts.timeout_seconds)
            source_kind = "url"
            source_value = opts.effective_url
        else:
            xlsx_source = Path(opts.effective_xlsx_path or "").resolve()
            source_kind = "path"
            source_value = str(xlsx_source)
        log_timing("source", started, source_kind=source_kind)

        output_version: str | None = None
        output_dir = opts.output_dir
        started = perf_counter()
        if opts.output_versioning_enabled:
            output_version = _render_output_version(
                opts.output_version_template,
                run_utc=run_started,
                source_kind=source_kind,
                source_value=source_value,
            )
            output_dir = output_dir / output_version
        output_dir.mkdir(parents=True, exist_ok=True)
        log_timing("output_dir", started, versioning=opts.output_versioning_enabled)

        parse_cfg = cfg.get("parse", {})
        config_refs = resolve_config_refs(parse_cfg.get("config_refs", {}), Path(pipeline_config_path).parent)
        started = perf_counter()
        if opts.in_memory_tables:
            loaded_configs = {key: load_config(path) for key, path in config_refs.items()}
            results = _parse_split_tables_in_memory(
                str(xlsx_source),
                loaded_configs,
                parse_cfg,
                opts.include_warnings,
                opts.table_representation,
            )
        else:
            split_xlsx_to_csv(
                str(xlsx_source),
                output_dir=str(split_dir),
                create_dirs=True,
            )
            results = _parse_split_csvs(split_dir, config_refs, parse_cfg, opts.include_warnings)
        log_timing(
            "split_parse",
            started,
            mode="memory" if opts.in_memory_tables else "disk",
            sheets=len(results),
            failed=sum(1 for row in results if not row.get("ok")),
        )

        started = perf_counter()
        if opts.delete_split_csv and split_dir.exists():
            shutil.rmtree(split_dir)
        log_timing("cleanup", started, delete_split_csv=opts.delete_split_csv)

        started = perf_counter()
        if not opts.summary_only and opts.write_sheet_json:
            write_per_sheet_outputs(
                results,
                output_dir,
                opts.indent,
                include_nulls=not opts.omit_nulls,
            )
        log_timing("write_sheet_json", started, enabled=bool(not opts.summary_only and opts.write_sheet_json))

        started = perf_counter()
        if not opts.summary_only and opts.write_combined_json:
            write_combined_output(
                results,
                output_dir,
                combined_name=opts.combined_name,
                indent=opts.indent,
                include_nulls=not opts.omit_nulls,
            )
        log_timing("write_combined_json", started, enabled=bool(not opts.summary_only and opts.write_combined_json))

        transform_output_path: Path | None = None
        transform_metadata_path: Path | None = None
        transform_index_updated = False

        started = perf_counter()
        if opts.transform_enabled:
            transform_output_path = _resolve_transform_output_path(opts, output_dir)
            transformed = build_election_data(
                results,
                precinct_result_scope=opts.transform_precinct_result_scope,
            )
            write_json_file(
                transform_output_path,
                transformed,
                indent=opts.indent,
                include_nulls=not opts.omit_nulls,
            )

            if opts.transform_write_metadata:
                transform_metadata_path = _resolve_transform_metadata_path(opts, transform_output_path)
                metadata_payload = build_metadata_payload(
                    source_kind=source_kind,
                    source_value=source_value,
                    election_id=opts.transform_election_id or "unknown-election",
                    run_started=run_started,
                )
                write_json_file(
                    transform_metadata_path,
                    metadata_payload,
                    indent=opts.indent,
                    include_nulls=not opts.omit_nulls,
                )

            if opts.transform_update_index:
                election_id = opts.transform_election_id
                if not election_id:
                    raise ValueError("transform.election_id is required when transform.update_index is true")

                index_path = opts.transform_index_path or (PROJECT_ROOT / "elections.index.json")
                data_url = _to_repo_relative_path(transform_output_path)
                precincts_url = opts.transform_precincts_url
                update_elections_index(
                    index_path=index_path,
                    election_id=election_id,
                    data_url=data_url,
                    precincts_url=precincts_url,
                    precinct_id_field=opts.transform_precinct_id_field,
                    precinct_label_field=opts.transform_precinct_label_field,
                    label=opts.transform_index_label,
                    date=opts.transform_index_date,
                    election_type=opts.transform_index_type,
                    county=opts.transform_index_county,
                    state=opts.transform_index_state,
                )
                transform_index_updated = True
        log_timing(
            "transform",
            started,
            enabled=opts.transform_enabled,
            updated_index=transform_index_updated,
        )

        started = perf_counter()
        manifest = build_manifest(
            source_kind=source_kind,
            source_value=source_value,
            started_at=run_started,
            finished_at=datetime.now(timezone.utc),
            output_dir=output_dir,
            base_output_dir=opts.output_dir,
            output_version=output_version,
            output_version_template=opts.output_version_template,
            output_versioning_enabled=opts.output_versioning_enabled,
            results=results,
            summary_only=opts.summary_only,
            write_sheet_json=opts.write_sheet_json,
            write_combined_json=opts.write_combined_json,
            write_manifest=opts.write_manifest,
            combined_name=opts.combined_name,
            in_memory_tables=opts.in_memory_tables,
            table_representation=opts.table_representation,
            keep_split_csv=opts.keep_split_csv,
            delete_split_csv=opts.delete_split_csv,
            omit_nulls=opts.omit_nulls,
            transform_enabled=opts.transform_enabled,
            transform_output_path=str(transform_output_path) if transform_output_path else None,
            transform_metadata_path=str(transform_metadata_path) if transform_metadata_path else None,
            transform_index_updated=transform_index_updated,
        )
        log_timing("build_manifest", started)

        started = perf_counter()
        if not opts.summary_only and opts.write_manifest:
            write_manifest_file(
                manifest,
                output_dir,
                manifest_name=opts.manifest_name,
                indent=opts.indent,
                include_nulls=not opts.omit_nulls,
            )
        log_timing("write_manifest", started, enabled=bool(not opts.summary_only and opts.write_manifest))

    if verbose:
        LOGGER.debug("pipeline timing stage=total elapsed=%.3fs", perf_counter() - total_started)

    return manifest


def _parse_split_csvs(
    split_dir: Path,
    config_refs: dict[str, Path],
    parse_cfg: dict[str, Any],
    include_warnings: bool,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    csv_files = sorted(split_dir.glob("*.csv"))
    for csv_file in csv_files:
        parser_config = pick_parser_config(csv_file, config_refs, parse_cfg)
        result_record: dict[str, Any] = {
            "sheet": csv_file.stem,
            "csv_file": str(csv_file),
            "parser_config": str(parser_config),
        }
        try:
            parsed = parse_csv_file(
                str(csv_file),
                str(parser_config),
                as_object=False,
                include_warnings=include_warnings,
            )
            result_record["ok"] = True
            result_record["data"] = parsed
        except Exception as exc:  # noqa: BLE001
            result_record["ok"] = False
            result_record["error"] = str(exc)
        results.append(result_record)
    return results


def _parse_split_tables_in_memory(
    xlsx_path: str,
    loaded_configs: dict[str, dict[str, Any]],
    parse_cfg: dict[str, Any],
    include_warnings: bool,
    table_representation: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    if table_representation == "dataframe":
        tables = split_xlsx_to_dataframes(xlsx_path)
    else:
        tables = split_xlsx_to_row_matrices(xlsx_path)

    for sheet_name, table in tables.items():
        parser_key = _pick_parser_key_for_sheet(sheet_name, parse_cfg, table)
        result_record: dict[str, Any] = {
            "sheet": sheet_name,
            "csv_file": None,
            "parser_config": parser_key,
        }

        if parser_key not in loaded_configs:
            result_record["ok"] = False
            result_record["error"] = f"Unknown parser config key: {parser_key}"
            results.append(result_record)
            continue

        try:
            if table_representation == "dataframe":
                parsed = parse_dataframe_with_config(
                    table,
                    loaded_configs[parser_key],
                    as_object=False,
                    include_warnings=include_warnings,
                )
            else:
                parsed = parse_rows_with_config(
                    table,
                    loaded_configs[parser_key],
                    as_object=False,
                    include_warnings=include_warnings,
                )
            result_record["ok"] = True
            result_record["data"] = parsed
        except Exception as exc:  # noqa: BLE001
            result_record["ok"] = False
            result_record["error"] = str(exc)
        results.append(result_record)

    return results


def _pick_parser_key_for_sheet(
    sheet_name: str,
    parse_cfg: dict[str, Any],
    table: Any,
) -> str:
    pseudo_name = f"{sheet_name}.csv"
    sheet_rules = parse_cfg.get("sheet_rules", [])
    for rule in sheet_rules:
        pattern = rule.get("pattern")
        config_ref = rule.get("config_ref")
        if not pattern or not config_ref:
            continue
        if re.search(pattern, pseudo_name):
            return str(config_ref)

    if parse_cfg.get("detect_turnout_header", True) and _looks_like_turnout_table(table):
        return "turnout"

    return str(parse_cfg.get("default_config_ref", "results"))


def _looks_like_turnout_table(table: Any) -> bool:
    if hasattr(table, "to_string"):
        text = table.to_string()
    else:
        text = "\n".join(
            ",".join(str(cell) for cell in row)
            for row in table
        )

    return (
        "Registered" in text
        and "Cards Cast" in text
        and "Voters Cast" in text
        and "% Turnout" in text
    )


def _render_output_version(
    template: str,
    *,
    run_utc: datetime,
    source_kind: str,
    source_value: str,
) -> str:
    source_name = Path(source_value).stem if source_kind == "path" else Path(source_value).name
    rendered = template.format(
        run_utc=run_utc,
        source_kind=source_kind,
        source_value=source_value,
        source_name=source_name,
    )
    rendered = rendered.strip()
    if not rendered:
        raise ValueError("Output version template resolved to an empty string")
    return re.sub(r'[<>:"/\\|?*\s]+', "_", rendered)


def _resolve_transform_output_path(opts: RuntimeOptions, output_dir: Path) -> Path:
    if opts.transform_output_path:
        return opts.transform_output_path
    if opts.transform_election_id:
        return PROJECT_ROOT / "elections" / opts.transform_election_id / "election.json"
    return output_dir / "election.json"


def _resolve_transform_metadata_path(opts: RuntimeOptions, transform_output_path: Path) -> Path:
    if opts.transform_metadata_path:
        return opts.transform_metadata_path
    return transform_output_path.with_name("metadata.json")


def _to_repo_relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")
