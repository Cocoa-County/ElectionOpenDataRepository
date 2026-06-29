# ArcGIS Endpoint Scraper

This tool scrapes ArcGIS FeatureServer layer data and outputs a GeoJSON FeatureCollection.

## Usage

```bash
node scrape.js -u "https://services1.arcgis.com/.../FeatureServer/0" -o scrape.json -d
```

## Options

- `-u`, `--url` (required): ArcGIS layer URL ending in `/FeatureServer/<layerId>`
- `-o`, `--output`: Output file path (default: `scrape.json`)
- `-d`, `--debug`: Enable verbose logging

## Pagination Strategy

The scraper does not assume object IDs start at 0 or 1.

1. It fetches layer metadata (`maxRecordCount`, `objectIdField`).
2. It paginates with `resultOffset` and `resultRecordCount`, ordered by the detected object ID field.
3. If offset paging is incomplete or unsupported, it falls back to:
	- `returnIdsOnly=true`
	- chunked `IN (...)` ID queries

This handles sparse/non-contiguous IDs and preserves features with `geometry: null`.
