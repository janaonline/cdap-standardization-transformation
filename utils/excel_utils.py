"""Efficient readers for Excel and CSV detection workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from utils.text_utils import clean_text, normalize_column_name


SUPPORTED_TABULAR_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".csv"}


def is_supported_tabular_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_TABULAR_EXTENSIONS


def get_sheet_names(path: str | Path) -> list[str]:
    """Return sheet names for Excel files, or a single CSV pseudo-sheet."""
    file_path = Path(path)
    if file_path.suffix.lower() == ".csv":
        return [file_path.stem]
    with pd.ExcelFile(file_path) as workbook:
        return workbook.sheet_names


def read_table(path: str | Path, *, sheet_name: str | int = 0, nrows: int | None = None) -> pd.DataFrame:
    """Read a tabular file with its first row as the header."""
    file_path = Path(path)
    if file_path.suffix.lower() == ".csv":
        return pd.read_csv(file_path, nrows=nrows)
    return pd.read_excel(file_path, sheet_name=sheet_name, nrows=nrows)


def read_raw_sample(path: str | Path, *, sheet_name: str | int = 0, nrows: int = 50) -> pd.DataFrame:
    """Read a small headerless sample for format detection."""
    file_path = Path(path)
    if file_path.suffix.lower() == ".csv":
        return pd.read_csv(file_path, header=None, nrows=nrows)
    return pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=nrows)


def read_sheet_samples(path: str | Path, *, max_rows: int = 50, max_sheets: int = 10) -> dict[str, pd.DataFrame]:
    """Read one headerless sample per sheet. This is O(sampled cells)."""
    names = get_sheet_names(path)[:max_sheets]
    return {name: read_raw_sample(path, sheet_name=name, nrows=max_rows) for name in names}


def detect_header_row(sample: pd.DataFrame, required_hints: list[str] | None = None) -> int | None:
    """Find the first likely header row in a headerless sample."""
    hints = {normalize_column_name(hint) for hint in (required_hints or [])}
    best_row = None
    best_score = 0

    for row_idx, row in sample.iterrows():
        values = [normalize_column_name(value) for value in row.tolist() if clean_text(value)]
        if len(values) < 2:
            continue
        score = len(set(values) & hints)
        if any("state" in value for value in values):
            score += 2
        if any("district" in value for value in values):
            score += 1
        if any("year" in value for value in values):
            score += 1
        if score > best_score:
            best_score = score
            best_row = int(row_idx)

    return best_row


def read_with_detected_header(path: str | Path, *, sheet_name: str | int = 0) -> pd.DataFrame:
    """Read a sheet using a detected header row when the default header is not useful."""
    sample = read_raw_sample(path, sheet_name=sheet_name, nrows=50)
    header_row = detect_header_row(sample)
    file_path = Path(path)
    if file_path.suffix.lower() == ".csv":
        return pd.read_csv(file_path, header=header_row or 0)
    return pd.read_excel(file_path, sheet_name=sheet_name, header=header_row or 0)


def row_to_text(row: Any) -> str:
    """Join a row into searchable text."""
    return " ".join(clean_text(value) for value in row if clean_text(value))
