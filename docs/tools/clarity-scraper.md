# Clarity Elections Scraper

Downloads raw Clarity JSON files into this subproject and transforms them into
repository `election.json` format.

Run commands in this guide from `tools/clarity_scraper` unless stated otherwise.

Validate transformed output against repository schemas:

```bash
../../.venv/Scripts/python ../validate_schemas.py
```

## Usage

```bash
node scrape.js \
	-u "https://results.enr.clarityelections.com/CA/Marin/126360" \
	-o "../../elections/ca/marin/2026-06-02-primary/election.json" \
	-d
```

## Options

- `-u`, `--url` (required): Clarity election root URL.
- `-o`, `--repo-output` (required): Repository output path for transformed `election.json`.
- `--raw-dir`: Subproject folder for raw downloads (default: `downloads`).
- `--lang`: Language code for Clarity localized files (default: `en`).
- `-d`, `--debug`: Print discovery/debug logging.

## How It Works

1. Reads `<url>/current_ver.txt` to discover the active data version.
2. Downloads raw Clarity files (`all.json`, `sum.json`, `electionsettings.json`) into:
	- `downloads/<state>/<county>/<electionId>/<version>/`
3. Transforms Clarity data into repository `election.json` structure.
4. Writes transformed output to the provided `--repo-output` path.
