"""Source workbook format detection for Stage 1 parser selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from utils.excel_utils import get_sheet_names, is_supported_tabular_file, read_sheet_samples, read_table, row_to_text
from utils.geo_utils import is_district_column, is_state_column
from utils.report_utils import write_excel_report
from utils.text_utils import clean_text, normalize_column_name
from utils.year_utils import extract_years_from_text, years_from_dataframe_sample, years_from_sheet_names
from validators.intermediate_validator import looks_like_intermediate_columns


UNKNOWN_DETECTION = {
    "detected_format": "unknown",
    "confidence": 0.0,
    "reason": "",
    "candidate_parser": "",
    "detected_sheets": [],
    "possible_years": [],
    "possible_geo_columns": [],
    "possible_indicator_columns": [],
}


def _score_sample(sheet_name: str, sample: pd.DataFrame) -> dict[str, Any]:
    text_rows = [row_to_text(row) for row in sample.itertuples(index=False)]
    all_text = " ".join(text_rows).lower()
    column_text = " ".join(clean_text(col) for col in sample.columns)

    possible_geo_columns: list[str] = []
    possible_indicator_columns: list[str] = []
    possible_years: list[str] = []
    possible_header_rows: list[int] = []
    year_column_count = 0

    for row_idx, row in sample.iterrows():
        cells = [clean_text(value) for value in row.tolist()]
        normalized = [normalize_column_name(value) for value in cells if clean_text(value)]
        if any(is_state_column(value) or is_district_column(value) for value in cells):
            possible_header_rows.append(int(row_idx))
        for value in cells:
            if is_state_column(value) or is_district_column(value):
                possible_geo_columns.append(value)
            if "indicator" in normalize_column_name(value) or "value" in normalize_column_name(value):
                possible_indicator_columns.append(value)
            years = extract_years_from_text(value)
            possible_years.extend(years)
            if years:
                year_column_count += 1
        if len([item for item in normalized if extract_years_from_text(item)]) >= 2:
            year_column_count += 2

    source_features = {
        "sheet": sheet_name,
        "has_percentage_distribution": "percentage distribution" in all_text,
        "has_usually_working": "usually working" in all_text,
        "has_industry_of_work": "industry of work" in all_text,
        "has_rural_urban": "rural" in all_text and "urban" in all_text,
        "has_gender_words": any(word in all_text for word in ["male", "female", "person", "persons"]),
        "has_state_section": "state :" in all_text or "state:" in all_text,
        "year_column_count": year_column_count,
        "possible_header_rows": possible_header_rows[:10],
        "possible_years": list(dict.fromkeys(possible_years + years_from_dataframe_sample(sample))),
        "possible_geo_columns": list(dict.fromkeys(possible_geo_columns)),
        "possible_indicator_columns": list(dict.fromkeys(possible_indicator_columns)),
        "sample_text": all_text[:1000],
        "column_text": column_text,
    }
    return source_features


def _choose_format(features: list[dict[str, Any]], sheet_years: list[str], input_columns: list[Any]) -> dict[str, Any]:
    if looks_like_intermediate_columns(input_columns):
        return {
            "detected_format": "intermediate",
            "confidence": 1.0,
            "reason": "Input has the common intermediate bridge columns.",
            "candidate_parser": "",
        }

    combined = {
        "plfs_industry": 0.0,
        "plfs_block": 0.0,
        "ncrb_district_section": 0.0,
        "flat_state_table": 0.0,
        "wide_year_columns": 0.0,
        "multi_sheet_year": 0.0,
        "ndap_tidy": 0.0,
    }
    reasons: dict[str, list[str]] = {key: [] for key in combined}

    for item in features:
        if item["has_percentage_distribution"] and item["has_usually_working"] and item["has_industry_of_work"]:
            combined["plfs_industry"] = max(combined["plfs_industry"], 0.95)
            reasons["plfs_industry"].append(f"{item['sheet']} contains PLFS industry title text.")
        if item["has_percentage_distribution"] and item["has_rural_urban"] and item["has_gender_words"]:
            combined["plfs_block"] = max(combined["plfs_block"], 0.75)
            reasons["plfs_block"].append(f"{item['sheet']} contains PLFS-like block labels.")
        if item["has_state_section"]:
            combined["ncrb_district_section"] = max(combined["ncrb_district_section"], 0.75)
            reasons["ncrb_district_section"].append(f"{item['sheet']} has State: section headings.")
        if item["year_column_count"] >= 3:
            combined["wide_year_columns"] = max(combined["wide_year_columns"], 0.8)
            reasons["wide_year_columns"].append(f"{item['sheet']} has multiple year-like columns.")
        if item["possible_geo_columns"] and item["possible_indicator_columns"]:
            combined["flat_state_table"] = max(combined["flat_state_table"], 0.7)
            reasons["flat_state_table"].append(f"{item['sheet']} has geography and indicator/value columns.")

    if len(sheet_years) >= 2:
        combined["multi_sheet_year"] = 0.82
        reasons["multi_sheet_year"].append("Multiple sheet names look like years.")

    normalized_columns = [normalize_column_name(col) for col in input_columns]
    if any("state" in col for col in normalized_columns) and any("year" in col for col in normalized_columns):
        combined["ndap_tidy"] = 0.78
        reasons["ndap_tidy"].append("Default header has State and Year columns.")

    selected = max(combined, key=combined.get)
    confidence = combined[selected]
    if confidence == 0:
        return {
            "detected_format": "unknown",
            "confidence": 0.0,
            "reason": "No detector rule reached a usable confidence.",
            "candidate_parser": "",
        }

    return {
        "detected_format": selected,
        "confidence": float(confidence),
        "reason": " ".join(reasons[selected]),
        "candidate_parser": f"converters.{selected}_parser",
    }


def detect_source_format(
    source_file: str | Path,
    *,
    report_file: str | Path | None = None,
    max_rows: int = 50,
) -> dict[str, Any]:
    """Inspect a source file and return the parser profile to use."""
    path = Path(source_file)
    result = dict(UNKNOWN_DETECTION)

    if not path.exists():
        result["reason"] = f"Source file does not exist: {path}"
        return result
    if not is_supported_tabular_file(path):
        result["reason"] = f"Unsupported source file extension: {path.suffix}"
        return result

    try:
        sheet_names = get_sheet_names(path)
        samples = read_sheet_samples(path, max_rows=max_rows)
        default_df = read_table(path, nrows=5)
    except Exception as exc:
        result["reason"] = f"Could not inspect source file: {exc}"
        return result

    features = [_score_sample(sheet, sample) for sheet, sample in samples.items()]
    sheet_years = years_from_sheet_names(path)
    choice = _choose_format(features, sheet_years, list(default_df.columns))

    possible_years: list[str] = []
    possible_geo_columns: list[str] = []
    possible_indicator_columns: list[str] = []
    for item in features:
        possible_years.extend(item["possible_years"])
        possible_geo_columns.extend(item["possible_geo_columns"])
        possible_indicator_columns.extend(item["possible_indicator_columns"])

    result.update(choice)
    result.update({
        "detected_sheets": sheet_names,
        "possible_years": list(dict.fromkeys(possible_years + sheet_years)),
        "possible_geo_columns": list(dict.fromkeys(possible_geo_columns)),
        "possible_indicator_columns": list(dict.fromkeys(possible_indicator_columns)),
    })

    if report_file:
        sample_rows = []
        for sheet, sample in samples.items():
            preview = sample.head(30).fillna("")
            for idx, row in preview.iterrows():
                sample_rows.append({"sheet": sheet, "row_number": int(idx) + 1, "row_text": row_to_text(row)})
        write_excel_report(
            report_file,
            {
                "detection_summary": [result],
                "sheet_features": features,
                "sample_first_rows": sample_rows,
            },
        )

    return result


def write_mapping_review_report(
    source_file: str | Path,
    *,
    detection: dict[str, Any],
    report_file: str | Path,
) -> str:
    """Create the human-review report used when no parser is selected."""
    path = Path(source_file)
    samples = read_sheet_samples(path, max_rows=30) if path.exists() and is_supported_tabular_file(path) else {}
    sample_rows = []
    for sheet, sample in samples.items():
        for idx, row in sample.head(30).fillna("").iterrows():
            sample_rows.append({"sheet": sheet, "row_number": int(idx) + 1, "row_text": row_to_text(row)})

    return write_excel_report(
        report_file,
        {
            "summary": [{
                "detected_format": detection.get("detected_format", "unknown"),
                "confidence": detection.get("confidence", 0),
                "reason": detection.get("reason", ""),
                "recommended_next_step": "Create or tune a parser profile for this source layout.",
            }],
            "detected_sheets": [{"sheet": item} for item in detection.get("detected_sheets", [])],
            "possible_geo_columns": [{"column": item} for item in detection.get("possible_geo_columns", [])],
            "possible_year_columns": [{"year_or_label": item} for item in detection.get("possible_years", [])],
            "possible_indicator_columns": [{"column": item} for item in detection.get("possible_indicator_columns", [])],
            "sample_first_30_rows": sample_rows,
        },
    )
