"""Excel report helpers used by detection and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from utils.file_utils import ensure_parent


def as_dataframe(rows: Any) -> pd.DataFrame:
    """Convert simple report payloads into a DataFrame."""
    if isinstance(rows, pd.DataFrame):
        return rows
    if rows is None:
        return pd.DataFrame()
    if isinstance(rows, dict):
        return pd.DataFrame([rows])
    if isinstance(rows, list):
        return pd.DataFrame(rows)
    return pd.DataFrame({"value": [rows]})


def write_excel_report(path: str | Path, sheets: dict[str, Any]) -> str:
    """Write a multi-sheet report, ensuring at least one visible sheet exists."""
    report_path = ensure_parent(Path(path))
    safe_sheets = sheets or {"summary": [{"message": "No report details supplied."}]}

    with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
        wrote_sheet = False
        for sheet_name, rows in safe_sheets.items():
            df = as_dataframe(rows)
            if df.empty:
                df = pd.DataFrame({"message": ["No rows."]})
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            wrote_sheet = True
        if not wrote_sheet:
            pd.DataFrame({"message": ["No report details supplied."]}).to_excel(
                writer, sheet_name="summary", index=False
            )

    return str(report_path)
