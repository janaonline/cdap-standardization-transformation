"""Parser for tables where years are represented as columns."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from utils.excel_utils import get_sheet_names, read_with_detected_header
from utils.file_utils import ensure_parent
from utils.text_utils import clean_text, normalize_column_name
from utils.year_utils import normalize_year_token
from validators.intermediate_validator import REQUIRED_INTERMEDIATE_COLUMNS


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

    state_col = next((col for col in df.columns if "state" in normalize_column_name(col)), None)
    district_col = next((col for col in df.columns if "district" in normalize_column_name(col)), None)
    year_cols = [col for col in df.columns if normalize_year_token(col)]
    if not state_col or not year_cols:
        raise ValueError("Wide year parser needs a State column and at least one year column.")

    indicator_name = clean_text(detection.get("reason")) if detection else "Value"
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        state = clean_text(row.get(state_col))
        if not state:
            continue
        for col in year_cols:
            value = row.get(col)
            if pd.isna(value) or clean_text(value) == "":
                continue
            rows.append({
                "State": state,
                "State LGD Code": "",
                "District": clean_text(row.get(district_col)) if district_col else "NA",
                "District LGD name": clean_text(row.get(district_col)) if district_col else "NA",
                "District LGD Code": "",
                "Indicator": indicator_name or "Value",
                "Sub indicator": "NA",
                "Rural %": "",
                "Urban %": "",
                "Total %": value,
                "Year": normalize_year_token(col),
                "Unit": "Value",
            })

    out_df = pd.DataFrame(rows, columns=REQUIRED_INTERMEDIATE_COLUMNS)
    output_path = ensure_parent(Path(output_file))
    out_df.to_excel(output_path, index=False)
    return {
        "success": True,
        "parser": "wide_year_columns",
        "rows": int(len(out_df)),
        "output_file": str(output_path),
        "years_detected": sorted(out_df["Year"].dropna().astype(str).unique().tolist()),
        "detection": detection or {},
    }
