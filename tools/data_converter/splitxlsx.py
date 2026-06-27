import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"


def _ensure_src_path() -> None:
    src = Path(__file__).resolve().parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split XLSX file into one CSV file per sheet"
    )
    parser.add_argument("xlsx_file", type=str, help="Path to XLSX input file")
    parser.add_argument(
        "--output-dir",
        "--output_dir",
        dest="output_dir",
        default=str(DEFAULT_OUTPUT_DIR),
    )
    parser.add_argument(
        "--create-dirs",
        "--create_dirs",
        dest="create_dirs",
        action="store_true",
        help="Create output directory if needed",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logs")
    parser.add_argument("--log", type=str, default=None, help="Optional log file path")
    return parser.parse_args()


def split_xlsx_to_csv(
    xlsx_file: str,
    output_dir: str = ".",
    verbose: bool = False,
    log_file: str | None = None,
    create_dirs: bool = False,
) -> None:
    _ensure_src_path()
    from data_converter.split import split_xlsx_to_csv as split_impl

    split_impl(
        xlsx_file,
        output_dir=output_dir,
        verbose=verbose,
        log_file=log_file,
        create_dirs=create_dirs,
    )


def split_xlsx_to_dataframes(xlsx_file: str):
    _ensure_src_path()
    from data_converter.split import split_xlsx_to_dataframes as split_impl

    return split_impl(xlsx_file)


def split_xlsx_to_row_matrices(xlsx_file: str):
    _ensure_src_path()
    from data_converter.split import split_xlsx_to_row_matrices as split_impl

    return split_impl(xlsx_file)


def main() -> int:
    args = parse_arguments()
    split_xlsx_to_csv(
        args.xlsx_file,
        output_dir=args.output_dir,
        verbose=args.verbose,
        log_file=args.log,
        create_dirs=args.create_dirs,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())