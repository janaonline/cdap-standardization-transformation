"""Parser for workbooks where each sheet represents a year."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from converters.flat_state_table_parser import parse_dataframe_to_intermediate
from utils.excel_utils import get_sheet_names, read_with_detected_header
from utils.file_utils import ensure_parent
from utils.year_utils import normalize_year_token


SKIP_SHEETS = {"all", "summary", "metadata", "notes"}


def parse(
    source_file: str | Path,
    output_file: str | Path,
    *,
    detection: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    source_path = Path(source_file)
    frames: list[pd.DataFrame] = []
    years: list[str] = []
    for sheet in get_sheet_names(source_path):
        if sheet.strip().lower() in SKIP_SHEETS:
            continue
        year = normalize_year_token(sheet)
        if not year:
            continue
        df = read_with_detected_header(source_path, sheet_name=sheet)
        frames.append(parse_dataframe_to_intermediate(df, year=year))
        years.append(year)

    if not frames:
        raise ValueError("Multi-sheet year parser did not find usable year sheets.")

    out_df = pd.concat(frames, ignore_index=True)
    output_path = ensure_parent(Path(output_file))
    out_df.to_excel(output_path, index=False)
    return {
        "success": True,
        "parser": "multi_sheet_year",
        "rows": int(len(out_df)),
        "output_file": str(output_path),
        "years_detected": sorted(set(years)),
        "detection": detection or {},
    }
