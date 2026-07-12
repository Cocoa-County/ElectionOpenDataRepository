# Election Open Data Repository

This repository is structured for static hosting on GitHub Pages and consumption by election map applications.

## Structure

- `elections.index.json`: Machine-readable index of all elections.
- `elections/ca/<county>/<election-id>/election.json`: Election results and contest data.
- `elections/ca/<county>/<election-id>/results.<geography>.json`: Geography-specific results and contest data.
- `elections/ca/<county>/<election-id>/precincts.gis.json`: Area geography GeoJSON, including precinct boundaries.
- `elections/ca/<county>/<election-id>/<geography>.gis.json`: Geography-specific boundary GeoJSON.
- `elections/ca/<county>/<election-id>/metadata.json`: Optional metadata extensions.
- `elections/ca/<county>/<election-id>/snapshots/<timestamp-id>/`: Timestamped election data snapshots.

## Current Imported Datasets

- Election ID: `ca-contracosta-2024-11-05-general`
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

Quick implementer path:

- Core public spec: `docs/data-spec-core.md`
- Schema profile summary: `docs/json-schema.md`
- Repository operations and validation commands: `docs/repo-operations.md`

- Canonical index URL pattern: `https://<org>.github.io/<repo>/elections.index.json`
- Example for this repository: `https://cocoa-county.github.io/ElectionOpenDataRepository/elections.index.json`
- Example election data URL: `https://cocoa-county.github.io/ElectionOpenDataRepository/elections/ca/contra_costa/2024-11-05-general/election.json`

Consumers should read index entries and resolve relative layer URLs (`dataUrl`, `gisUrl`, and optional `metadataUrl`) from the index location.

Consumer flow is maintained in one place to avoid doc drift:

- Core consumer flow: `docs/data-spec-core.md` (`Core Consumer Flow` section)
- Snapshots are layers-only.

## Data Contract Notes

Specification scope is limited to published data artifacts and schema contracts. Repository tooling, scripts, and deployment workflows are implementation details and are not required for third-party implementations.

- `elections.index.json` supports both relative and absolute URLs.
- Relative paths resolve from the index file location.
- `defaultElectionId` should match an election `id` in the `elections` array.
- Every `election.id` should be unique.
- Recommended election `id` format: `{state-abbr}-{county-or-jurisdiction}-{yyyy-mm-dd}-{election-type}`.
- Snapshot `id` values are scoped to a single election and should not include election id prefixes.
- Layer `id` values are scoped to a single snapshot.
- Use a composite identifier outside fields as `electionId/snapshotId/layerId`.
- GeoJSON properties should include the declared join field values that match keys in the paired results file.

## JSON Schemas

The repository now includes JSON Schema definitions under `schemas/`:

- `schemas/elections.index.schema.json`
- `schemas/election.schema.json`
- `schemas/gis.schema.json`
- `schemas/metadata.schema.json`

The index and election schemas support snapshot-first multi-layer publication where layers are defined per snapshot and can vary by timestamp.

Validation entry points:

- Create local virtual environment once: `python -m venv .venv`
- Install validator dependency: `.venv\Scripts\python -m pip install -r tools/requirements.txt`
- `.venv\Scripts\python tools/validate_index_paths.py`
- `.venv\Scripts\python tools/validate_schemas.py`
- Validate specific files only: `.venv\Scripts\python tools/validate_schemas.py --file elections/ca/contra_costa/2026-06-02-primary/election.json`
- Enable progress logging: `.venv\Scripts\python tools/validate_schemas.py --verbose`
- Limit error volume during large runs: `.venv\Scripts\python tools/validate_schemas.py --max-errors-per-file 10 --max-total-errors 100`

For implementation details, use:

- Core public data contract: `docs/data-spec-core.md`
- Schema profile notes: `docs/json-schema.md`
- Repository-only operations: `docs/repo-operations.md`

## Snapshot Versioning

This repository now supports multiple timestamped versions of the same election to track results over time.

- Use a per-snapshot timestamp field: `resultsTimestamp` (ISO datetime).
- Add multiple snapshots under one election entry using unique `id` values and distinct `resultsTimestamp` values.
- If multiple snapshots use the same GIS file for a geography view, store one shared `<geography>.gis.json` at the election root and point snapshot metadata or index entries at that shared file.
- Snapshot layer sets are allowed to differ across timestamps.
- Snapshot `layers` are self-contained and replace parent election layers for snapshot rendering.

## Troubleshooting

- **Index loads, but election file URLs fail**: Confirm your consumer resolves relative URLs from the index file location, not from another base path.
- **Missing metadata warning**: Some `metadata.json` files are optional and may be absent by design.
- **Unexpected 404 on GitHub Pages**: Verify GitHub Pages is enabled for the `main` branch root and that the latest workflow run completed successfully.
- **Path consistency checks**: Repository-specific checks are documented in `docs/repo-operations.md`.

