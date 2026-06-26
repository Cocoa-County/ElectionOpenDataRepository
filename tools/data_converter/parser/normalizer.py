from __future__ import annotations

import re
from typing import Any


def normalize_cell(value: str, cfg: dict[str, Any]) -> str:
    text = value
    newline_replacement = cfg.get("newline_replacement", " ")
    text = text.replace("\r\n", newline_replacement)
    text = text.replace("\n", newline_replacement)
    text = text.replace("\r", newline_replacement)

    if cfg.get("collapse_whitespace", True):
        text = re.sub(r"\s+", " ", text)

    if cfg.get("trim", True):
        text = text.strip()

    if cfg.get("strip_wrapping_quotes", False) and len(text) >= 2:
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]

    return text


def normalize_rows(rows: list[list[str]], cfg: dict[str, Any]) -> list[list[str]]:
    normalized: list[list[str]] = []
    for row in rows:
        normalized.append([normalize_cell(cell, cfg) for cell in row])
    return normalized
