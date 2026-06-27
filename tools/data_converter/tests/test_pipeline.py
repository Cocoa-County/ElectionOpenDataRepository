from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import pipeline
from data_converter.pipeline import runner


def _write_pipeline_config(path: Path, output_dir: Path, xlsx_path: Path) -> None:
    config = {
        "input": {
            "xlsx_path": str(xlsx_path),
            "timeout_seconds": 5,
        },
        "parse": {
            "config_refs": {
                "results": "results.yml",
                "turnout": "turnout_summary.yml",
            },
            "sheet_rules": [
                {"pattern": "^Sheet1\\.csv$", "config_ref": "turnout"},
                {"pattern": ".*", "config_ref": "results"},
            ],
            "default_config_ref": "results",
            "detect_turnout_header": True,
        },
        "warnings": {"include": True},
        "json": {"indent": 2, "omit_nulls": False},
        "io": {
            "output_dir": str(output_dir),
            "tables": {"in_memory": False, "representation": "rows"},
            "write_sheet_json": True,
            "write_manifest": True,
            "manifest_name": "manifest.json",
            "summary_only": False,
            "keep_split_csv": False,
            "delete_split_csv": True,
        },
    }
    path.write_text(yaml.safe_dump(config), encoding="utf-8")


def test_pipeline_writes_sheet_json_and_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "pipeline_output"
    config_path = tmp_path / "pipeline.yml"
    xlsx_path = tmp_path / "input.xlsx"
    xlsx_path.write_bytes(b"fake")
    _write_pipeline_config(config_path, output_dir, xlsx_path)

    def fake_split(_xlsx: str, output_dir: str, **_kwargs: object) -> None:
        split_dir = Path(output_dir)
        split_dir.mkdir(parents=True, exist_ok=True)
        (split_dir / "Sheet1.csv").write_text("turnout header", encoding="utf-8")
        (split_dir / "Sheet2.csv").write_text("results header", encoding="utf-8")

    def fake_parse(csv_path: str, yaml_path: str, **_kwargs: object) -> dict:
        if csv_path.endswith("Sheet1.csv"):
            assert yaml_path.endswith("turnout_summary.yml")
            return {"meta": {"page": 1}, "optional": None}
        assert yaml_path.endswith("results.yml")
        return {"meta": {"page": 2}, "optional": None}

    monkeypatch.setattr(runner, "split_xlsx_to_csv", fake_split)
    monkeypatch.setattr(runner, "parse_csv_file", fake_parse)

    manifest = pipeline.run_pipeline(
        str(config_path),
        omit_nulls_override=True,
    )

    assert manifest["counts"] == {"total_sheets": 2, "succeeded": 2, "failed": 0}
    assert (output_dir / "Sheet1.json").exists()
    assert (output_dir / "Sheet2.json").exists()
    assert (output_dir / "manifest.json").exists()

    sheet_payload = json.loads((output_dir / "Sheet1.json").read_text(encoding="utf-8"))
    assert "optional" not in sheet_payload


def test_pipeline_summary_only_writes_no_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "pipeline_output"
    config_path = tmp_path / "pipeline.yml"
    xlsx_path = tmp_path / "input.xlsx"
    xlsx_path.write_bytes(b"fake")
    _write_pipeline_config(config_path, output_dir, xlsx_path)

    def fake_split(_xlsx: str, output_dir: str, **_kwargs: object) -> None:
        split_dir = Path(output_dir)
        split_dir.mkdir(parents=True, exist_ok=True)
        (split_dir / "Sheet1.csv").write_text("turnout header", encoding="utf-8")

    def fake_parse(_csv_path: str, _yaml_path: str, **_kwargs: object) -> dict:
        return {"meta": {"page": 1}, "optional": None}

    monkeypatch.setattr(runner, "split_xlsx_to_csv", fake_split)
    monkeypatch.setattr(runner, "parse_csv_file", fake_parse)

    manifest = pipeline.run_pipeline(
        str(config_path),
        summary_only_override=True,
    )

    assert manifest["counts"]["succeeded"] == 1
    assert not (output_dir / "Sheet1.json").exists()
    assert not (output_dir / "manifest.json").exists()


def test_pipeline_conflicting_cleanup_flags(tmp_path: Path) -> None:
    output_dir = tmp_path / "pipeline_output"
    config_path = tmp_path / "pipeline.yml"
    xlsx_path = tmp_path / "input.xlsx"
    xlsx_path.write_bytes(b"fake")
    _write_pipeline_config(config_path, output_dir, xlsx_path)

    with pytest.raises(ValueError, match="Conflicting cleanup options"):
        pipeline.run_pipeline(
            str(config_path),
            keep_split_csv_override=True,
            delete_split_csv_override=True,
        )


def test_pipeline_output_versioning_subdir_and_manifest_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "pipeline_output"
    config_path = tmp_path / "pipeline.yml"
    xlsx_path = tmp_path / "input.xlsx"
    xlsx_path.write_bytes(b"fake")
    _write_pipeline_config(config_path, output_dir, xlsx_path)

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["io"]["versioning"] = {
        "enabled": True,
        "template": "v_{run_utc:%Y%m%d}",
    }
    config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    def fake_split(_xlsx: str, output_dir: str, **_kwargs: object) -> None:
        split_dir = Path(output_dir)
        split_dir.mkdir(parents=True, exist_ok=True)
        (split_dir / "Sheet1.csv").write_text("turnout header", encoding="utf-8")

    def fake_parse(_csv_path: str, _yaml_path: str, **_kwargs: object) -> dict:
        return {"meta": {"page": 1}}

    monkeypatch.setattr(runner, "split_xlsx_to_csv", fake_split)
    monkeypatch.setattr(runner, "parse_csv_file", fake_parse)

    manifest = pipeline.run_pipeline(str(config_path))

    assert manifest["settings"]["output_versioning_enabled"] is True
    assert manifest["settings"]["output_version"] is not None
    assert manifest["base_output_dir"] == str(output_dir)

    version_dir = output_dir / manifest["settings"]["output_version"]
    assert version_dir.exists()
    assert (version_dir / "manifest.json").exists()


def test_pipeline_in_memory_rows_mode_skips_split_csv_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "pipeline_output"
    config_path = tmp_path / "pipeline.yml"
    xlsx_path = tmp_path / "input.xlsx"
    xlsx_path.write_bytes(b"fake")
    _write_pipeline_config(config_path, output_dir, xlsx_path)

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["io"]["tables"] = {"in_memory": True, "representation": "rows"}
    config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    def fail_split(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("split_xlsx_to_csv should not be called in in-memory mode")

    def fake_split_rows(_xlsx: str) -> dict[str, list[list[str]]]:
        return {
            "Sheet1": [["Header"], ["Value"]],
            "Sheet2": [["Header"], ["Value"]],
        }

    def fake_parse_rows(rows: list[list[str]], cfg_obj: dict, **_kwargs: object) -> dict:
        assert rows
        assert cfg_obj
        return {"meta": {"page": 1}, "optional": None}

    monkeypatch.setattr(runner, "split_xlsx_to_csv", fail_split)
    monkeypatch.setattr(runner, "split_xlsx_to_row_matrices", fake_split_rows)
    monkeypatch.setattr(runner, "load_config", lambda _path: {"document": {"type": "election_results"}, "normalization": {}, "header": {"page": {"row": 0, "col": 0, "regex": ".*"}, "report_timestamp": {"row": 0}}, "values": {}})
    monkeypatch.setattr(runner, "parse_rows_with_config", fake_parse_rows)

    manifest = pipeline.run_pipeline(str(config_path), omit_nulls_override=True)

    assert manifest["counts"] == {"total_sheets": 2, "succeeded": 2, "failed": 0}
    assert manifest["settings"]["in_memory_tables"] is True
    assert manifest["settings"]["table_representation"] == "rows"


def test_pipeline_in_memory_dataframe_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pandas as pd

    output_dir = tmp_path / "pipeline_output"
    config_path = tmp_path / "pipeline.yml"
    xlsx_path = tmp_path / "input.xlsx"
    xlsx_path.write_bytes(b"fake")
    _write_pipeline_config(config_path, output_dir, xlsx_path)

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["io"]["tables"] = {"in_memory": True, "representation": "dataframe"}
    config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    def fake_split_frames(_xlsx: str) -> dict[str, pd.DataFrame]:
        return {"Sheet2": pd.DataFrame({"A": ["x"]})}

    def fake_parse_frame(frame: pd.DataFrame, cfg_obj: dict, **_kwargs: object) -> dict:
        assert not frame.empty
        assert cfg_obj
        return {"meta": {"page": 2}}

    monkeypatch.setattr(runner, "split_xlsx_to_dataframes", fake_split_frames)
    monkeypatch.setattr(runner, "load_config", lambda _path: {"document": {"type": "election_results"}, "normalization": {}, "header": {"page": {"row": 0, "col": 0, "regex": ".*"}, "report_timestamp": {"row": 0}}, "values": {}})
    monkeypatch.setattr(runner, "parse_dataframe_with_config", fake_parse_frame)

    manifest = pipeline.run_pipeline(str(config_path))
    assert manifest["counts"]["succeeded"] == 1
    assert manifest["settings"]["table_representation"] == "dataframe"


def test_pipeline_defaults_to_in_memory_when_not_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "pipeline_output"
    config_path = tmp_path / "pipeline.yml"
    xlsx_path = tmp_path / "input.xlsx"
    xlsx_path.write_bytes(b"fake")
    _write_pipeline_config(config_path, output_dir, xlsx_path)

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["io"].pop("tables", None)
    config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    def fail_split(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("split_xlsx_to_csv should not be called by default")

    def fake_split_rows(_xlsx: str) -> dict[str, list[list[str]]]:
        return {"Sheet2": [["Header"], ["Value"]]}

    monkeypatch.setattr(runner, "split_xlsx_to_csv", fail_split)
    monkeypatch.setattr(runner, "split_xlsx_to_row_matrices", fake_split_rows)
    monkeypatch.setattr(runner, "load_config", lambda _path: {"document": {"type": "election_results"}, "normalization": {}, "header": {"page": {"row": 0, "col": 0, "regex": ".*"}, "report_timestamp": {"row": 0}}, "values": {}})
    monkeypatch.setattr(runner, "parse_rows_with_config", lambda _rows, _cfg, **_kwargs: {"meta": {"page": 2}})

    manifest = pipeline.run_pipeline(str(config_path))
    assert manifest["settings"]["in_memory_tables"] is True
    assert manifest["counts"]["succeeded"] == 1


def test_pipeline_writes_combined_json_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "pipeline_output"
    config_path = tmp_path / "pipeline.yml"
    xlsx_path = tmp_path / "input.xlsx"
    xlsx_path.write_bytes(b"fake")
    _write_pipeline_config(config_path, output_dir, xlsx_path)

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["io"]["tables"] = {"in_memory": True, "representation": "rows"}
    cfg["io"]["write_sheet_json"] = False
    cfg["io"]["write_combined_json"] = True
    cfg["io"]["combined_name"] = "all_sheets.json"
    cfg["io"]["write_manifest"] = False
    config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    def fake_split_rows(_xlsx: str) -> dict[str, list[list[str]]]:
        return {
            "Sheet1": [["Header"], ["Value"]],
            "Sheet2": [["Header"], ["Value"]],
        }

    monkeypatch.setattr(runner, "split_xlsx_to_row_matrices", fake_split_rows)
    monkeypatch.setattr(runner, "load_config", lambda _path: {"document": {"type": "election_results"}, "normalization": {}, "header": {"page": {"row": 0, "col": 0, "regex": ".*"}, "report_timestamp": {"row": 0}}, "values": {}})
    monkeypatch.setattr(runner, "parse_rows_with_config", lambda _rows, _cfg, **_kwargs: {"meta": {"page": 2}, "optional": None})

    manifest = pipeline.run_pipeline(str(config_path), omit_nulls_override=True)

    assert manifest["settings"]["write_combined_json"] is True
    assert manifest["settings"]["combined_name"] == "all_sheets.json"
    assert not (output_dir / "Sheet1.json").exists()
    assert not (output_dir / "manifest.json").exists()
    combined_payload = json.loads((output_dir / "all_sheets.json").read_text(encoding="utf-8"))
    assert "sheets" in combined_payload
    assert "Sheet1" in combined_payload["sheets"]
    assert "optional" not in combined_payload["sheets"]["Sheet1"]


def test_pipeline_transform_writes_election_and_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "pipeline_output"
    config_path = tmp_path / "pipeline.yml"
    xlsx_path = tmp_path / "input.xlsx"
    xlsx_path.write_bytes(b"fake")
    _write_pipeline_config(config_path, output_dir, xlsx_path)

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["io"]["tables"] = {"in_memory": True, "representation": "rows"}
    cfg["io"]["write_sheet_json"] = False
    cfg["io"]["write_combined_json"] = False
    cfg["io"]["write_manifest"] = False
    cfg["transform"] = {
        "enabled": True,
        "election_id": "2026-06-02-primary",
        "output_path": str(tmp_path / "elections" / "2026-06-02-primary" / "election.json"),
        "write_metadata": True,
        "metadata_path": str(tmp_path / "elections" / "2026-06-02-primary" / "metadata.json"),
        "update_index": False,
    }
    config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    def fake_split_rows(_xlsx: str) -> dict[str, list[list[str]]]:
        return {
            "Sheet1": [["Header"], ["Value"]],
            "Sheet2": [["Header"], ["Value"]],
        }

    def fake_parse_rows(_rows: list[list[str]], cfg_obj: dict, **_kwargs: object) -> dict:
        if cfg_obj.get("document", {}).get("type") == "turnout_summary":
            return {
                "precincts": [
                    {
                        "precinct": "P1",
                        "results": {
                            "Total": {
                                "registered_voters": 100,
                                "voters_cast": 60,
                            }
                        },
                    }
                ]
            }
        return {
            "contest": {"contest_name": "ASSESSOR", "vote_for": 1},
            "options": ["A", "B"],
            "precincts": [
                {
                    "precinct": "P1",
                    "results": {
                        "Total": {
                            "registered_voters": 90,
                            "times_cast": 50,
                            "options": {
                                "A": {"votes": 30, "percent": 60.0},
                                "B": {"votes": 20, "percent": 40.0},
                            },
                            "total_votes": 50,
                        }
                    },
                }
            ],
        }

    def fake_load_config(path: Path) -> dict:
        if str(path).endswith("turnout_summary.yml"):
            return {
                "document": {"type": "turnout_summary"},
                "normalization": {},
                "header": {"page": {"row": 0, "col": 0, "regex": ".*"}, "report_timestamp": {"row": 0}},
                "values": {},
            }
        return {
            "document": {"type": "election_results"},
            "normalization": {},
            "header": {"page": {"row": 0, "col": 0, "regex": ".*"}, "report_timestamp": {"row": 0}},
            "values": {},
        }

    monkeypatch.setattr(runner, "split_xlsx_to_row_matrices", fake_split_rows)
    monkeypatch.setattr(runner, "load_config", fake_load_config)
    monkeypatch.setattr(runner, "parse_rows_with_config", fake_parse_rows)

    manifest = pipeline.run_pipeline(str(config_path))

    election_path = tmp_path / "elections" / "2026-06-02-primary" / "election.json"
    metadata_path = tmp_path / "elections" / "2026-06-02-primary" / "metadata.json"
    assert election_path.exists()
    assert metadata_path.exists()
    election_payload = json.loads(election_path.read_text(encoding="utf-8"))
    assert "contests" in election_payload
    assert election_payload["contests"][0]["precincts"]["P1"]["registeredVoters"] == 100
    assert manifest["settings"]["transform_enabled"] is True
