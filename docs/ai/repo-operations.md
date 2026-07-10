# Repository Operations Guide

This document describes repository-specific operational practices.

It is intentionally separate from the public data contract.

## Purpose

Use this guide for local maintenance, migration, and quality checks in this repository.

Do not treat this guide as a requirement for third-party data producers or consumers.

## Operational Checks

1. Path consistency checks can be run with local validators such as `tools/validate_index_paths.py`.
2. Additional repository checks may be added over time without changing the public data contract.

## Contract Boundary

1. Public contract requirements are documented in `docs/ai/data-spec-core.md` and JSON Schemas under `schemas/`.
2. Repository scripts, workflows, and local validation tooling are implementation details.
