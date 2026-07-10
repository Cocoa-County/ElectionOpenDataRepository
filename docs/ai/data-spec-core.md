# Core Data Specification

This document defines the minimum public contract for election data exchange.

The specification is data-shape oriented and implementation-neutral.

## Required Artifacts

1. `elections.index.json`
2. At least one election results document referenced by `dataUrl` or by a geography view `dataUrl`
3. At least one GIS GeoJSON document referenced by `precinctsUrl` or by a geography view `gisUrl`

Optional artifact:

1. `metadata.json` referenced by `metadataUrl`

## Core Rules

1. `elections.index.json` is the canonical entry point.
2. Each election entry must include:
   1. `id`
   2. `label`
   3. Either the legacy precinct fields `dataUrl`, `precinctsUrl`, `precinctIdField`, and `precinctLabelField`, or a `geographies` array
3. Each `geographies` item must include:
   1. `id`
   2. `type`
   3. `label`
   4. `dataUrl`
   5. `gisUrl`
   6. `joinField`
4. `dataUrl`, `precinctsUrl`, `gisUrl`, and `metadataUrl` may be absolute URLs or relative paths.
5. Consumers resolve relative paths from the location of `elections.index.json`.
6. Consumers must ignore unknown fields.

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
   Publishes index, election results, and precinct GIS documents that validate against core schemas.
2. Core Consumer:
   Reads required core fields and safely ignores unknown fields.

## Minimal Examples

### Example `elections.index.json`

```json
{
   "version": 1,
   "updated": "2026-07-09",
   "defaultElectionId": "2026-06-02-primary",
   "elections": [
      {
         "id": "2026-06-02-primary",
         "label": "June 2, 2026 Primary",
         "dataUrl": "elections/ca/example/2026-06-02-primary/election.json",
         "precinctsUrl": "elections/ca/example/2026-06-02-primary/precincts.gis.json",
         "metadataUrl": "elections/ca/example/2026-06-02-primary/metadata.json",
         "precinctIdField": "precinct_id",
         "precinctLabelField": "precinct_name",
         "geographies": [
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
         "precincts": {
            "p-001": {
               "label": "Precinct 001",
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
5. If using `geographies`, ensure each geography `joinField` matches both GIS properties and results keys.
6. Confirm your consumer ignores unknown fields.

## Core Consumer Flow

Use this minimal flow in any language:

1. Fetch and parse `elections.index.json`.
2. Select an election entry by `defaultElectionId` or a caller-provided `id`.
3. If `geographies` is present, select a geography view by `id` or `type`; otherwise use the legacy precinct fields.
4. Resolve `dataUrl` and `precinctsUrl` or the selected geography `dataUrl` and `gisUrl` relative to the index location when needed.
5. Fetch and parse election results and the selected GIS GeoJSON file.
6. Read feature identifier values from GeoJSON using `joinField` or `precinctIdField`.
7. Join GeoJSON identifiers to `contest.areas` or `contest.precincts` keys from results data.
8. If `metadataUrl` exists, fetch it as optional context only.
9. Ignore unknown fields in all documents.
