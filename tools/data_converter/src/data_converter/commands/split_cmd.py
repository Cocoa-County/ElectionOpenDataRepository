from __future__ import annotations

from argparse import ArgumentParser, Namespace, _SubParsersAction

from data_converter.defaults import DEFAULT_OUTPUT_DIR
from data_converter.split import split_xlsx_to_csv


def register(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    parser = subparsers.add_parser("split", help="Split XLSX into one CSV file per sheet")
    parser.add_argument("--xlsx", required=True, help="Path to XLSX input file")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for output CSV files",
    )
    parser.add_argument("--create-dirs", action="store_true", help="Create output directory")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logs")
    parser.add_argument("--log", help="Path to optional log file")
    parser.set_defaults(handler=run)


def run(args: Namespace) -> int:
    split_xlsx_to_csv(
        args.xlsx,
        output_dir=args.output_dir,
        verbose=args.verbose,
        log_file=args.log,
        create_dirs=args.create_dirs,
    )
    return 0
