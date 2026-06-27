from __future__ import annotations

from datetime import datetime
import re
from typing import Any


def safe_get(row: list[str], col: int) -> str:
    if col < 0:
        return ""
    if col >= len(row):
        return ""
    return row[col]


def is_blank_row(row: list[str]) -> bool:
    return all(cell.strip() == "" for cell in row)


def row_matches_required_cells(row: list[str], rules: list[dict[str, Any]]) -> bool:
    for rule in rules:
        col = int(rule["col"])
        expected = str(rule["equals"])
        if safe_get(row, col) != expected:
            return False
    return True


def find_header_row(
    rows: list[list[str]],
    start_row: int,
    max_scan_rows: int,
    required_cells: list[dict[str, Any]],
) -> int | None:
    end_row = min(len(rows), start_row + max_scan_rows)
    for row_idx in range(start_row, end_row):
        if row_matches_required_cells(rows[row_idx], required_cells):
            return row_idx
    return None


def extract_regex_groups(text: str, pattern: str) -> dict[str, str] | None:
    match = re.match(pattern, text)
    if not match:
        return None
    return match.groupdict()


def find_datetime_in_row(row: list[str], formats: list[str]) -> datetime | None:
    for value in row:
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def parse_common_header(rows: list[list[str]], cfg: dict[str, Any]) -> dict[str, Any]:
    header_cfg = cfg["header"]

    page_cfg = header_cfg["page"]
    page_row = rows[page_cfg["row"]]
    page_text = safe_get(page_row, page_cfg["col"])
    page_match = extract_regex_groups(page_text, page_cfg["regex"])
    if not page_match:
        raise ValueError(f"Could not parse page metadata from text: {page_text}")

    ts_cfg = header_cfg["report_timestamp"]
    ts_row = rows[ts_cfg["row"]]
    ts_formats = ts_cfg.get("scan_row_for_datetime", {}).get("formats", [])
    parsed_ts = find_datetime_in_row(ts_row, ts_formats)

    out: dict[str, Any] = {
        "page": int(page_match["page"]),
        "total_pages": int(page_match["total_pages"]),
        "report_timestamp": parsed_ts.isoformat() if parsed_ts else None,
    }
    return out


def is_precinct_label(label: str, pattern: str) -> bool:
    return bool(re.match(pattern, label))


def is_child_row(label: str, child_rows: list[str]) -> bool:
    return label in child_rows


def is_summary_group_parent(label: str, parent_labels: list[str]) -> bool:
    return label in parent_labels


def is_summary_row(label: str, regex_labels: list[str]) -> bool:
    for pattern in regex_labels:
        if re.match(pattern, label):
            return True
    return False
