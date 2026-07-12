from __future__ import annotations

from pathlib import Path

DEFAULT_JSON_INDENT = 2
DEFAULT_CSV_GLOB = "*.csv"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp" / "output"
DEFAULT_PIPELINE_TIMEOUT_SECONDS = 120
