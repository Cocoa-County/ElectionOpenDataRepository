from __future__ import annotations

from typing import Any


DEFAULT_NULL_TOKENS = {"", "N/A", "n/a", "NA", "na"}


def parse_integer(value: str, cfg: dict[str, Any], masked_tokens: set[str] | None = None) -> int | None:
    text = value.strip()
    if _is_null_like(text, cfg, masked_tokens):
        return None

    if cfg.get("strip_commas", False):
        text = text.replace(",", "")

    return int(text)


def parse_float(value: str, cfg: dict[str, Any], masked_tokens: set[str] | None = None) -> float | None:
    text = value.strip()
    if _is_null_like(text, cfg, masked_tokens):
        return None
    return float(text)


def parse_percent(value: str, cfg: dict[str, Any], masked_tokens: set[str] | None = None) -> float | None:
    text = value.strip()
    if _is_null_like(text, cfg, masked_tokens):
        return None

    suffix = cfg.get("strip_suffix", "%")
    if suffix and text.endswith(suffix):
        text = text[: -len(suffix)].strip()

    return float(text)


def _is_null_like(text: str, cfg: dict[str, Any], masked_tokens: set[str] | None) -> bool:
    if text in DEFAULT_NULL_TOKENS and cfg.get("empty_as_null", True):
        return True

    if masked_tokens and text in masked_tokens and cfg.get("masked_as_null", True):
        return True

    return False
