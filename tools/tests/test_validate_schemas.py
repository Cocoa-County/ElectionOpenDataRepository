import importlib.util
import shutil
from pathlib import Path


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _copy_schemas(tmp_path: Path) -> None:
    source = Path(__file__).parents[2] / "schemas"
    target = tmp_path / "schemas"
    shutil.copytree(source, target)


def _build_valid_repo(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_json(
        tmp_path / "elections.index.json",
        """{
  "version": 1,
  "updated": "2026-07-12",
  "elections": [
    {
      "id": "ca-test-2026-06-02-primary",
      "label": "Test Election",
      "snapshots": [
        {
          "id": "final",
          "layers": [
            {
              "id": "precincts",
              "type": "precinct",
              "label": "Precincts",
              "dataUrl": "elections/ca/test/2026-06-02-primary/results.precincts.json",
              "gisUrl": "elections/ca/test/2026-06-02-primary/precincts.gis.json",
              "joinField": "precinct_id"
            }
          ]
        }
      ]
    }
  ]
}
""",
    )
    _write_json(
        tmp_path / "elections/ca/test/2026-06-02-primary/results.precincts.json",
        """{
  "geography": {"id": "precincts", "type": "precinct", "label": "Precincts", "joinField": "precinct_id"},
  "contests": [
    {
      "index": 0,
      "id": "c1",
      "label": "Contest",
      "choices": [{"index": 0, "id": "a", "label": "A", "votes": 1}],
      "areas": {"p-1": {"label": "P1", "registeredVoters": 1, "totalVoters": 1, "results": [1]}}
    }
  ]
}
""",
    )
    _write_json(
        tmp_path / "elections/ca/test/2026-06-02-primary/precincts.gis.json",
        """{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {"precinct_id": "p-1"},
      "geometry": {"type": "Polygon", "coordinates": [[[-122.1, 37.1], [-122.0, 37.1], [-122.0, 37.2], [-122.1, 37.2], [-122.1, 37.1]]]}
    }
  ]
}
""",
    )


def test_validate_schemas_success(tmp_path: Path):
    _build_valid_repo(tmp_path)
    module = _load_module("validate_schemas", Path(__file__).parents[1] / "validate_schemas.py")
    assert module.validate_schemas(repo_root=tmp_path)


def test_validate_schemas_invalid_election_payload(tmp_path: Path):
    _build_valid_repo(tmp_path)
    _write_json(tmp_path / "elections/ca/test/2026-06-02-primary/results.precincts.json", "{}")
    module = _load_module("validate_schemas", Path(__file__).parents[1] / "validate_schemas.py")
    assert not module.validate_schemas(repo_root=tmp_path)


def test_validate_schemas_rejects_legacy_snapshot_fields(tmp_path: Path):
    _copy_schemas(tmp_path)
    _write_json(
        tmp_path / "elections.index.json",
        """{
  "version": 1,
  "updated": "2026-07-12",
  "elections": [
    {
      "id": "ca-test-2026-06-02-primary",
      "label": "Test Election",
      "snapshots": [
        {
          "id": "final",
          "dataUrl": "elections/ca/test/2026-06-02-primary/election.json",
          "areasUrl": "elections/ca/test/2026-06-02-primary/precincts.gis.json",
          "areaIdField": "precinct_id",
          "areaLabelField": "precinct"
        }
      ]
    }
  ]
}
""",
    )
    _write_json(tmp_path / "elections/ca/test/2026-06-02-primary/election.json", "{\"contests\": []}")
    _write_json(
        tmp_path / "elections/ca/test/2026-06-02-primary/precincts.gis.json",
        """{"type":"FeatureCollection","features":[]}""",
    )

    module = _load_module("validate_schemas", Path(__file__).parents[1] / "validate_schemas.py")
    assert not module.validate_schemas(repo_root=tmp_path)


def test_validate_schemas_allows_nullable_result_values(tmp_path: Path):
    _build_valid_repo(tmp_path)
    _write_json(
        tmp_path / "elections/ca/test/2026-06-02-primary/results.precincts.json",
        """{
  "geography": {"id": "precincts", "type": "precinct", "label": "Precincts", "joinField": "precinct_id"},
  "contests": [
    {
      "index": 0,
      "id": "c1",
      "label": "Contest",
      "choices": [{"index": 0, "id": "a", "label": "A", "votes": null}],
      "areas": {
        "p-1": {
          "label": "P1",
          "registeredVoters": null,
          "totalVoters": null,
          "results": [null],
          "percentage": [null],
          "winner": null
        }
      }
    }
  ]
}
""",
    )

    module = _load_module("validate_schemas", Path(__file__).parents[1] / "validate_schemas.py")
    assert module.validate_schemas(repo_root=tmp_path)


def test_validate_schemas_allows_missing_voter_totals(tmp_path: Path):
    _build_valid_repo(tmp_path)
    _write_json(
        tmp_path / "elections/ca/test/2026-06-02-primary/results.precincts.json",
        """{
  "geography": {"id": "precincts", "type": "precinct", "label": "Precincts", "joinField": "precinct_id"},
  "contests": [
    {
      "index": 0,
      "id": "c1",
      "label": "Contest",
      "choices": [{"index": 0, "id": "a", "label": "A", "votes": 1}],
      "areas": {
        "p-1": {
          "label": "P1",
          "results": [1]
        }
      }
    }
  ]
}
""",
    )

    module = _load_module("validate_schemas", Path(__file__).parents[1] / "validate_schemas.py")
    assert module.validate_schemas(repo_root=tmp_path)


def test_validate_schemas_uses_metadata_schema_for_metadata_prefix_files(tmp_path: Path):
    _copy_schemas(tmp_path)
    _write_json(
        tmp_path / "elections.index.json",
        """{
  "version": 1,
  "updated": "2026-07-12",
  "elections": [
    {
      "id": "ca-test-2026-06-02-primary",
      "label": "Test Election",
      "snapshots": [
        {
          "id": "final",
          "layers": [
            {
              "id": "precincts",
              "type": "precinct",
              "label": "Precincts",
              "dataUrl": "elections/ca/test/2026-06-02-primary/results.precincts.json",
              "gisUrl": "elections/ca/test/2026-06-02-primary/precincts.gis.json",
              "joinField": "precinct_id",
              "metadataUrl": "elections/ca/test/2026-06-02-primary/metadata.cities.json"
            }
          ]
        }
      ]
    }
  ]
}
""",
    )
    _write_json(
        tmp_path / "elections/ca/test/2026-06-02-primary/results.precincts.json",
        """{
  "contests": [
    {
      "index": 0,
      "id": "c1",
      "label": "Contest",
      "choices": [{"index": 0, "id": "a", "label": "A", "votes": 1}],
      "areas": {"p-1": {"label": "P1", "registeredVoters": 1, "totalVoters": 1, "results": [1]}}
    }
  ]
}
""",
    )
    _write_json(
        tmp_path / "elections/ca/test/2026-06-02-primary/precincts.gis.json",
        """{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {"precinct_id": "p-1"},
      "geometry": {"type": "Polygon", "coordinates": [[[-122.1, 37.1], [-122.0, 37.1], [-122.0, 37.2], [-122.1, 37.2], [-122.1, 37.1]]]}
    }
  ]
}
""",
    )
    _write_json(
        tmp_path / "elections/ca/test/2026-06-02-primary/metadata.cities.json",
        """{
  "schemaVersion": 1,
  "generated": "2026-07-12"
}
""",
    )

    module = _load_module("validate_schemas", Path(__file__).parents[1] / "validate_schemas.py")
    assert module.validate_schemas(repo_root=tmp_path)


def test_validate_schemas_specific_file_mode_passes_valid_file(tmp_path: Path):
    _build_valid_repo(tmp_path)
    module = _load_module("validate_schemas", Path(__file__).parents[1] / "validate_schemas.py")
    assert module.validate_schemas(
        repo_root=tmp_path,
        files=["elections/ca/test/2026-06-02-primary/results.precincts.json"],
    )


def test_validate_schemas_specific_file_mode_fails_invalid_file(tmp_path: Path):
    _build_valid_repo(tmp_path)
    _write_json(tmp_path / "elections/ca/test/2026-06-02-primary/results.precincts.json", "{}")
    module = _load_module("validate_schemas", Path(__file__).parents[1] / "validate_schemas.py")
    assert not module.validate_schemas(
        repo_root=tmp_path,
        files=["elections/ca/test/2026-06-02-primary/results.precincts.json"],
    )


def test_validate_schemas_allows_empty_winner_array(tmp_path: Path):
    _build_valid_repo(tmp_path)
    _write_json(
        tmp_path / "elections/ca/test/2026-06-02-primary/results.precincts.json",
        """{
  "geography": {"id": "precincts", "type": "precinct", "label": "Precincts", "joinField": "precinct_id"},
  "contests": [
    {
      "index": 0,
      "id": "c1",
      "label": "Contest",
      "choices": [{"index": 0, "id": "a", "label": "A", "votes": 1}],
      "areas": {
        "p-1": {
          "label": "P1",
          "registeredVoters": 1,
          "totalVoters": 1,
          "results": [1],
          "winner": []
        }
      }
    }
  ]
}
""",
    )

    module = _load_module("validate_schemas", Path(__file__).parents[1] / "validate_schemas.py")
    assert module.validate_schemas(repo_root=tmp_path)