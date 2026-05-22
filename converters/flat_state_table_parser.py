"""Parser for simple state-level tables with indicator columns."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from utils.excel_utils import get_sheet_names, read_with_detected_header
from utils.file_utils import ensure_parent
from utils.text_utils import clean_text, normalize_column_name
from utils.year_utils import detect_best_single_year
from validators.intermediate_validator import REQUIRED_INTERMEDIATE_COLUMNS


GEO_COLUMNS = {"state", "state_ut", "state_name", "district", "district_name", "year"}


def _find_column(df: pd.DataFrame, names: set[str]) -> str | None:
    for col in df.columns:
        if normalize_column_name(col) in names:
            return col
    return None


def parse_dataframe_to_intermediate(
    df: pd.DataFrame,
    *,
    year: str,
    title: str = "",
) -> pd.DataFrame:
    """Melt a flat state/district table into the bridge schema."""
    state_col = _find_column(df, {"state", "state_ut", "state_name"})
    district_col = _find_column(df, {"district", "district_name"})
    year_col = _find_column(df, {"year", "financial_year"})
    if not state_col:
        raise ValueError("Flat state parser could not find a State column.")

    skip_cols = {state_col}
    if district_col:
        skip_cols.add(district_col)
    if year_col:
        skip_cols.add(year_col)

    indicator_cols = [
        col for col in df.columns
        if col not in skip_cols and not normalize_column_name(col).endswith("code")
    ]
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        state = clean_text(row.get(state_col))
        if not state:
            continue
        row_year = clean_text(row.get(year_col)) if year_col else year
        for indicator_col in indicator_cols:
            value = row.get(indicator_col)
            if pd.isna(value) or clean_text(value) == "":
                continue
            indicator = clean_text(indicator_col)
            rows.append({
                "State": state,
                "State LGD Code": "",
                "District": clean_text(row.get(district_col)) if district_col else "NA",
                "District LGD name": clean_text(row.get(district_col)) if district_col else "NA",
                "District LGD Code": "",
                "Indicator": indicator or title or "Value",
                "Sub indicator": "NA",
                "Rural %": "",
                "Urban %": "",
                "Total %": value,
                "Year": row_year,
                "Unit": "Percentage" if "%" in indicator or "percent" in indicator.lower() else "Value",
            })
    return pd.DataFrame(rows, columns=REQUIRED_INTERMEDIATE_COLUMNS)


def parse(
    source_file: str | Path,
    output_file: str | Path,
    *,
    metadata_file: str | Path | None = None,
    year_detection_priority: list[str] | None = None,
    detection: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    source_path = Path(source_file)
    sheet = get_sheet_names(source_path)[0]
    df = read_with_detected_header(source_path, sheet_name=sheet)
    year, year_sources = detect_best_single_year(
        source_path,
        metadata_file=metadata_file,
        priority=year_detection_priority,
    )
    if not year:
        raise ValueError("Flat state parser could not detect a year.")
    out_df = parse_dataframe_to_intermediate(df, year=year)
    output_path = ensure_parent(Path(output_file))
    out_df.to_excel(output_path, index=False)
    return {
        "success": True,
        "parser": "flat_state_table",
        "rows": int(len(out_df)),
        "output_file": str(output_path),
        "years_detected": sorted(out_df["Year"].dropna().astype(str).unique().tolist()),
        "year_sources": year_sources,
        "detection": detection or {},
    }
