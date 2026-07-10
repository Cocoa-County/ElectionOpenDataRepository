# JSON Schema Contracts

This repository includes JSON Schema files for the primary published data contracts:

- `schemas/elections.index.schema.json`
- `schemas/election.schema.json`
- `schemas/precincts.gis.schema.json`
- `schemas/metadata.schema.json`

These schemas are aligned to the CocoaCountyMap specification documents referenced by this repository:

- `https://github.com/Cocoa-County/CocoaCountyMap/blob/main/election-data-repository-design.md`
- `https://github.com/Cocoa-County/CocoaCountyMap/blob/main/dataSpecification.md`

## Scope and Notes

- `elections.index.schema.json` enforces required app-compatibility fields and supports optional snapshot metadata used by this repository.
- `election.schema.json` models the `data.json` contract used by CocoaCountyMap and this repository's `election.json` files.
- `precincts.gis.schema.json` validates GeoJSON structure. Cross-file checks are intentionally out of scope for JSON Schema alone.
- `metadata.schema.json` supports both historical minimal metadata (`schemaVersion`, `generated`) and newer metadata with `electionId`, `source`, and `run` fields.

Cross-file integrity checks should continue to be handled by repository validators such as `tools/validate_index_paths.py`.