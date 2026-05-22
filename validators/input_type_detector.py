"""Detect whether an input is already the common intermediate format."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.excel_utils import is_supported_tabular_file, read_table
from validators.intermediate_validator import looks_like_intermediate_columns


INTERMEDIATE_FORMAT = "INTERMEDIATE_FORMAT"
SOURCE_FORMAT = "SOURCE_FORMAT"
UNKNOWN = "UNKNOWN"


def detect_input_type(file_path: str | Path) -> dict[str, Any]:
    """Classify a candidate input file without scanning entire workbooks."""
    path = Path(file_path)
    if not path.exists():
        return {
            "input_type": UNKNOWN,
            "confidence": 0.0,
            "reason": f"File does not exist: {path}",
            "columns": [],
        }

    if not is_supported_tabular_file(path):
        return {
            "input_type": UNKNOWN,
            "confidence": 0.0,
            "reason": f"Unsupported file extension: {path.suffix}",
            "columns": [],
        }

    try:
        df = read_table(path, nrows=5)
    except Exception as exc:
        return {
            "input_type": UNKNOWN,
            "confidence": 0.0,
            "reason": f"Could not read tabular columns: {exc}",
            "columns": [],
        }

    columns = list(df.columns)
    if looks_like_intermediate_columns(columns):
        return {
            "input_type": INTERMEDIATE_FORMAT,
            "confidence": 1.0,
            "reason": "Required intermediate columns are present after normalized matching.",
            "columns": [str(col) for col in columns],
        }

    return {
        "input_type": SOURCE_FORMAT,
        "confidence": 0.8,
        "reason": "Readable tabular file, but not the intermediate bridge schema.",
        "columns": [str(col) for col in columns],
    }
