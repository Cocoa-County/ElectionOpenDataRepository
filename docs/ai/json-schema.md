# JSON Schema Contracts

This project publishes JSON Schema files for a tool-agnostic election data format.

## Core Profile

The Core Profile is the minimum needed for interoperability. A publisher can be compliant without adopting this repository layout, scripts, or workflows.

- `schemas/elections.index.schema.json`
- `schemas/election.schema.json`
- `schemas/precincts.gis.schema.json`

Core rules:

- Consumers read `elections.index.json` as the entry point.
- `dataUrl` and `precinctsUrl` identify the election data and precinct GeoJSON resources.
- Consumers must ignore unknown fields.

## Extended Profile (Optional)

- `schemas/metadata.schema.json`

`metadata.json` is optional. It has a minimal core (`schemaVersion`, `generated`) plus optional extensions such as `electionId`, `source`, and `run`. Those extension fields are publisher-supplied and are not required for core consumers.

## Notes

- Schemas are additive-friendly and allow unknown properties for compatibility.
- GeoJSON validation in `precincts.gis.schema.json` focuses on structural conformance.
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