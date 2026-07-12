# JSON Schema Contracts

This project publishes JSON Schema files for a tool-agnostic election data format.

## Core Profile

The Core Profile is the minimum needed for interoperability. A publisher can be compliant without adopting this repository layout, scripts, or workflows.

- `schemas/elections.index.schema.json`
- `schemas/election.schema.json`
- `schemas/gis.schema.json`

Core rules:

- Consumers read `elections.index.json` as the entry point.
- Recommended election `id` format is `{state-abbr}-{county-or-jurisdiction}-{yyyy-mm-dd}-{election-type}`.
- Layer-aware snapshots use `layers[*].dataUrl` and `layers[*].gisUrl` to identify one switchable map view at a time.
- Consumers must ignore unknown fields.

## Layer-Aware Additions

The schemas now support an additive generalized layer model.

- `schemas/elections.index.schema.json` requires snapshots on election entries and supports `layers` on snapshots.
- Each layer item declares a `joinField` so joins are data-driven and geography-agnostic.
- `schemas/election.schema.json` uses `contest.areas` for area-keyed results.
- A results file may include a top-level `geography` object so it remains self-describing even when opened without the index.
- Snapshot layer sets may differ across timestamps of the same election group.
- A snapshot publishes one or more `layers`.
- Snapshot `layers` are self-contained and do not inherit parent election layers.
- Snapshot ids are election-local and layer ids are snapshot-local; compose full references as `electionId/snapshotId/layerId`.

Recommended producer layout for new map layers:

- `results.precincts.json` with `precincts.gis.json`
- `results.places.json` with `places.gis.json`
- `results.supervisor_districts.json` with `supervisor_districts.gis.json`

## Extended Profile (Optional)

- `schemas/metadata.schema.json`

`metadata.json` is optional. It has a minimal core (`schemaVersion`, `generated`) plus optional extensions such as `electionId`, `source`, and `run`. Those extension fields are publisher-supplied and are not required for core consumers.

## Notes

- Schemas are additive-friendly and allow unknown properties for compatibility.
- GeoJSON validation in `gis.schema.json` focuses on structural conformance and can be reused across area geometry views.
- Cross-file integrity behavior is implementation-specific and intentionally outside the core data contract.

## Required vs Ignorable

For easiest interoperability, implementers can use this rule:

1. Enforce required fields defined by each core schema.
2. Treat non-required fields as optional.
3. Ignore unknown fields.

Examples of commonly ignorable fields for core consumers:

- `metadataUrl` in index entries
- `source` and `run` objects in metadata
- snapshot-specific descriptive tags that are not required by schema
