"""Compatibility entrypoint forwarding to unified pipeline CLI."""

from __future__ import annotations

from pathlib import Path
import sys

__all__ = ["load_pipeline_config", "run_pipeline", "main"]


def _ensure_src_path() -> None:
    root = Path(__file__).resolve().parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> int:
    _ensure_src_path()
    from data_converter.cli import main as cli_main

    return cli_main(["pipeline", *sys.argv[1:]])


def load_pipeline_config(path: str | Path):
    _ensure_src_path()
    from data_converter.pipeline.config import load_pipeline_config as _loader

    return _loader(path)


def run_pipeline(*args, **kwargs):
    _ensure_src_path()
    from data_converter.pipeline.runner import run_pipeline as _runner

    return _runner(*args, **kwargs)


if __name__ == "__main__":
    raise SystemExit(main())
