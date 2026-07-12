#!/usr/bin/env python3
"""
Validate that all paths in elections.index.json resolve to existing files.
This ensures the migration was successful.
"""

import json
from pathlib import Path
import sys


REQUIRED_LAYER_FIELDS = ["id", "type", "label", "dataUrl", "gisUrl", "joinField"]


def _has_legacy_area_fields(node: dict) -> bool:
    return all(key in node for key in ["dataUrl", "areasUrl", "areaIdField", "areaLabelField"])


def _layer_errors(owner_id: str, layer: dict) -> list[str]:
    missing = [key for key in REQUIRED_LAYER_FIELDS if key not in layer or layer.get(key) in (None, "")]
    layer_id = str(layer.get("id", "unknown"))
    errors = []
    if "/" in layer_id:
        errors.append(f"ERROR: Layer {owner_id}/layers/{layer_id} must not contain '/'. Use scoped IDs as electionId/snapshotId/layerId outside the layer id field")
    if not missing:
        return errors
    errors.append(f"ERROR: Layer {owner_id}/layers/{layer_id} is missing required fields: {', '.join(missing)}")
    return errors


def _check_url(repo_root: Path, file_checks: list[tuple[str, str, str, bool]], owner_id: str, key: str, url: str) -> bool:
    file_path = repo_root / url
    exists = file_path.exists()
    file_checks.append((owner_id, key, url, exists))
    return exists


def _validate_layers(repo_root: Path, owner_id: str, layers: list[dict], file_checks: list[tuple[str, str, str, bool]]) -> bool:
    all_valid = True
    for layer in layers:
        for error in _layer_errors(owner_id, layer):
            print(error)
            all_valid = False
        layer_id = layer.get("id", "unknown")
        prefix = f"{owner_id}/layers/{layer_id}"
        for key in ["dataUrl", "gisUrl", "metadataUrl"]:
            url = layer.get(key)
            if not url:
                continue
            if not _check_url(repo_root, file_checks, prefix, key, url):
                print(f"ERROR: Missing layer file for {prefix}: {url}")
                all_valid = False
    return all_valid


def validate_index():
    """Check all index entries and paths."""
    repo_root = Path(__file__).parent.parent
    index_path = repo_root / "elections.index.json"
    
    if not index_path.exists():
        print(f"ERROR: Index file not found: {index_path}")
        return False
    
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    elections = index.get("elections", [])
    if not elections:
        print("ERROR: No elections found in index")
        return False
    
    all_valid = True
    file_checks = []
    
    for election in elections:
        election_id = election.get("id", "unknown")
        county = election.get("county", "unknown")

        if "layers" in election:
            print(f"ERROR: Election {election_id} defines election-level layers. Use snapshot layers instead.")
            all_valid = False

        snapshots = election.get("snapshots", [])
        if not snapshots:
            print(f"ERROR: Election {election_id} has no snapshots. At least one snapshot is required.")
            all_valid = False
        
        # Check legacy main dataUrl and areasUrl
        for key in ["dataUrl", "areasUrl"]:
            if key in election:
                url = election[key]
                exists = _check_url(repo_root, file_checks, election_id, key, url)
                if not exists:
                    print(f"ERROR: Missing file for {election_id} ({county}): {url}")
                    all_valid = False

        layers = election.get("layers", [])
        if layers:
            if not _validate_layers(repo_root, election_id, layers, file_checks):
                all_valid = False
        has_parent_layers = bool(layers)
        
        # Check metadata file
        if "dataUrl" in election:
            data_url = election["dataUrl"]
            # Infer metadata URL by replacing filename
            metadata_url = data_url.rsplit('/', 1)[0] + "/metadata.json"
            metadata_path = repo_root / metadata_url
            exists = metadata_path.exists()
            file_checks.append((election_id, "metadata.json", metadata_url, exists))
            if not exists:
                print(f"WARNING: Metadata not found for {election_id}: {metadata_url}")
        
        # Check snapshots
        seen_snapshot_ids = set()
        for snapshot in snapshots:
            snapshot_id = snapshot.get("id", "unknown")
            if snapshot_id in seen_snapshot_ids:
                print(f"ERROR: Duplicate snapshot id for {election_id}: {snapshot_id}")
                all_valid = False
            seen_snapshot_ids.add(snapshot_id)

            if "/" in str(snapshot_id):
                print(f"ERROR: Snapshot {election_id}/{snapshot_id} must not contain '/'. Use scoped IDs as electionId/snapshotId/layerId outside snapshot id fields")
                all_valid = False
            if snapshot_id == election_id or str(snapshot_id).startswith(f"{election_id}-"):
                print(f"ERROR: Snapshot {election_id}/{snapshot_id} includes the election id prefix. Snapshot ids must be concise and local to the election")
                all_valid = False

            has_snapshot_layers = bool(snapshot.get("layers"))
            has_snapshot_legacy = _has_legacy_area_fields(snapshot)

            if has_snapshot_layers and has_snapshot_legacy:
                print(f"ERROR: Snapshot {election_id}/{snapshot_id} defines both layers and legacy area fields; choose exactly one mode")
                all_valid = False
            elif not has_snapshot_layers and not has_snapshot_legacy:
                print(f"ERROR: Snapshot {election_id}/{snapshot_id} defines neither complete legacy area fields nor layers")
                all_valid = False

            if has_parent_layers and has_snapshot_layers:
                print(f"WARNING: Snapshot {election_id}/{snapshot_id} has layers while parent election also has layers; snapshot layers should be treated as authoritative")

            for key in ["dataUrl", "areasUrl"]:
                if key in snapshot:
                    url = snapshot[key]
                    exists = _check_url(repo_root, file_checks, f"{election_id}/{snapshot_id}", key, url)
                    if not exists:
                        print(f"ERROR: Missing snapshot file: {url}")
                        all_valid = False
            snapshot_layers = snapshot.get("layers", [])
            if snapshot_layers:
                if not _validate_layers(repo_root, f"{election_id}/{snapshot_id}", snapshot_layers, file_checks):
                    all_valid = False
    
    # Summary
    total_files = len(file_checks)
    valid_files = sum(1 for _, _, _, exists in file_checks if exists)
    print(f"\nValidation Summary: {valid_files}/{total_files} files found")
    
    if all_valid:
        print("All index paths are valid.")
        return True
    else:
        print("Some paths are missing or invalid")
        return False


if __name__ == "__main__":
    success = validate_index()
    sys.exit(0 if success else 1)
