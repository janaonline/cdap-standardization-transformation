"""Validation and normalization for the common intermediate raw dataset."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from utils.excel_utils import read_table
from utils.file_utils import ensure_parent
from utils.report_utils import write_excel_report
from utils.text_utils import compact_key, is_blank


REQUIRED_INTERMEDIATE_COLUMNS = [
    "State",
    "State LGD Code",
    "District",
    "District LGD name",
    "District LGD Code",
    "Indicator",
    "Sub indicator",
    "Rural %",
    "Urban %",
    "Total %",
    "Year",
    "Unit",
]


COLUMN_ALIASES = {
    "state": "State",
    "statename": "State",
    "stateut": "State",
    "statelgdcode": "State LGD Code",
    "district": "District",
    "districtname": "District",
    "districtlgdname": "District LGD name",
    "districtlgdcode": "District LGD Code",
    "indicator": "Indicator",
    "indicatorname": "Indicator",
    "subindicator": "Sub indicator",
    "subindicatorname": "Sub indicator",
    "ruralpct": "Rural %",
    "ruralpercent": "Rural %",
    "ruralpercentage": "Rural %",
    "urbanpct": "Urban %",
    "urbanpercent": "Urban %",
    "urbanpercentage": "Urban %",
    "totalpct": "Total %",
    "totalpercent": "Total %",
    "totalpercentage": "Total %",
    "year": "Year",
    "financialyear": "Year",
    "unit": "Unit",
    "measurementunit": "Unit",
}

VALUE_COLUMNS = ["Rural %", "Urban %", "Total %"]


def canonical_column_name(column: Any) -> str | None:
    """Return the canonical intermediate column name for a tolerant alias."""
    return COLUMN_ALIASES.get(compact_key(column))


def intermediate_column_map(columns: list[Any]) -> dict[Any, str]:
    """Map source columns to canonical intermediate names."""
    mapping: dict[Any, str] = {}
    used: set[str] = set()
    for column in columns:
        canonical = canonical_column_name(column)
        if canonical and canonical not in used:
            mapping[column] = canonical
            used.add(canonical)
    return mapping


def looks_like_intermediate_columns(columns: list[Any]) -> bool:
    """True when all required bridge columns are present after normalization."""
    mapped = set(intermediate_column_map(columns).values())
    return set(REQUIRED_INTERMEDIATE_COLUMNS).issubset(mapped)


def normalize_intermediate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Rename tolerant aliases and order columns exactly as the bridge schema."""
    renamed = df.rename(columns=intermediate_column_map(list(df.columns))).copy()
    missing = [col for col in REQUIRED_INTERMEDIATE_COLUMNS if col not in renamed.columns]
    if missing:
        raise ValueError(f"Intermediate file missing required columns: {missing}")
    return renamed[REQUIRED_INTERMEDIATE_COLUMNS]


def normalize_intermediate_file(input_file: str | Path, output_file: str | Path) -> str:
    """Read, normalize, and write the bridge dataset."""
    df = normalize_intermediate_dataframe(read_table(input_file))
    output_path = ensure_parent(Path(output_file))
    df.to_excel(output_path, index=False)
    return str(output_path)


def _filled_any_value(row: pd.Series) -> bool:
    return any(not is_blank(row.get(col)) for col in VALUE_COLUMNS)


def validate_intermediate_dataframe(
    df: pd.DataFrame,
    *,
    report_file: str | Path | None = None,
) -> dict[str, Any]:
    """Validate the bridge dataset and optionally write an Excel report."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        normalized = normalize_intermediate_dataframe(df)
    except Exception as exc:
        errors.append(str(exc))
        normalized = df.copy()

    if normalized.empty:
        errors.append("Intermediate dataset has zero rows.")

    for column in ["State", "Indicator", "Year", "Unit"]:
        if column in normalized.columns:
            missing_count = int(normalized[column].map(is_blank).sum())
            if missing_count:
                errors.append(f"{column} has {missing_count} blank rows.")

    if all(col in normalized.columns for col in VALUE_COLUMNS):
        blank_values = int((~normalized.apply(_filled_any_value, axis=1)).sum())
        if blank_values:
            errors.append(f"{blank_values} rows have no Rural %, Urban %, or Total % value.")

        non_numeric: list[dict[str, Any]] = []
        for col in VALUE_COLUMNS:
            values = normalized[col]
            filled = values[~values.map(is_blank)]
            coerced = pd.to_numeric(filled, errors="coerce")
            bad = int(coerced.isna().sum())
            if bad:
                non_numeric.append({"column": col, "non_numeric_count": bad})
        if non_numeric:
            warnings.append("Value columns contain non-numeric values; review report details.")
    else:
        non_numeric = []

    duplicate_subset = [col for col in REQUIRED_INTERMEDIATE_COLUMNS if col in normalized.columns]
    duplicate_count = int(normalized.duplicated(subset=duplicate_subset).sum()) if duplicate_subset else 0
    if duplicate_count:
        warnings.append(f"Found {duplicate_count} duplicate intermediate rows.")

    missing_geo_codes = []
    for column in ["State LGD Code", "District LGD Code"]:
        if column in normalized.columns:
            missing_geo_codes.append({
                "column": column,
                "blank_or_na_count": int(normalized[column].map(is_blank).sum()),
            })

    empty_columns = [
        col for col in normalized.columns if int(normalized[col].map(is_blank).sum()) == len(normalized)
    ]
    if empty_columns:
        warnings.append(f"Fully empty columns: {', '.join(empty_columns)}")

    summary = {
        "success": not errors,
        "rows": int(len(normalized)),
        "unique_indicators": int(normalized["Indicator"].nunique()) if "Indicator" in normalized.columns else 0,
        "unique_years": int(normalized["Year"].nunique()) if "Year" in normalized.columns else 0,
        "unique_states": int(normalized["State"].nunique()) if "State" in normalized.columns else 0,
        "duplicate_rows": duplicate_count,
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
                "missing_geography_codes": missing_geo_codes,
                "non_numeric_values": non_numeric,
                "empty_columns": [{"column": col} for col in empty_columns],
            },
        )

    return {
        "success": not errors,
        "rows": int(len(normalized)),
        "warnings": warnings,
        "errors": errors,
        "report_file": report_path,
        "unique_indicators": summary["unique_indicators"],
        "unique_years": sorted(normalized["Year"].dropna().astype(str).unique().tolist())
        if "Year" in normalized.columns else [],
        "unique_states": summary["unique_states"],
    }


def validate_intermediate_file(input_file: str | Path, *, report_file: str | Path | None = None) -> dict[str, Any]:
    """Validate an intermediate file from disk."""
    try:
        df = read_table(input_file)
    except Exception as exc:
        result = {
            "success": False,
            "rows": 0,
            "warnings": [],
            "errors": [f"Could not read intermediate file: {exc}"],
            "report_file": "",
        }
        if report_file:
            result["report_file"] = write_excel_report(report_file, {"errors": [{"error": result["errors"][0]}]})
        return result
    return validate_intermediate_dataframe(df, report_file=report_file)
