# Core Data Specification

This document defines the minimum public contract for election data exchange.

The specification is data-shape oriented and implementation-neutral.

## Required Artifacts

1. `elections.index.json`
2. At least one election results document referenced by `dataUrl` or by a geography view `dataUrl`
3. At least one GIS GeoJSON document referenced by `areasUrl` or by a geography view `gisUrl`

Optional artifact:

1. `metadata.json` referenced by `metadataUrl`

## Core Rules

1. `elections.index.json` is the canonical entry point.
2. Each election entry must include:
   1. `id`
   2. `label`
   3. `snapshots` with at least one snapshot
3. Each snapshot `layers` item must include:
   1. `id`
   2. `type`
   3. `label`
   4. `dataUrl`
   5. `gisUrl`
   6. `joinField`
4. `dataUrl`, `areasUrl`, `gisUrl`, and `metadataUrl` may be absolute URLs or relative paths.
5. Consumers resolve relative paths from the location of `elections.index.json`.
6. Consumers must ignore unknown fields.
7. A snapshot must be self-contained. It publishes exactly one mode:
   1. Legacy area fields: `dataUrl`, `areasUrl`, `areaIdField`, `areaLabelField`
   2. A `layers` array
8. If a snapshot has `layers`, consumers must use snapshot layers only and must not inherit parent election layers.
9. Snapshot `id` is local to an election, and layer `id` is local to a snapshot.
10. Use composite addressing outside the data fields as `electionId/snapshotId/layerId`.
11. Recommended election `id` format: `{state-abbr}-{county-or-jurisdiction}-{yyyy-mm-dd}-{election-type}`.

## File Contracts

1. Index contract: `schemas/elections.index.schema.json`
2. Election results contract: `schemas/election.schema.json`
3. Geography GIS contract: `schemas/precincts.gis.schema.json`
4. Optional metadata contract: `schemas/metadata.schema.json`

## Optional Metadata

`metadata.json` is optional for core interoperability.

When present, `metadata.json` requires:

1. `schemaVersion`
2. `generated`

Any additional metadata fields are optional extensions and may be ignored by consumers.

## Minimal Conformance Targets

1. Core Producer:
   Publishes index, election results, and area GIS documents that validate against core schemas.
2. Core Consumer:
   Reads required core fields and safely ignores unknown fields.

## Minimal Examples

### Example `elections.index.json`

```json
{
   "version": 1,
   "updated": "2026-07-09",
   "defaultElectionId": "ca-example-2026-06-02-primary",
   "elections": [
      {
         "id": "ca-example-2026-06-02-primary",
         "label": "June 2, 2026 Primary",
         "dataUrl": "elections/ca/example/2026-06-02-primary/election.json",
         "areasUrl": "elections/ca/example/2026-06-02-primary/precincts.gis.json",
         "metadataUrl": "elections/ca/example/2026-06-02-primary/metadata.json",
         "areaIdField": "precinct_id",
         "areaLabelField": "precinct_name",
         "layers": [
            {
               "id": "precincts",
               "type": "precinct",
               "label": "Precincts",
               "dataUrl": "elections/ca/example/2026-06-02-primary/results.precincts.json",
               "gisUrl": "elections/ca/example/2026-06-02-primary/precincts.gis.json",
               "joinField": "precinct_id",
               "labelField": "precinct_name"
            },
            {
               "id": "places",
               "type": "place",
               "label": "Cities + Unincorporated",
               "dataUrl": "elections/ca/example/2026-06-02-primary/results.places.json",
               "gisUrl": "elections/ca/example/2026-06-02-primary/places.gis.json",
               "joinField": "place_name",
               "labelField": "place_name"
            },
            {
               "id": "supervisor_districts",
               "type": "supervisor_district",
               "label": "Supervisor Districts",
               "dataUrl": "elections/ca/example/2026-06-02-primary/results.supervisor_districts.json",
               "gisUrl": "elections/ca/example/2026-06-02-primary/supervisor_districts.gis.json",
               "joinField": "district_id",
               "labelField": "district_label"
            }
         ]
      }
   ]
}
```

### Example geography-aware `results.places.json`

```json
{
   "geography": {
      "id": "places",
      "type": "place",
      "label": "Cities + Unincorporated",
      "joinField": "place_name",
      "labelField": "place_name",
      "gisUrl": "elections/ca/example/2026-06-02-primary/places.gis.json"
   },
   "contests": [
      {
         "index": 0,
         "id": "president",
         "label": "President",
         "choices": [
            {
               "index": 0,
               "id": "cand-a",
               "label": "Candidate A",
               "votes": 120
            },
            {
               "index": 1,
               "id": "cand-b",
               "label": "Candidate B",
               "votes": 95
            }
         ],
         "areas": {
            "Walnut Creek": {
               "label": "Walnut Creek",
               "registeredVoters": 400,
               "totalVoters": 225,
               "results": [120, 95]
            }
         }
      }
   ]
}
```

### Example `election.json`

```json
{
   "contests": [
      {
         "index": 0,
         "id": "president",
         "label": "President",
         "choices": [
            {
               "index": 0,
               "id": "cand-a",
               "label": "Candidate A",
               "votes": 120
            },
            {
               "index": 1,
               "id": "cand-b",
               "label": "Candidate B",
               "votes": 95
            }
         ],
         "areas": {
            "p-001": {
               "label": "Area 001",
               "registeredVoters": 400,
               "totalVoters": 225,
               "results": [120, 95]
            }
         }
      }
   ]
}
```

### Example `precincts.gis.json`

```json
{
   "type": "FeatureCollection",
   "features": [
      {
         "type": "Feature",
         "properties": {
            "precinct_id": "p-001",
            "precinct_name": "Precinct 001"
         },
         "geometry": {
            "type": "Polygon",
            "coordinates": [
               [
                  [-122.52, 37.70],
                  [-122.50, 37.70],
                  [-122.50, 37.72],
                  [-122.52, 37.72],
                  [-122.52, 37.70]
               ]
            ]
         }
      }
   ]
}
```

### Example Optional `metadata.json`

```json
{
   "schemaVersion": 1,
   "generated": "2026-07-09",
   "electionId": "2026-06-02-primary"
}
```

## Fast Implementation Checklist

1. Publish `elections.index.json` at a stable URL.
2. Ensure every index election entry has required core fields.
3. Ensure declared join field values in GeoJSON match keys used by results.
4. Validate files against schemas.
5. If using `layers`, ensure each layer `joinField` matches both GIS properties and results keys.
6. Confirm your consumer ignores unknown fields.

## Core Consumer Flow

Use this minimal flow in any language:

1. Fetch and parse `elections.index.json`.
2. Select an election entry by `defaultElectionId` or a caller-provided `id`.
3. Select one snapshot by snapshot-local `id`, `snapshotTypes`, or `resultsTimestamp`.
4. If the selected snapshot has `layers`, select a layer by snapshot-local layer `id` or `type`.
5. If the selected snapshot does not have `layers`, use that snapshot's legacy area fields.
6. Resolve selected `dataUrl`, `areasUrl`, `gisUrl`, and `metadataUrl` relative to the index location when needed.
7. Fetch and parse election results and the selected GIS GeoJSON file.
8. Read feature identifier values from GeoJSON using `joinField` or `areaIdField`.
9. Join GeoJSON identifiers to `contest.areas` keys from results data.
10. If `metadataUrl` exists, fetch it as optional context only.
11. Ignore unknown fields in all documents.

