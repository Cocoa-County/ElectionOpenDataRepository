from __future__ import annotations

import csv
from pathlib import Path


def read_csv_rows(path: str | Path) -> list[list[str]]:
    csv_path = Path(path)
    rows: list[list[str]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            rows.append(row)
    return rows
