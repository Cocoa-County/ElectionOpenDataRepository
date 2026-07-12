from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_file(path: Path, payload: dict[str, Any], *, indent: int, include_nulls: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=indent, ensure_ascii=False)
    if not include_nulls:
        text = json.dumps(_drop_nulls(payload), indent=indent, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")


def update_elections_index(
    *,
    index_path: Path,
    election_id: str,
    data_url: str,
    precincts_url: str | None,
    precinct_id_field: str | None,
    precinct_label_field: str | None,
    label: str | None,
    date: str | None,
    election_type: str | None,
    county: str | None,
    state: str | None,
) -> None:
    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}")

    index_obj = json.loads(index_path.read_text(encoding="utf-8"))
    elections = index_obj.get("elections")
    if not isinstance(elections, list):
        raise ValueError("elections.index.json missing top-level elections array")

    matched = None
    for row in elections:
        if isinstance(row, dict) and row.get("id") == election_id:
            matched = row
            break

    if matched is None:
        matched = {"id": election_id}
        elections.append(matched)

    if not precincts_url:
        raise ValueError("precincts_url is required to update elections index in layers-only mode")
    if not precinct_id_field:
        raise ValueError("precinct_id_field is required to update elections index in layers-only mode")

    snapshot_layers = [
        {
            "id": "precincts",
            "type": "precinct",
            "label": "Precincts",
            "dataUrl": data_url,
            "gisUrl": precincts_url,
            "joinField": precinct_id_field,
        }
    ]
    if precinct_label_field:
        snapshot_layers[0]["labelField"] = precinct_label_field

    matched["snapshots"] = [
        {
            "id": "latest",
            "snapshotTypes": ["latest"],
            "layers": snapshot_layers,
        }
    ]
    if label:
        matched["label"] = label
    if date:
        matched["date"] = date
    if election_type:
        matched["type"] = election_type
    if county:
        matched["county"] = county
    if state:
        matched["state"] = state

    for legacy_key in ["dataUrl", "areasUrl", "areaIdField", "areaLabelField", "precinctsUrl", "precinctIdField", "precinctLabelField"]:
        if legacy_key in matched:
            del matched[legacy_key]

    index_path.write_text(json.dumps(index_obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _drop_nulls(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _drop_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_drop_nulls(v) for v in value]
    return value
