from __future__ import annotations

from typing import Any

from .matching import (
    extract_regex_groups,
    find_header_row,
    is_blank_row,
    is_child_row,
    is_precinct_label,
    is_summary_group_parent,
    is_summary_row,
    parse_common_header,
    safe_get,
)
from .models import ParseWarning
from .value_parser import parse_integer, parse_percent


def parse_results(
    rows: list[list[str]],
    cfg: dict[str, Any],
    warnings: list[ParseWarning],
) -> dict[str, Any]:
    meta = parse_common_header(rows, cfg)

    contest_cfg = cfg["contest"]
    title_info, title_row_idx = _parse_contest_title(rows, contest_cfg)

    table_cfg = contest_cfg["table"]
    search_cfg = table_cfg["header_row_search"]
    start_row = title_row_idx + search_cfg.get("start_row_offset", 1)
    header_row_idx = find_header_row(
        rows,
        start_row=start_row,
        max_scan_rows=search_cfg["max_scan_rows"],
        required_cells=search_cfg["required_cells"],
    )
    if header_row_idx is None:
        raise ValueError("Results table header row not found")

    header_row = rows[header_row_idx]
    right_block = table_cfg["right_block"]
    options = _extract_options(header_row, right_block)
    trailing_columns = _extract_trailing_columns(header_row, right_block.get("trailing_columns", {}))

    records_cfg = cfg["records"]
    precinct_cfg = records_cfg["precinct_group"]
    footer_cfg = cfg["footer"]
    values_cfg = cfg.get("values", {})
    masked_tokens = set(values_cfg.get("masked_tokens", []))
    skip_labels = set(records_cfg.get("skip_rows", []))

    left_block = table_cfg["left_block"]
    right_label_col = right_block["label_col"]

    precincts: list[dict[str, Any]] = []
    summaries = {"rows": [], "groups": []}
    state: dict[str, Any] = {
        "current_precinct": None,
        "current_summary_group": None,
    }

    for row_idx in range(header_row_idx + 1, len(rows)):
        row = rows[row_idx]
        left_label = safe_get(row, left_block["label_col"])
        right_label = safe_get(row, right_label_col)
        label = right_label or left_label

        if is_blank_row(row):
            continue
        if label in skip_labels:
            continue

        if is_precinct_label(left_label, precinct_cfg["parent_regex"]):
            entry = {"precinct": left_label, "results": {}}
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
            summary_row = _parse_result_metrics(
                row,
                options,
                left_block,
                trailing_columns,
                values_cfg,
                masked_tokens,
            )
            summary_row["label"] = label
            summaries["rows"].append(summary_row)
            continue

        if is_child_row(label, precinct_cfg["child_rows"]):
            parsed = _parse_result_metrics(
                row,
                options,
                left_block,
                trailing_columns,
                values_cfg,
                masked_tokens,
            )
            if state["current_precinct"] is not None:
                state["current_precinct"]["results"][label] = parsed
                continue
            if state["current_summary_group"] is not None:
                state["current_summary_group"]["results"][label] = parsed
                continue
            warnings.append(
                ParseWarning(
                    row=row_idx,
                    message="Child row encountered without active precinct or summary group",
                )
            )

    return {
        "meta": meta,
        "contest": title_info,
        "options": [option["name"] for option in options],
        "precincts": precincts,
        "summaries": summaries,
    }


def _parse_contest_title(rows: list[list[str]], contest_cfg: dict[str, Any]) -> tuple[dict[str, Any], int]:
    title_cfg = contest_cfg["title_row"]
    col = title_cfg["col"]
    regex = title_cfg["regex"]

    for row_idx, row in enumerate(rows):
        text = safe_get(row, col)
        groups = extract_regex_groups(text, regex)
        if groups:
            out = {
                "contest_name": groups["contest_name"],
                "vote_for": int(groups["vote_for"]),
                "privacy_note": groups.get("privacy_note"),
            }
            return out, row_idx

    raise ValueError("Contest title row not found")


def _extract_options(header_row: list[str], right_block: dict[str, Any]) -> list[dict[str, Any]]:
    options_cfg = right_block["options"]
    start_col = options_cfg["start_col"]
    pair_width = options_cfg["pair_width"]
    value_col_offset = options_cfg["value_col_offset"]
    percent_col_offset = options_cfg["percent_col_offset"]
    stop_headers = set(options_cfg["stop_headers"])

    options: list[dict[str, Any]] = []
    col = start_col
    while col < len(header_row):
        name = safe_get(header_row, col)
        if not name:
            # Some exports can insert a blank spacer before a candidate header.
            # Advance one column when blank so shifted headers are still discovered.
            col += 1
            continue
        if name in stop_headers:
            break

        options.append(
            {
                "name": name,
                "votes_col": col + value_col_offset,
                "percent_col": col + percent_col_offset,
            }
        )
        col += pair_width

    return options


def _extract_trailing_columns(
    header_row: list[str],
    trailing_cfg: dict[str, Any],
) -> dict[str, int]:
    found: dict[str, int] = {}
    for key, spec in trailing_cfg.items():
        expected = spec.get("header_equals")
        for idx, value in enumerate(header_row):
            if value == expected:
                found[key] = idx
                break
    return found


def _parse_result_metrics(
    row: list[str],
    options: list[dict[str, Any]],
    left_block: dict[str, int],
    trailing_columns: dict[str, int],
    values_cfg: dict[str, Any],
    masked_tokens: set[str],
) -> dict[str, Any]:
    options_out: dict[str, dict[str, Any]] = {}
    for option in options:
        name = option["name"]
        options_out[name] = {
            "votes": parse_integer(
                safe_get(row, option["votes_col"]),
                values_cfg.get("integer", {}),
                masked_tokens,
            ),
            "percent": parse_percent(
                safe_get(row, option["percent_col"]),
                values_cfg.get("percent", {}),
                masked_tokens,
            ),
        }

    total_votes_col = trailing_columns.get("total_votes")
    unresolved_col = trailing_columns.get("unresolved_write_in")

    return {
        "times_cast": parse_integer(
            safe_get(row, left_block["times_cast_col"]),
            values_cfg.get("integer", {}),
            masked_tokens,
        ),
        "registered_voters": parse_integer(
            safe_get(row, left_block["registered_voters_col"]),
            values_cfg.get("integer", {}),
            masked_tokens,
        ),
        "options": options_out,
        "total_votes": parse_integer(
            safe_get(row, total_votes_col) if total_votes_col is not None else "",
            values_cfg.get("integer", {}),
            masked_tokens,
        ),
        "unresolved_write_in": parse_integer(
            safe_get(row, unresolved_col) if unresolved_col is not None else "",
            values_cfg.get("integer", {}),
            masked_tokens,
        ),
    }
