from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd


def split_xlsx_to_dataframes(xlsx_file: str) -> dict[str, pd.DataFrame]:
    xls = pd.ExcelFile(xlsx_file)
    out: dict[str, pd.DataFrame] = {}
    for sheet_name in xls.sheet_names:
        out[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name)
    return out


def dataframe_to_rows(df: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    rows.append([_to_cell_string(col) for col in df.columns.tolist()])
    for values in df.values.tolist():
        rows.append([_to_cell_string(value) for value in values])
    return rows


def split_xlsx_to_row_matrices(xlsx_file: str) -> dict[str, list[list[str]]]:
    frames = split_xlsx_to_dataframes(xlsx_file)
    return {sheet_name: dataframe_to_rows(df) for sheet_name, df in frames.items()}


def split_xlsx_to_csv(
    xlsx_file: str,
    output_dir: str = ".",
    verbose: bool = False,
    log_file: str | None = None,
    create_dirs: bool = False,
) -> None:
    logging.basicConfig(filename=log_file, level=logging.INFO) if log_file else logging.basicConfig(level=logging.INFO)

    output_path = Path(output_dir)
    if not output_path.exists():
        if create_dirs:
            output_path.mkdir(parents=True, exist_ok=True)
            if verbose:
                logging.info("Created output directory: %s", output_path)
        else:
            raise FileNotFoundError(
                f"Output directory {output_path} does not exist. Use --create-dirs to create it."
            )

    frames = split_xlsx_to_dataframes(xlsx_file)
    for sheet_name, df in frames.items():
        csv_path = output_path / f"{sheet_name}.csv"
        df.to_csv(csv_path, index=False)
        if verbose:
            logging.info("Saved %s", csv_path)


def _to_cell_string(value: Any) -> str:
    if value is None:
        return ""
    # Treat pandas/numpy NaN consistently as empty for parser compatibility.
    if pd.isna(value):
        return ""
    return str(value)
