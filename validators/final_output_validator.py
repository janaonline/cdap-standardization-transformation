"""Validation for final CDAP output files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from utils.excel_utils import read_table
from utils.report_utils import write_excel_report
from utils.text_utils import is_blank


REQUIRED_FINAL_COLUMNS = [
    "Unique Dataset Identifier",
    "Geo-Level",
    "Geo-cut",
    "Geo-Name",
    "Latitude for Geo-Name",
    "Longitude for Geo-Name",
    "LGD Code 1 (Primary LGD Code)",
    "Discontinued Geography Codes (Primary code)",
    "Secondary geo Code",
    "Tertiary geo Code",
    "Quaternary geo Code",
    "Quinary geo Code",
    "Super-Tag",
    "Super-tag code",
    "Sector",
    "Sector Code",
    "Sub-Sector",
    "Sub-Sector Code",
    "Dataset -Sector Mapping Code",
    "Indicator ",
    "Indicator Code",
    "Measurement Type of Indicator",
    "Indicator date",
    "Sub-Indicator ",
    "Sub-Indicator Code",
    "Dataset- Sector- Indicator Mapping Code",
    "Unit",
    "Value",
    "Keywords",
    "Temporal data ",
    "Temporal Indicator name",
    "Temporal Indicator linking Code",
    "Temporal time period ",
]

CRITICAL_NON_BLANK_COLUMNS = [
    "Unique Dataset Identifier",
    "Geo-Level",
    "Geo-cut",
    "Geo-Name",
    "Indicator ",
    "Indicator Code",
    "Sub-Indicator Code",
    "Value",
    "Unit",
    "Keywords",
    "Temporal Indicator linking Code",
]

WARNING_NON_BLANK_COLUMNS = ["Sector", "Sub-Sector"]


def _year_from_uid(value: Any) -> str:
    match = re.search(r"((?:19|20)\d{2})$", str(value))
    return match.group(1) if match else ""


def validate_final_output_file(
    final_file: str | Path,
    *,
    intermediate_rows: int | None = None,
    report_file: str | Path | None = None,
) -> dict[str, Any]:
    """Validate required CDAP columns and high-risk business-rule invariants."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        df = read_table(final_file)
    except Exception as exc:
        errors.append(f"Could not read final output: {exc}")
        df = pd.DataFrame()

    missing_columns = [col for col in REQUIRED_FINAL_COLUMNS if col not in df.columns]
    if missing_columns:
        errors.append(f"Final output missing required columns: {missing_columns}")

    if df.empty:
        errors.append("Final output has zero rows.")

    non_blank_summary: list[dict[str, Any]] = []
    for column in CRITICAL_NON_BLANK_COLUMNS:
        if column not in df.columns:
            continue
        blank_count = int(df[column].map(is_blank).sum())
        non_blank_summary.append({"column": column, "blank_count": blank_count})
        if blank_count:
            errors.append(f"{column} has {blank_count} blank rows.")

    for column in WARNING_NON_BLANK_COLUMNS:
        if column not in df.columns:
            continue
        blank_count = int(df[column].map(is_blank).sum())
        non_blank_summary.append({"column": column, "blank_count": blank_count})
        if blank_count:
            warnings.append(f"{column} has {blank_count} blank rows.")

    if "Value" in df.columns:
        filled = df["Value"][~df["Value"].map(is_blank)]
        bad_numeric = int(pd.to_numeric(filled, errors="coerce").isna().sum())
        if bad_numeric:
            warnings.append(f"Value has {bad_numeric} non-numeric filled rows.")

    mismatch_count = 0
    if all(col in df.columns for col in ["Unique Dataset Identifier", "Indicator date", "Temporal time period "]):
        uid_years = df["Unique Dataset Identifier"].map(_year_from_uid)
        indicator_years = df["Indicator date"].astype(str)
        temporal_years = df["Temporal time period "].astype(str)
        mismatch_count = int(((uid_years != indicator_years) | (uid_years != temporal_years)).sum())
        if mismatch_count:
            errors.append(f"UID year mismatches Indicator date or Temporal time period in {mismatch_count} rows.")

    na99_columns = [
        "Discontinued Geography Codes (Primary code)",
        "Secondary geo Code",
        "Tertiary geo Code",
        "Quaternary geo Code",
        "Quinary geo Code",
    ]
    na99_summary = []
    for column in na99_columns:
        if column in df.columns:
            missing_na99 = int((df[column].astype(str).str.strip() != "NA99").sum())
            na99_summary.append({"column": column, "non_na99_count": missing_na99})
            if missing_na99:
                warnings.append(f"{column} contains {missing_na99} non-NA99 values.")

    if intermediate_rows is not None and len(df) != intermediate_rows:
        warnings.append(f"Final row count {len(df)} differs from intermediate row count {intermediate_rows}.")

    empty_columns = [col for col in df.columns if int(df[col].map(is_blank).sum()) == len(df)]
    if empty_columns:
        warnings.append(f"Fully empty final columns: {', '.join(empty_columns)}")

    summary = {
        "success": not errors,
        "rows": int(len(df)),
        "intermediate_rows": intermediate_rows,
        "uid_year_mismatch_count": mismatch_count,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }

    report_path = ""
    if report_file:
        report_path = write_excel_report(
            report_file,
            {
                "summary": [summary],
                "errors": [{"error": item} for item in errors],
                "warnings": [{"warning": item} for item in warnings],
                "required_non_blank": non_blank_summary,
                "na99_rules": na99_summary,
                "empty_columns": [{"column": col} for col in empty_columns],
            },
        )

    return {
        "success": not errors,
        "rows": int(len(df)),
        "warnings": warnings,
        "errors": errors,
        "report_file": report_path,
    }
