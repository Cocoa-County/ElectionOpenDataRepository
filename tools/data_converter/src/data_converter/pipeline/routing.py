from __future__ import annotations

from pathlib import Path
import re
from typing import Any


def resolve_config_refs(refs: dict[str, str], base_dir: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for key, value in refs.items():
        path = Path(value)
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        out[key] = path
    return out


def pick_parser_config(csv_file: Path, config_refs: dict[str, Path], parse_cfg: dict[str, Any]) -> Path:
    sheet_rules = parse_cfg.get("sheet_rules", [])
    for rule in sheet_rules:
        pattern = rule.get("pattern")
        config_ref = rule.get("config_ref")
        if not pattern or not config_ref:
            continue
        if re.search(pattern, csv_file.name):
            if config_ref not in config_refs:
                raise ValueError(f"Unknown config_ref in sheet rule: {config_ref}")
            return config_refs[config_ref]

    if parse_cfg.get("detect_turnout_header", True) and looks_like_turnout(csv_file):
        return config_refs["turnout"]

    default_ref = parse_cfg.get("default_config_ref", "results")
    if default_ref not in config_refs:
        raise ValueError(f"Unknown default_config_ref: {default_ref}")
    return config_refs[default_ref]


def looks_like_turnout(csv_file: Path) -> bool:
    text = csv_file.read_text(encoding="utf-8", errors="replace")
    return (
        "Registered" in text
        and "Cards Cast" in text
        and "Voters Cast" in text
        and "% Turnout" in text
    )
