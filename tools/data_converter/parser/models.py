from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass
class ParseWarning:
    row: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"row": self.row, "message": self.message}


@dataclass
class ParsedDocument:
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.data

    def to_json(self, indent: int = 2, include_nulls: bool = True) -> str:
        payload = self.data if include_nulls else _omit_null_fields(self.data)
        return json.dumps(payload, indent=indent, ensure_ascii=False)

    def write_json(self, path: str | Path, indent: int = 2, include_nulls: bool = True) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            self.to_json(indent=indent, include_nulls=include_nulls),
            encoding="utf-8",
        )


def to_json_string(data: Any, indent: int = 2, include_nulls: bool = True) -> str:
    payload = data if include_nulls else _omit_null_fields(data)
    return json.dumps(payload, indent=indent, ensure_ascii=False)


def _omit_null_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _omit_null_fields(inner_value)
            for key, inner_value in value.items()
            if inner_value is not None
        }
    if isinstance(value, list):
        return [_omit_null_fields(item) for item in value]
    return value
