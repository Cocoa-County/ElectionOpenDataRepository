from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .config_loader import load_config
from .csv_reader import read_csv_rows
from .models import ParseWarning, ParsedDocument, to_json_string
from .normalizer import normalize_rows
from .results_parser import parse_results
from .turnout_parser import parse_turnout_summary


def parse_file(
    csv_path: str,
    yaml_path: str,
    as_object: bool = False,
    include_warnings: bool = True,
) -> dict[str, Any] | ParsedDocument:
    cfg = load_config(yaml_path)
    rows = read_csv_rows(csv_path)
    normalized = normalize_rows(rows, cfg.get("normalization", {}))

    warnings: list[ParseWarning] = []
    document_type = cfg["document"]["type"]
    if document_type == "turnout_summary":
        parsed = parse_turnout_summary(normalized, cfg, warnings)
    elif document_type == "election_results":
        parsed = parse_results(normalized, cfg, warnings)
    else:
        raise ValueError(f"Unsupported document type: {document_type}")

    if include_warnings:
        parsed["warnings"] = [warning.to_dict() for warning in warnings]

    if as_object:
        return ParsedDocument(parsed)
    return parsed


def parse_directory(
    input_dir: str,
    yaml_path: str,
    pattern: str = "*.csv",
    recursive: bool = False,
    include_warnings: bool = True,
) -> list[dict[str, Any]]:
    base_dir = Path(input_dir)
    paths = base_dir.rglob(pattern) if recursive else base_dir.glob(pattern)

    results: list[dict[str, Any]] = []
    for csv_path in sorted(paths):
        if not csv_path.is_file():
            continue
        try:
            parsed = parse_file(
                str(csv_path),
                yaml_path,
                as_object=False,
                include_warnings=include_warnings,
            )
            results.append(
                {
                    "file": str(csv_path),
                    "ok": True,
                    "data": parsed,
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "file": str(csv_path),
                    "ok": False,
                    "error": str(exc),
                }
            )

    return results


def cli_main() -> None:
    parser = argparse.ArgumentParser(description="Parse election CSV files with YAML config")
    parser.add_argument("--config", required=True, help="Path to YAML parser config")
    parser.add_argument("--csv", help="Path to a single CSV file to parse")
    parser.add_argument("--input-dir", help="Directory of CSV files for batch parsing")
    parser.add_argument("--glob", default="*.csv", help="Glob pattern for batch parsing")
    parser.add_argument("--recursive", action="store_true", help="Recursively parse directories")
    parser.add_argument("--output", help="Output JSON file for single parse")
    parser.add_argument("--output-dir", help="Output directory for batch parse JSON files")
    parser.add_argument("--indent", type=int, default=2, help="JSON indent")
    parser.add_argument(
        "--omit-nulls",
        action="store_true",
        help="Omit keys with null values when writing JSON",
    )
    parser.add_argument(
        "--hide-warnings",
        action="store_true",
        help="Do not include warnings in output payload",
    )
    args = parser.parse_args()

    include_warnings = not args.hide_warnings
    include_nulls = not args.omit_nulls

    if bool(args.csv) == bool(args.input_dir):
        parser.error("Provide exactly one of --csv or --input-dir")

    if args.csv:
        parsed = parse_file(
            args.csv,
            args.config,
            as_object=True,
            include_warnings=include_warnings,
        )
        if args.output:
            parsed.write_json(args.output, indent=args.indent, include_nulls=include_nulls)
            print(f"Wrote {args.output}")
        else:
            print(parsed.to_json(indent=args.indent, include_nulls=include_nulls))
        return

    results = parse_directory(
        args.input_dir,
        args.config,
        pattern=args.glob,
        recursive=args.recursive,
        include_warnings=include_warnings,
    )

    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for result in results:
            src = Path(result["file"])
            dst = output_dir / f"{src.stem}.json"
            if result["ok"]:
                dst.write_text(
                    to_json_string(
                        result["data"],
                        indent=args.indent,
                        include_nulls=include_nulls,
                    ),
                    encoding="utf-8",
                )
            else:
                dst.write_text(
                    to_json_string(
                        result,
                        indent=args.indent,
                        include_nulls=include_nulls,
                    ),
                    encoding="utf-8",
                )

    print(to_json_string(results, indent=args.indent, include_nulls=include_nulls))
