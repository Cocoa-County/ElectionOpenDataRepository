from __future__ import annotations

import logging
from argparse import ArgumentParser, Namespace, _SubParsersAction

from data_converter.parser.models import to_json_string

from data_converter.defaults import DEFAULT_PIPELINE_TIMEOUT_SECONDS


def register(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    parser = subparsers.add_parser("pipeline", help="Run full pipeline: download/split/parse/write")
    parser.add_argument("--config", required=True, help="Path to pipeline YAML config")
    source_group = parser.add_mutually_exclusive_group(required=False)
    source_group.add_argument("--url", help="Override URL input from config")
    source_group.add_argument("--xlsx", help="Override local XLSX input from config")
    parser.add_argument("--output-dir", help="Override output directory")

    parser.add_argument("--summary-only", action="store_true", help="Do not write JSON files")
    parser.add_argument("--write-sheet-json", dest="write_sheet_json", action="store_true")
    parser.add_argument("--no-write-sheet-json", dest="write_sheet_json", action="store_false")
    parser.set_defaults(write_sheet_json=None)
    parser.add_argument("--write-combined-json", dest="write_combined_json", action="store_true")
    parser.add_argument("--no-write-combined-json", dest="write_combined_json", action="store_false")
    parser.set_defaults(write_combined_json=None)
    parser.add_argument("--combined-name", help="Filename for combined JSON output")
    parser.add_argument("--transform", dest="transform", action="store_true")
    parser.add_argument("--no-transform", dest="transform", action="store_false")
    parser.set_defaults(transform=None)
    parser.add_argument("--transform-output", help="Output path for transformed election JSON")
    parser.add_argument("--transform-metadata", help="Output path for transformed metadata JSON")
    parser.add_argument("--update-index", dest="update_index", action="store_true")
    parser.add_argument("--no-update-index", dest="update_index", action="store_false")
    parser.set_defaults(update_index=None)
    parser.add_argument("--write-manifest", dest="write_manifest", action="store_true")
    parser.add_argument("--no-write-manifest", dest="write_manifest", action="store_false")
    parser.set_defaults(write_manifest=None)
    parser.add_argument("--in-memory-tables", dest="in_memory_tables", action="store_true")
    parser.add_argument("--no-in-memory-tables", dest="in_memory_tables", action="store_false")
    parser.set_defaults(in_memory_tables=None)
    parser.add_argument(
        "--table-representation",
        choices=("rows", "dataframe"),
        help="In-memory table representation used before parse",
    )
    parser.add_argument("--keep-split-csv", dest="keep_split_csv", action="store_true")
    parser.add_argument("--delete-split-csv", dest="delete_split_csv", action="store_true")
    parser.add_argument("--output-versioning", dest="output_versioning", action="store_true")
    parser.add_argument("--no-output-versioning", dest="output_versioning", action="store_false")
    parser.set_defaults(output_versioning=None)
    parser.add_argument(
        "--output-version-template",
        help="Template for version subdirectory, for example {run_utc:%%Y%%m%%dT%%H%%M%%SZ}",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging with stage timing",
    )
    parser.add_argument("--omit-nulls", action="store_true")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_PIPELINE_TIMEOUT_SECONDS,
        help="Download timeout seconds",
    )
    parser.set_defaults(handler=run)


def run(args: Namespace) -> int:
    from data_converter.pipeline.runner import run_pipeline

    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

    manifest = run_pipeline(
        args.config,
        xlsx_path=args.xlsx,
        url=args.url,
        output_dir_override=args.output_dir,
        summary_only_override=args.summary_only,
        write_sheet_json_override=args.write_sheet_json,
        write_combined_json_override=args.write_combined_json,
        write_manifest_override=args.write_manifest,
        combined_name_override=args.combined_name,
        transform_override=args.transform,
        transform_output_path_override=args.transform_output,
        transform_metadata_path_override=args.transform_metadata,
        transform_update_index_override=args.update_index,
        in_memory_tables_override=args.in_memory_tables,
        table_representation_override=args.table_representation,
        keep_split_csv_override=args.keep_split_csv,
        delete_split_csv_override=args.delete_split_csv,
        output_versioning_override=args.output_versioning,
        output_version_template_override=args.output_version_template,
        omit_nulls_override=args.omit_nulls,
        timeout_override=args.timeout,
        verbose=args.verbose,
    )

    print(
        to_json_string(
            {
                "counts": manifest["counts"],
                "output_dir": manifest["output_dir"],
                "source": manifest["source"],
            },
            indent=2,
            include_nulls=True,
        )
    )
    return 0
