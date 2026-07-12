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