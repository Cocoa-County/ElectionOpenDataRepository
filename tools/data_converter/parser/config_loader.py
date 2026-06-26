from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml


REQUIRED_ROOT_KEYS = ["document", "normalization", "header", "values"]
ALLOWED_DOCUMENT_TYPES = {"election_results", "turnout_summary"}


def load_config(path: str | Path) -> dict[str, Any]:
    cfg_path = Path(path)
    with cfg_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if not isinstance(config, dict):
        raise ValueError("Config must be a dictionary-like YAML object")

    _validate_config(config)
    return config


def _validate_config(config: dict[str, Any]) -> None:
    for key in REQUIRED_ROOT_KEYS:
        if key not in config:
            raise ValueError(f"Missing required top-level key: {key}")

    document_type = config.get("document", {}).get("type")
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise ValueError(
            f"Unsupported document.type '{document_type}'. "
            f"Expected one of {sorted(ALLOWED_DOCUMENT_TYPES)}"
        )

    page_cfg = config.get("header", {}).get("page", {})
    _validate_int(page_cfg, "row")
    _validate_int(page_cfg, "col")
    _validate_regex(page_cfg.get("regex"), "header.page.regex")

    ts_cfg = config.get("header", {}).get("report_timestamp", {})
    _validate_int(ts_cfg, "row")

    if document_type == "turnout_summary":
        table_cfg = config.get("table", {})
        _validate_required_cells(table_cfg)
    elif document_type == "election_results":
        contest_cfg = config.get("contest", {})
        title_row_cfg = contest_cfg.get("title_row", {})
        _validate_int(title_row_cfg, "col")
        _validate_regex(title_row_cfg.get("regex"), "contest.title_row.regex")
        _validate_required_cells(contest_cfg.get("table", {}))

    _validate_value_rules(config.get("values", {}))


def _validate_required_cells(table_cfg: dict[str, Any]) -> None:
    search_cfg = table_cfg.get("header_row_search", {})
    required_cells = search_cfg.get("required_cells", [])
    if not isinstance(required_cells, list):
        raise ValueError("header_row_search.required_cells must be a list")
    for idx, cell_rule in enumerate(required_cells):
        if not isinstance(cell_rule, dict):
            raise ValueError(f"required_cells[{idx}] must be a dict")
        _validate_int(cell_rule, "col")
        if "equals" not in cell_rule:
            raise ValueError(f"required_cells[{idx}] missing equals")


def _validate_value_rules(values_cfg: dict[str, Any]) -> None:
    for numeric_key in ("integer", "float", "percent"):
        bucket = values_cfg.get(numeric_key, {})
        if bucket and not isinstance(bucket, dict):
            raise ValueError(f"values.{numeric_key} must be a dict")


def _validate_int(parent: dict[str, Any], key: str) -> None:
    if key not in parent:
        raise ValueError(f"Missing required key: {key}")
    if not isinstance(parent.get(key), int):
        raise ValueError(f"Expected integer for key: {key}")


def _validate_regex(pattern: Any, path: str) -> None:
    if not isinstance(pattern, str):
        raise ValueError(f"Expected string regex at {path}")
    try:
        re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"Invalid regex at {path}: {exc}") from exc
