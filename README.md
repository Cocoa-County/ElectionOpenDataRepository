# Election Open Data Repository

This repository is structured for static hosting on GitHub Pages and consumption by election map applications.

## Structure

- `elections.index.json`: Machine-readable index of all elections.
- `elections/<election-id>/election.json`: Election results and contest data.
- `elections/<election-id>/precincts.gis.json`: Precinct boundary GeoJSON.
- `elections/<election-id>/metadata.json`: Optional metadata and source details.

## Current Imported Dataset

- Election ID: `2024-11-05-general`
- Data file: `elections/2024-11-05-general/election.json`
- Precinct file: `elections/2024-11-05-general/precincts.gis.json`
- Source: `https://github.com/Cocoa-County/CocoaCountyMap` (`public/data`)

## GitHub Pages Hosting

1. In repository settings, enable GitHub Pages from the `main` branch root.
2. Your index URL will be:
   `https://<org>.github.io/<repo>/elections.index.json`
3. Explore data at:
   `https://cocoa-county.github.io/ElectionOpenDataRepository/`

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
- In the static explorer, select an election, then switch versions from the `Version` dropdown to compare counts over time.
