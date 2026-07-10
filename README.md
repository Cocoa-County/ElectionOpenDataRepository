# Election Open Data Repository

This repository is structured for static hosting on GitHub Pages and consumption by election map applications.

## Structure

- `elections.index.json`: Machine-readable index of all elections.
- `elections/ca/<county>/<election-id>/election.json`: Election results and contest data.
- `elections/ca/<county>/<election-id>/precincts.gis.json`: Precinct boundary GeoJSON.
- `elections/ca/<county>/<election-id>/metadata.json`: Optional metadata and source details.
- `elections/ca/<county>/<election-id>/snapshots/<timestamp-id>/`: Timestamped election data snapshots.

## Current Imported Datasets

- Election ID: `2024-11-05-general`
- County: Contra Costa
- Data file: `elections/ca/contra_costa/2024-11-05-general/election.json`
- Precinct file: `elections/ca/contra_costa/2024-11-05-general/precincts.gis.json`
- Source: `https://github.com/Cocoa-County/CocoaCountyMap` (`public/data`)

## GitHub Pages Hosting

1. In repository settings, enable GitHub Pages from the `main` branch root.
2. Your index URL will be:
   `https://<org>.github.io/<repo>/elections.index.json`

## Data Access

Use `elections.index.json` as the canonical entry point for all consumers.

- Canonical index URL pattern: `https://<org>.github.io/<repo>/elections.index.json`
- Example for this repository: `https://cocoa-county.github.io/ElectionOpenDataRepository/elections.index.json`
- Example election data URL: `https://cocoa-county.github.io/ElectionOpenDataRepository/elections/ca/contra_costa/2024-11-05-general/election.json`

Consumers should read index entries and resolve any relative `dataUrl`, `precinctsUrl`, or `metadataUrl` values from the index location.

## Data Contract Notes

- `elections.index.json` supports both relative and absolute URLs.
- Relative paths resolve from the index file location.
- `defaultElectionId` should match an election `id` in the `elections` array.
- Every `election.id` should be unique.
- GeoJSON properties should include `precinctIdField` values that match keys in `election.json`.

## Snapshot Versioning

This repository now supports multiple timestamped versions of the same election to track results over time.

- Use a stable election group field: `electionGroupId`.
- Use a per-snapshot timestamp field: `resultsTimestamp` (ISO datetime).
- Add multiple election entries in `elections.index.json` that share the same `electionGroupId` but have different `id`, `dataUrl`, and `resultsTimestamp` values.
- If multiple snapshots use the same precinct GeoJSON, store one shared `precincts.gis.json` at the election root and point snapshot metadata or index entries at that shared file.

## Troubleshooting

- **Index loads, but election file URLs fail**: Confirm your consumer resolves relative URLs from the index file location, not from another base path.
- **Missing metadata warning**: Some `metadata.json` files are optional and may be absent by design.
- **Unexpected 404 on GitHub Pages**: Verify GitHub Pages is enabled for the `main` branch root and that the latest workflow run completed successfully.
- **Path consistency checks**: Run `python tools/validate_index_paths.py` to verify that index references resolve to files in the repository.
