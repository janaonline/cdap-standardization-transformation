"""Parser for district tables with repeated 'State : Name' section headings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from utils.excel_utils import get_sheet_names, read_raw_sample
from utils.file_utils import ensure_parent
from utils.text_utils import clean_text, normalize_column_name
from utils.year_utils import detect_best_single_year
from validators.intermediate_validator import REQUIRED_INTERMEDIATE_COLUMNS


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
    raw = read_raw_sample(source_path, sheet_name=sheet, nrows=100000)
    year, year_sources = detect_best_single_year(
        source_path,
        metadata_file=metadata_file,
        priority=year_detection_priority,
    )
    if not year:
        raise ValueError("NCRB district-section parser could not detect a year.")

    current_state = ""
    headers: list[str] = []
    rows: list[dict[str, Any]] = []
    for _, row in raw.iterrows():
        cells = [clean_text(value) for value in row.tolist()]
        row_text = " ".join(cells)
        if "state :" in row_text.lower() or row_text.lower().startswith("state:"):
            current_state = row_text.split(":", 1)[-1].strip()
            headers = []
            continue
        if current_state and not headers and any("district" in normalize_column_name(value) for value in cells):
            headers = cells
            continue
        if current_state and headers:
            district_value = ""
            for idx, header in enumerate(headers):
                if "district" in normalize_column_name(header):
                    district_value = cells[idx] if idx < len(cells) else ""
                    break
            if not district_value:
                continue
            for idx, header in enumerate(headers):
                if idx >= len(cells) or "district" in normalize_column_name(header):
                    continue
                value = cells[idx]
                if value == "":
                    continue
                rows.append({
                    "State": current_state,
                    "State LGD Code": "",
                    "District": district_value,
                    "District LGD name": district_value,
                    "District LGD Code": "",
                    "Indicator": header,
                    "Sub indicator": "NA",
                    "Rural %": "",
                    "Urban %": "",
                    "Total %": value,
                    "Year": year,
                    "Unit": "Value",
                })

    out_df = pd.DataFrame(rows, columns=REQUIRED_INTERMEDIATE_COLUMNS)
    if out_df.empty:
        raise ValueError("NCRB district-section parser produced zero rows.")
    output_path = ensure_parent(Path(output_file))
    out_df.to_excel(output_path, index=False)
    return {
        "success": True,
        "parser": "ncrb_district_section",
        "rows": int(len(out_df)),
        "output_file": str(output_path),
        "years_detected": [year],
        "year_sources": year_sources,
        "detection": detection or {},
    }
