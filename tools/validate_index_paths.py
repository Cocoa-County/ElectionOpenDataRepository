#!/usr/bin/env python3
"""
Validate that all paths in elections.index.json resolve to existing files.
This ensures the migration was successful.
"""

import json
from pathlib import Path
import sys


LEGACY_FIELDS = ["dataUrl", "areasUrl", "areaIdField", "areaLabelField"]


def _check_url(repo_root: Path, file_checks: list[tuple[str, str, str, bool]], owner_id: str, key: str, url: str) -> bool:
    file_path = repo_root / url
    exists = file_path.exists()
    file_checks.append((owner_id, key, url, exists))
    return exists


def _validate_layers(repo_root: Path, owner_id: str, layers: list[dict], file_checks: list[tuple[str, str, str, bool]]) -> bool:
    all_valid = True
    for layer in layers:
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


def validate_index(repo_root: Path | None = None):
    """Check all index entries and paths."""
    if repo_root is None:
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

        if "layers" in election:
            print(f"ERROR: Election {election_id} defines election-level layers. Use snapshot layers instead.")
            all_valid = False

        legacy_on_election = [key for key in LEGACY_FIELDS if key in election]
        if legacy_on_election:
            print(f"ERROR: Election {election_id} uses unsupported legacy fields: {', '.join(legacy_on_election)}")
            all_valid = False

        snapshots = election.get("snapshots", [])
        if not snapshots:
            print(f"ERROR: Election {election_id} has no snapshots. At least one snapshot is required.")
            all_valid = False
        
        layers = election.get("layers", [])
        if layers and not _validate_layers(repo_root, election_id, layers, file_checks):
            all_valid = False
        
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

            legacy_on_snapshot = [key for key in LEGACY_FIELDS if key in snapshot]
            if legacy_on_snapshot:
                print(f"ERROR: Snapshot {election_id}/{snapshot_id} uses unsupported legacy fields: {', '.join(legacy_on_snapshot)}")
                all_valid = False

            snapshot_layers = snapshot.get("layers", [])
            if not snapshot_layers:
                print(f"ERROR: Snapshot {election_id}/{snapshot_id} must define at least one layer")
                all_valid = False
                continue

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
