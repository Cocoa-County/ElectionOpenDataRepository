# ArcGIS Endpoint Scraper

This tool scrapes ArcGIS FeatureServer layer data and outputs a GeoJSON FeatureCollection.

## Usage

```bash
node scrape.js -u "https://services1.arcgis.com/.../FeatureServer/0" -o scrape.json -d
```

If an endpoint is blocked in Node HTTP clients but works in a real browser session,
use the browser scraper:

```bash
node scrape-browser.js -u "https://services1.arcgis.com/.../FeatureServer/0" -o scrape.json -d
```

## Options

- `-u`, `--url` (required): ArcGIS layer URL ending in `/FeatureServer/<layerId>`
- `-o`, `--output`: Output file path (default: `scrape.json`)
- `-d`, `--debug`: Enable verbose logging
- `--header`: Additional request header in `Name: Value` format (repeatable)
- `--cookie`: Full `Cookie` header value for endpoints protected by WAF/CDN challenges

## Pagination Strategy

The scraper does not assume object IDs start at 0 or 1.

1. It fetches layer metadata (`maxRecordCount`, `objectIdField`).
2. It paginates with `resultOffset` and `resultRecordCount`, ordered by the detected object ID field.
3. If offset paging is incomplete or unsupported, it falls back to:
	- `returnIdsOnly=true`
	- chunked `IN (...)` ID queries

This handles sparse/non-contiguous IDs and preserves features with `geometry: null`.

## 403 Troubleshooting

Some county ArcGIS services are behind web application firewalls that block generic
HTTP clients and return an HTML 403 page. The scraper now sends browser-like
default headers (`User-Agent`, `Accept`, `Referer`, `Origin`) on every request.

When `--debug` is enabled and a request fails, the scraper prints:

- HTTP status and status text
- response `content-type`
- a short response body preview

This makes it easier to distinguish ArcGIS JSON errors from WAF/proxy HTML blocks.

If the response is a Cloudflare challenge page, scrape requests may require browser
clearance cookies. You can pass these explicitly:

```bash
node scrape.js -d \
	-u "https://.../FeatureServer/0" \
	--cookie "cf_clearance=...; __cf_bm=..." \
	--header "Referer: https://gis.marincounty.gov/" \
	-o precincts.gis.json
```

If browser access works but CLI requests still return Cloudflare HTML, the endpoint
is likely enforcing browser/TLS fingerprint checks. In that case, this scraper may
not be able to access the service directly from Node HTTP clients.

## Browser Automation Mode

`scrape-browser.js` fetches ArcGIS data from an actual Chrome page context.
This is useful when WAF/CDN checks block Node and curl traffic.

### Browser Mode Options

- `-u`, `--url` (required): ArcGIS layer URL ending in `/FeatureServer/<layerId>`
- `-o`, `--output`: Output file path (default: `scrape.json`)
- `-d`, `--debug`: Enable verbose logging
- `--headless`: Run browser headless (often blocked by WAF)
- `--profileDir`: Persistent Chrome profile path for cookie/session reuse
- `--manual` (default `true`): Allow manual challenge solve before retry

### Marin Example

```bash
node scrape-browser.js -d \
	-u "https://gis.marincounty.gov/server/rest/services/Elections/CONSOLIDATED_PRECINCT/FeatureServer/0" \
	-o precincts.gis.json \
	--profileDir .browser-profile-marin
```

If Cloudflare appears, complete the challenge in the opened browser window,
then return to terminal and press Enter.
