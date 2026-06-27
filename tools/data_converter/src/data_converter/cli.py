from __future__ import annotations

import argparse
from typing import Sequence

from data_converter.commands import parse_cmd, pipeline_cmd, split_cmd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-converter",
        description="Unified CLI for splitting, parsing, and pipeline orchestration",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    split_cmd.register(subparsers)
    parse_cmd.register(subparsers)
    pipeline_cmd.register(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2
    return int(handler(args))
