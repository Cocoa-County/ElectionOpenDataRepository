from __future__ import annotations

from typing import Any

from .matching import (
    is_blank_row,
    find_header_row,
    is_child_row,
    is_precinct_label,
    match_derived_child_row,
    is_summary_group_parent,
    is_summary_row,
    parse_common_header,
    safe_get,
)
from .models import ParseWarning
from .value_parser import parse_integer, parse_percent


def parse_turnout_summary(
    rows: list[list[str]],
    cfg: dict[str, Any],
    warnings: list[ParseWarning],
) -> dict[str, Any]:
    meta = parse_common_header(rows, cfg)
    title_block = _parse_title_block(rows, cfg)
    meta.update(title_block)

    table_cfg = cfg["table"]
    search_cfg = table_cfg["header_row_search"]
    header_row_idx = find_header_row(
        rows,
        start_row=0,
        max_scan_rows=search_cfg["max_scan_rows"],
        required_cells=search_cfg["required_cells"],
    )
    if header_row_idx is None:
        raise ValueError("Turnout table header row not found")

    columns = table_cfg["columns"]
    precinct_cfg = cfg["precinct_group"]
    footer_cfg = cfg["footer"]
    values_cfg = cfg.get("values", {})
    derived_child_rows = precinct_cfg.get("derived_child_rows", [])

    precincts: list[dict[str, Any]] = []
    summaries = {"rows": [], "groups": []}
    state: dict[str, Any] = {
        "current_precinct": None,
        "current_summary_group": None,
    }

    for row_idx in range(header_row_idx + 1, len(rows)):
        row = rows[row_idx]
        label = safe_get(row, columns["label"])

        if is_blank_row(row):
            continue

        derived_child_label = match_derived_child_row(
            label,
            state["current_precinct"].get("precinct") if state["current_precinct"] is not None else None,
            derived_child_rows,
        )
        if derived_child_label is not None:
            metrics = _parse_turnout_metrics(row, columns, values_cfg)
            state["current_precinct"]["results"][derived_child_label] = metrics
            continue

        derived_summary_label = match_derived_child_row(
            label,
            state["current_summary_group"].get("label") if state["current_summary_group"] is not None else None,
            derived_child_rows,
        )
        if derived_summary_label is not None:
            metrics = _parse_turnout_metrics(row, columns, values_cfg)
            state["current_summary_group"]["results"][derived_summary_label] = metrics
            continue

        if is_precinct_label(label, precinct_cfg["parent_regex"]):
            entry = {"precinct": label, "results": {}}
            precincts.append(entry)
            state["current_precinct"] = entry
            state["current_summary_group"] = None
            continue

        if is_summary_group_parent(label, footer_cfg["summary_groups"]["parent_labels"]):
            group = {"label": label, "results": {}}
            summaries["groups"].append(group)
            state["current_summary_group"] = group
            state["current_precinct"] = None
            continue

        if is_summary_row(label, footer_cfg["summary_rows"]["regex_labels"]):
            summaries["rows"].append(_parse_turnout_metrics(row, columns, values_cfg))
            summaries["rows"][-1]["label"] = label
            continue

        if is_child_row(label, precinct_cfg["child_rows"]):
            metrics = _parse_turnout_metrics(row, columns, values_cfg)
            if state["current_precinct"] is not None:
                state["current_precinct"]["results"][label] = metrics
                continue
            if state["current_summary_group"] is not None:
                state["current_summary_group"]["results"][label] = metrics
                continue
            warnings.append(
                ParseWarning(
                    row=row_idx,
                    message="Child row encountered without active precinct or summary group",
                )
            )
            continue

    return {"meta": meta, "precincts": precincts, "summaries": summaries}


def _parse_title_block(rows: list[list[str]], cfg: dict[str, Any]) -> dict[str, Any]:
    title_cfg = cfg["title_block"]
    start_row = title_cfg["start_row"]
    col = title_cfg["col"]
    line_names = title_cfg["lines"]

    out: dict[str, Any] = {}
    for offset, key in enumerate(line_names):
        out[key] = safe_get(rows[start_row + offset], col)
    return out


def _parse_turnout_metrics(
    row: list[str],
    columns: dict[str, int],
    values_cfg: dict[str, Any],
) -> dict[str, Any]:
    return {
        "registered_voters": parse_integer(
            safe_get(row, columns["registered_voters"]),
            values_cfg.get("integer", {}),
        ),
        "cards_cast": parse_integer(
            safe_get(row, columns["cards_cast"]),
            values_cfg.get("integer", {}),
        ),
        "voters_cast": parse_integer(
            safe_get(row, columns["voters_cast"]),
            values_cfg.get("integer", {}),
        ),
        "turnout": parse_percent(
            safe_get(row, columns["turnout"]),
            values_cfg.get("percent", {}),
        ),
    }
