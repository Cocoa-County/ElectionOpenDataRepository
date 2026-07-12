# Repository Operations Guide

This document describes repository-specific operational practices.

It is intentionally separate from the public data contract.

## Purpose

Use this guide for local maintenance, migration, and quality checks in this repository.

Do not treat this guide as a requirement for third-party data producers or consumers.

## Operational Checks

Use the following repository maintenance checks during local updates and before pull requests.

Install validation dependencies once:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r tools/requirements.txt
```

1. Path and repository rule checks:

```powershell
.venv\Scripts\python tools/validate_index_paths.py
```

What it verifies:

- All local relative artifact paths referenced from `elections.index.json` resolve to existing files.
- Snapshot ids are unique per election.
- Snapshot ids do not include election id prefixes.
- Snapshots publish one or more `layers`.
- Election-level `layers` are flagged as repository-invalid.

2. Schema checks:

```powershell
.venv\Scripts\python tools/validate_schemas.py
```

Useful options for large repositories or targeted debugging:

```powershell
# Validate one or more specific files (repeat --file)
.venv\Scripts\python tools/validate_schemas.py --file elections/ca/marin/2026-06-02-primary/election.json --file elections/ca/marin/2026-06-02-primary/precincts.gis.json

# Show per-file progress and timing details
.venv\Scripts\python tools/validate_schemas.py --verbose

# Cap error volume so runs fail fast with actionable output
.venv\Scripts\python tools/validate_schemas.py --max-errors-per-file 10 --max-total-errors 100
```

What it verifies:

- `elections.index.json` validates against `schemas/elections.index.schema.json`.
- Local referenced JSON artifacts validate against matching schemas:
	- `*.gis.json` -> `schemas/gis.schema.json`
	- `metadata.json` -> `schemas/metadata.schema.json`
	- other referenced `*.json` results files -> `schemas/election.schema.json`

3. Optional test checks for validation tools:

```powershell
.venv\Scripts\python -m pytest tools/tests -v
```

4. Additional repository checks may be added over time without changing the public data contract.

## Contract Boundary

1. Public contract requirements are documented in `docs/data-spec-core.md` and JSON Schemas under `schemas/`.
2. Repository scripts, workflows, and local validation tooling are implementation details.
