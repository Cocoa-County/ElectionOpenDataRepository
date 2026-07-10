# Election Open Data Repository

This repository is structured for static hosting on GitHub Pages and consumption by election map applications.

## Structure

- `elections.index.json`: Machine-readable index of all elections.
- `elections/ca/<county>/<election-id>/election.json`: Legacy election results and contest data.
- `elections/ca/<county>/<election-id>/results.<geography>.json`: Geography-specific results and contest data.
- `elections/ca/<county>/<election-id>/precincts.gis.json`: Legacy or precinct geography GeoJSON.
- `elections/ca/<county>/<election-id>/<geography>.gis.json`: Geography-specific boundary GeoJSON.
- `elections/ca/<county>/<election-id>/metadata.json`: Optional metadata extensions.
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

Quick implementer path:

- Core public spec: `docs/ai/data-spec-core.md`
- Schema profile summary: `docs/ai/json-schema.md`

- Canonical index URL pattern: `https://<org>.github.io/<repo>/elections.index.json`
- Example for this repository: `https://cocoa-county.github.io/ElectionOpenDataRepository/elections.index.json`
- Example election data URL: `https://cocoa-county.github.io/ElectionOpenDataRepository/elections/ca/contra_costa/2024-11-05-general/election.json`

Consumers should read index entries and resolve any relative `dataUrl`, `precinctsUrl`, `gisUrl`, or `metadataUrl` values from the index location.

Consumer quick start:

1. Fetch `elections.index.json`.
2. Pick an election entry by `id`.
3. Select a layer from `layers` when present, otherwise use the legacy precinct fields.
4. Load the selected results file and GIS file.
5. Join GIS feature identifiers to `contest.areas` or `contest.precincts` keys.
6. Optionally load `metadataUrl`.

## Data Contract Notes

Specification scope is limited to published data artifacts and schema contracts. Repository tooling, scripts, and deployment workflows are implementation details and are not required for third-party implementations.

- `elections.index.json` supports both relative and absolute URLs.
- Relative paths resolve from the index file location.
- `defaultElectionId` should match an election `id` in the `elections` array.
- Every `election.id` should be unique.
- GeoJSON properties should include the declared join field values that match keys in the paired results file.

## JSON Schemas

The repository now includes JSON Schema definitions under `schemas/`:

- `schemas/elections.index.schema.json`
- `schemas/election.schema.json`
- `schemas/precincts.gis.schema.json`
- `schemas/metadata.schema.json`

The index and election schemas now support additive multi-layer publication. New producers should prefer `layers` plus `results.<geography>.json` and `<geography>.gis.json`, while existing precinct-only artifacts remain valid.

For implementation details, use:

- Core public data contract: `docs/ai/data-spec-core.md`
- Schema profile notes: `docs/ai/json-schema.md`
- Repository-only operations: `docs/ai/repo-operations.md`

## Snapshot Versioning

This repository now supports multiple timestamped versions of the same election to track results over time.

- Use a stable election group field: `electionGroupId`.
- Use a per-snapshot timestamp field: `resultsTimestamp` (ISO datetime).
- Add multiple election entries in `elections.index.json` that share the same `electionGroupId` but have different `id`, `dataUrl`, and `resultsTimestamp` values.
- If multiple snapshots use the same GIS file for a geography view, store one shared `<geography>.gis.json` at the election root and point snapshot metadata or index entries at that shared file.

## Troubleshooting

- **Index loads, but election file URLs fail**: Confirm your consumer resolves relative URLs from the index file location, not from another base path.
- **Missing metadata warning**: Some `metadata.json` files are optional and may be absent by design.
- **Unexpected 404 on GitHub Pages**: Verify GitHub Pages is enabled for the `main` branch root and that the latest workflow run completed successfully.
- **Path consistency checks**: Repository-specific checks are documented in `docs/ai/repo-operations.md`.
