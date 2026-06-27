from __future__ import annotations

import argparse

from data_converter.parser.models import to_json_string

from .runner import run_pipeline


def cli_main() -> None:
    parser = argparse.ArgumentParser(description="Download, split, and parse election XLSX files")
    parser.add_argument("--pipeline-config", required=True, help="Path to pipeline YAML config")
    parser.add_argument("--url", help="URL to XLSX file")
    parser.add_argument("--xlsx", help="Local XLSX path")
    parser.add_argument("--output-dir", help="Override output directory")

    parser.add_argument("--summary-only", action="store_true", help="Print summary only")
    parser.add_argument("--write-sheet-json", dest="write_sheet_json", action="store_true")
    parser.add_argument("--no-write-sheet-json", dest="write_sheet_json", action="store_false")
    parser.set_defaults(write_sheet_json=None)
    parser.add_argument("--write-manifest", dest="write_manifest", action="store_true")
    parser.add_argument("--no-write-manifest", dest="write_manifest", action="store_false")
    parser.set_defaults(write_manifest=None)
    parser.add_argument("--keep-split-csv", dest="keep_split_csv", action="store_true")
    parser.add_argument("--delete-split-csv", dest="delete_split_csv", action="store_true")
    parser.add_argument("--omit-nulls", action="store_true")
    parser.add_argument("--timeout", type=int, help="Download timeout seconds")
    args = parser.parse_args()

    manifest = run_pipeline(
        args.pipeline_config,
        xlsx_path=args.xlsx,
        url=args.url,
        output_dir_override=args.output_dir,
        summary_only_override=args.summary_only,
        write_sheet_json_override=args.write_sheet_json,
        write_manifest_override=args.write_manifest,
        keep_split_csv_override=args.keep_split_csv,
        delete_split_csv_override=args.delete_split_csv,
        omit_nulls_override=args.omit_nulls,
        timeout_override=args.timeout,
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
