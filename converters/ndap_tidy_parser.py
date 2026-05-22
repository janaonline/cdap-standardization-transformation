"""Parser for NDAP-like tidy files with State, Year, and indicator columns."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from converters.flat_state_table_parser import parse_dataframe_to_intermediate
from utils.excel_utils import get_sheet_names, read_with_detected_header
from utils.file_utils import ensure_parent
from utils.text_utils import normalize_column_name


def parse(
    source_file: str | Path,
    output_file: str | Path,
    *,
    detection: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    source_path = Path(source_file)
    sheet = get_sheet_names(source_path)[0]
    df = read_with_detected_header(source_path, sheet_name=sheet)
    if not any("state" in normalize_column_name(col) for col in df.columns):
        raise ValueError("NDAP tidy parser could not find a State column.")
    if not any("year" in normalize_column_name(col) for col in df.columns):
        raise ValueError("NDAP tidy parser could not find a Year column.")

    out_df = parse_dataframe_to_intermediate(df, year="")
    output_path = ensure_parent(Path(output_file))
    out_df.to_excel(output_path, index=False)
    return {
        "success": True,
        "parser": "ndap_tidy",
        "rows": int(len(out_df)),
        "output_file": str(output_path),
        "years_detected": sorted(out_df["Year"].dropna().astype(str).unique().tolist()),
        "detection": detection or {},
    }
