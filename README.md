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

## Data Contract Notes

- `elections.index.json` supports both relative and absolute URLs.
- Relative paths resolve from the index file location.
- `defaultElectionId` should match an election `id` in the `elections` array.
- Every `election.id` should be unique.
- GeoJSON properties should include `precinctIdField` values that match keys in `election.json`.
