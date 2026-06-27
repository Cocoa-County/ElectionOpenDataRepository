# Data Converter

This folder contains tools for converting and parsing Contra Costa election reporting files.

## Overview

The workflow is split into three layers:

1. XLSX sheet splitting
2. CSV parsing using YAML parser configs
3. End-to-end orchestration (download -> split -> parse -> write JSON)

## Main Scripts

- `data_converter.py`: unified command surface with subcommands `split`, `parse`, `pipeline`
- `splitxlsx.py`: compatibility shim and reusable split function
- `convert.py`: compatibility shim forwarding to `parse` subcommand
- `pipeline.py`: compatibility shim forwarding to `pipeline` subcommand

## Profiles

Profiles package parser YAML and examples by county and source format.

- `profiles/contra_costa/election_results_xlsx/results.yml`
- `profiles/contra_costa/election_results_xlsx/turnout_summary.yml`
- `profiles/contra_costa/election_results_xlsx/pipeline.yml.example`
- `profiles/contra_costa/election_results_xlsx/results.yml.example.json`
- `profiles/contra_costa/election_results_xlsx/turnout_summary.yml.example.json`

## Pipeline Config

Use `profiles/contra_costa/election_results_xlsx/pipeline.yml.example` as a template. It controls:

- input source defaults (`url` or `xlsx_path`)
- parser config references (`results`, `turnout`)
- per-sheet parser routing rules
- warning inclusion
- JSON formatting and null handling
- output behaviors (per-sheet JSON, manifest, summary-only)
- optional combined JSON output (single file containing all sheet payloads)
- optional output versioning with template-based subdirectories
- in-memory table mode by default (no split CSV files written)
- split CSV cleanup behavior

### Output Versioning

Pipeline output versioning is optional and configured under `io.versioning`.

When enabled:

- a version string is rendered from a template
- that version string becomes a subdirectory under the base output dir
- all generated files for the run are written into that versioned folder
- manifest includes run metadata describing the version settings used

Example config section:

```yaml
io:
	output_dir: "output"
	versioning:
		enabled: true
		template: "run_{run_utc:%Y%m%dT%H%M%SZ}_{source_kind}"
```

Supported template variables:

- `{run_utc}` with datetime formatting, for example `{run_utc:%Y%m%dT%H%M%SZ}`
- `{source_kind}` where value is `url` or `path`
- `{source_value}` full URL or local source path
- `{source_name}` filename-ish source token

Template output is sanitized for path safety.

## Pipeline Architecture

The orchestration code is modularized under `src/data_converter/pipeline/`:

- `src/data_converter/pipeline/config.py`: load/validate pipeline YAML and resolve runtime options
- `src/data_converter/pipeline/download.py`: XLSX download and basic file validation
- `src/data_converter/pipeline/routing.py`: select parser YAML per split CSV sheet
- `src/data_converter/pipeline/outputs.py`: per-sheet JSON and manifest writing
- `src/data_converter/pipeline/runner.py`: core orchestration flow
- `src/data_converter/pipeline/cli.py`: argument parsing and CLI output

Parser internals live under `src/data_converter/parser/`.

Split internals live under `src/data_converter/split/` and expose:

- `split_xlsx_to_csv(...)` for file output mode
- `split_xlsx_to_dataframes(...)` for in-memory DataFrame mode
- `split_xlsx_to_row_matrices(...)` for in-memory row-matrix mode

`pipeline.py` remains a compatibility entrypoint.

## Usage

### Unified CLI

1. Split XLSX to CSV

```powershell
python .\data_converter.py split --xlsx ..\..\raw\20260602_ContraCostaSOV_ByPCT_LVTP.xlsx --output-dir output\ --create-dirs
```

2. Parse one CSV

```powershell
python .\data_converter.py parse --config .\profiles\contra_costa\election_results_xlsx\results.yml --csv .\output\Sheet2.csv --output .\output\Sheet2.parsed.json
```

3. Run full pipeline from URL

```powershell
python .\data_converter.py pipeline --config .\profiles\contra_costa\election_results_xlsx\pipeline.yml.example --summary-only
```

4. Run full pipeline with the profile defaults (combined JSON + manifest)

```powershell
python .\data_converter.py pipeline --config .\profiles\contra_costa\election_results_xlsx\pipeline.yml.example
```

5. Run pipeline with versioned output subdirectory

```powershell
python .\data_converter.py pipeline --config .\profiles\contra_costa\election_results_xlsx\pipeline.yml.example --output-versioning --output-version-template "run_{run_utc:%Y%m%dT%H%M%SZ}"
```

6. Run pipeline fully in memory (default behavior)

```powershell
python .\data_converter.py pipeline --config .\profiles\contra_costa\election_results_xlsx\pipeline.yml.example --in-memory-tables --table-representation rows
```

7. Run pipeline with only one combined JSON output file

```powershell
python .\data_converter.py pipeline --config .\profiles\contra_costa\election_results_xlsx\pipeline.yml.example --write-combined-json --combined-name output.json --no-write-sheet-json --no-write-manifest
```

Current profile default outputs:

- `output.json` (combined per-sheet payloads)
- `manifest.json` (run metadata and per-sheet status)

### Compatibility shims

- `splitxlsx.py` still supports direct split execution.
- `convert.py` forwards arguments to `data_converter.py parse`.
- `pipeline.py` forwards arguments to `data_converter.py pipeline`.

## Common Flags (pipeline)

- `--url`: override URL input from config
- `--xlsx`: override local XLSX input from config
- `--output-dir`: override output directory
- `--summary-only`: skip writing JSON files
- `--write-sheet-json` / `--no-write-sheet-json`
- `--write-combined-json` / `--no-write-combined-json`
- `--combined-name`: filename for combined JSON output
- `--write-manifest` / `--no-write-manifest`
- `--in-memory-tables` / `--no-in-memory-tables`
- `--table-representation`: `rows` or `dataframe`
- `--keep-split-csv` / `--delete-split-csv`
- `--output-versioning` / `--no-output-versioning`
- `--output-version-template`: template for version subdirectory
- `--omit-nulls`: remove null-valued keys in JSON output
- `--timeout`: download timeout in seconds

## Notes

- Parser dict outputs always keep full schema; null omission only affects JSON serialization output.
- Pipeline handles per-sheet parse failures and reports them in the manifest instead of aborting the entire run.
- Default output location for generated files is the repository root `output/` directory unless overridden.
- Manifest includes run details such as duration, base output dir, resolved output dir, and versioning settings.
- Manifest settings include whether in-memory table mode was used and which table representation was selected.
- In-memory table processing is enabled by default unless disabled with `--no-in-memory-tables` or `io.tables.in_memory: false`.
- Combined JSON output writes a top-level `sheets` object keyed by sheet name.
