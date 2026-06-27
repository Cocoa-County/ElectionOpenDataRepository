from __future__ import annotations

from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path

from data_converter.parser.models import to_json_string

from data_converter.defaults import DEFAULT_CSV_GLOB, DEFAULT_JSON_INDENT


def register(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    parser = subparsers.add_parser("parse", help="Parse CSV files using parser YAML config")
    parser.add_argument("--config", required=True, help="Path to parser YAML config")

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--csv", help="Path to one CSV file")
    input_group.add_argument("--input-dir", help="Directory containing CSV files")

    parser.add_argument("--glob", default=DEFAULT_CSV_GLOB, help="Glob for --input-dir mode")
    parser.add_argument("--recursive", action="store_true", help="Recursively parse directories")
    parser.add_argument("--output", help="Output JSON file for single parse")
    parser.add_argument("--output-dir", help="Output directory for batch parse JSON files")
    parser.add_argument("--output-manifest", help="Output path for batch manifest JSON")
    parser.add_argument("--indent", type=int, default=DEFAULT_JSON_INDENT, help="JSON indent")
    parser.add_argument("--omit-nulls", action="store_true", help="Omit null keys in JSON output")
    parser.add_argument("--hide-warnings", action="store_true", help="Hide warnings in parse output")
    parser.set_defaults(handler=run)


def run(args: Namespace) -> int:
    from data_converter.parser.main import parse_directory, parse_file

    include_warnings = not args.hide_warnings
    include_nulls = not args.omit_nulls

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
        return 0

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
            payload = result["data"] if result.get("ok") else result
            dst.write_text(
                to_json_string(payload, indent=args.indent, include_nulls=include_nulls),
                encoding="utf-8",
            )

    if args.output_manifest:
        Path(args.output_manifest).write_text(
            to_json_string(results, indent=args.indent, include_nulls=include_nulls),
            encoding="utf-8",
        )

    print(to_json_string(results, indent=args.indent, include_nulls=include_nulls))
    return 0
