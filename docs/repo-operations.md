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
- Snapshots publish exactly one mode (`layers` or complete legacy area fields).
- Election-level `layers` are flagged as repository-invalid.

2. Schema checks:

```powershell
.venv\Scripts\python tools/validate_schemas.py
```

What it verifies:

- `elections.index.json` validates against `schemas/elections.index.schema.json`.
- Local referenced JSON artifacts validate against matching schemas:
	- `*.gis.json` -> `schemas/precincts.gis.schema.json`
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
