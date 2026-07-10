# JSON Schema Contracts

This project publishes JSON Schema files for a tool-agnostic election data format.

## Core Profile

The Core Profile is the minimum needed for interoperability. A publisher can be compliant without adopting this repository layout, scripts, or workflows.

- `schemas/elections.index.schema.json`
- `schemas/election.schema.json`
- `schemas/precincts.gis.schema.json`

Core rules:

- Consumers read `elections.index.json` as the entry point.
- Legacy entries use `dataUrl` and `precinctsUrl` to identify election data and precinct GeoJSON resources.
- Geography-aware entries use `geographies[*].dataUrl` and `geographies[*].gisUrl` to identify one switchable map view at a time.
- Consumers must ignore unknown fields.

## Geography-Aware Additions

The schemas now support an additive generalized geography model.

- `schemas/elections.index.schema.json` accepts a `geographies` array on election entries and snapshots.
- Each geography item declares a `joinField` so joins are data-driven rather than precinct-specific.
- `schemas/election.schema.json` accepts legacy `contest.precincts` and generalized `contest.areas`.
- A results file may include a top-level `geography` object so it remains self-describing even when opened without the index.

Recommended producer layout for new geography views:

- `results.precincts.json` with `precincts.gis.json`
- `results.places.json` with `places.gis.json`
- `results.supervisor_districts.json` with `supervisor_districts.gis.json`

## Extended Profile (Optional)

- `schemas/metadata.schema.json`

`metadata.json` is optional. It has a minimal core (`schemaVersion`, `generated`) plus optional extensions such as `electionId`, `source`, and `run`. Those extension fields are publisher-supplied and are not required for core consumers.

## Notes

- Schemas are additive-friendly and allow unknown properties for compatibility.
- GeoJSON validation in `precincts.gis.schema.json` focuses on structural conformance and can be reused for non-precinct geometry views.
- Cross-file integrity behavior is implementation-specific and intentionally outside the core data contract.

## Required vs Ignorable

For easiest interoperability, implementers can use this rule:

1. Enforce required fields defined by each core schema.
2. Treat non-required fields as optional.
3. Ignore unknown fields.

Examples of commonly ignorable fields for core consumers:

- `metadataUrl` in index entries
- `geographies` in legacy precinct-only consumers that intentionally support one view only
- `source` and `run` objects in metadata
- snapshot-specific descriptive tags that are not required by schema