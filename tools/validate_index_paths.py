#!/usr/bin/env python3
"""
Validate that all paths in elections.index.json resolve to existing files.
This ensures the migration was successful.
"""

import json
from pathlib import Path
import sys


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
        
        # Check main dataUrl and precinctsUrl
        for key in ["dataUrl", "precinctsUrl"]:
            if key in election:
                url = election[key]
                file_path = repo_root / url
                exists = file_path.exists()
                file_checks.append((election_id, key, url, exists))
                if not exists:
                    print(f"ERROR: Missing file for {election_id} ({county}): {url}")
                    all_valid = False
        
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
        snapshots = election.get("snapshots", [])
        for snapshot in snapshots:
            snapshot_id = snapshot.get("id", "unknown")
            for key in ["dataUrl", "precinctsUrl"]:
                if key in snapshot:
                    url = snapshot[key]
                    file_path = repo_root / url
                    exists = file_path.exists()
                    file_checks.append((f"{election_id}/{snapshot_id}", key, url, exists))
                    if not exists:
                        print(f"ERROR: Missing snapshot file: {url}")
                        all_valid = False
    
    # Summary
    total_files = len(file_checks)
    valid_files = sum(1 for _, _, _, exists in file_checks if exists)
    print(f"\nValidation Summary: {valid_files}/{total_files} files found")
    
    if all_valid:
        print("✓ All index paths are valid!")
        return True
    else:
        print("✗ Some paths are missing or invalid")
        return False


if __name__ == "__main__":
    success = validate_index()
    sys.exit(0 if success else 1)
