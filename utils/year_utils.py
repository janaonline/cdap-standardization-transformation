"""Year extraction helpers for source detection and parser adapters."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from utils.excel_utils import get_sheet_names, read_sheet_samples
from utils.text_utils import clean_text


YEAR_PATTERN = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
SHORT_YEAR_PATTERN = re.compile(r"(?:'|fy\s*)?(\d{2})(?!\d)", re.IGNORECASE)


def normalize_year_token(value: Any) -> str | None:
    """Return a four-digit year string from common government table labels."""
    text = clean_text(value)
    if not text:
        return None

    # Financial-year ranges are assigned to the ending calendar year.
    fy_match = re.search(r"((?:19|20)\d{2})\s*[-/]\s*(\d{2})(?!\d)", text)
    if fy_match:
        century = fy_match.group(1)[:2]
        return f"{century}{fy_match.group(2)}"

    full_years = YEAR_PATTERN.findall(text)
    if full_years:
        return full_years[-1] if len(full_years) > 1 else full_years[0]

    if re.search(r"till|upto|up to|march|financial year|fy", text, re.IGNORECASE):
        short_match = SHORT_YEAR_PATTERN.search(text)
        if short_match:
            year = int(short_match.group(1))
            return str(2000 + year if year <= 79 else 1900 + year)

    return None


def extract_years_from_text(value: Any) -> list[str]:
    """Extract unique years from a text value in encounter order."""
    text = clean_text(value)
    lower_text = text.lower()
    if re.search(r"\bnic\b.{0,30}(?:19|20)\d{2}|(?:19|20)\d{2}.{0,30}\bnic\b", lower_text):
        return []
    years: list[str] = []

    for match in re.finditer(r"((?:19|20)\d{2})\s*[-/]\s*(\d{2})(?!\d)", text):
        century = match.group(1)[:2]
        years.append(f"{century}{match.group(2)}")

    years.extend(YEAR_PATTERN.findall(text))

    if re.search(r"till|upto|up to|march|financial year|fy", text, re.IGNORECASE):
        short = SHORT_YEAR_PATTERN.search(text)
        if short:
            value_int = int(short.group(1))
            years.append(str(2000 + value_int if value_int <= 79 else 1900 + value_int))

    deduped: list[str] = []
    for year in years:
        if year not in deduped:
            deduped.append(year)
    return deduped


def years_from_dataframe_sample(df: pd.DataFrame) -> list[str]:
    """Scan a sampled DataFrame once for year-like text."""
    years: list[str] = []
    for column in df.columns:
        years.extend(extract_years_from_text(column))
    for row in df.itertuples(index=False):
        for value in row:
            years.extend(extract_years_from_text(value))
    return list(dict.fromkeys(years))


def years_from_sheet_names(path: str | Path) -> list[str]:
    years: list[str] = []
    for sheet in get_sheet_names(path):
        years.extend(extract_years_from_text(sheet))
    return list(dict.fromkeys(years))


def years_from_metadata_uid(metadata_file: str | Path | None) -> list[str]:
    """Read metadata once and collect years from UID-like text values."""
    if not metadata_file:
        return []
    path = Path(metadata_file)
    if not path.exists():
        return []
    try:
        df = pd.read_excel(path, nrows=200)
    except Exception:
        return []

    years: list[str] = []
    uid_columns = [col for col in df.columns if "unique" in clean_text(col).lower() or "uid" in clean_text(col).lower()]
    scan_columns = uid_columns or list(df.columns)
    for col in scan_columns:
        for value in df[col].dropna().tolist():
            years.extend(extract_years_from_text(value))
    return list(dict.fromkeys(years))


def detect_year_sources(
    source_file: str | Path,
    *,
    metadata_file: str | Path | None = None,
    max_rows: int = 50,
) -> dict[str, list[str]]:
    """Collect years by priority source without repeatedly reading full files."""
    path = Path(source_file)
    table_years: list[str] = []
    try:
        for sample in read_sheet_samples(path, max_rows=max_rows).values():
            table_years.extend(years_from_dataframe_sample(sample))
    except Exception:
        table_years = []

    return {
        "explicit_year_column": [],
        "year_columns": [],
        "table_title": list(dict.fromkeys(table_years)),
        "sheet_name": years_from_sheet_names(path) if path.exists() else [],
        "metadata_uid": years_from_metadata_uid(metadata_file),
        "filename": extract_years_from_text(path.name),
    }


def choose_single_year(year_sources: dict[str, list[str]], priority: list[str] | None = None) -> str | None:
    """Choose one year only when a priority source provides a clear candidate."""
    ordered = priority or [
        "explicit_year_column",
        "year_columns",
        "table_title",
        "sheet_name",
        "metadata_uid",
        "filename",
    ]
    for source in ordered:
        years = list(dict.fromkeys(year_sources.get(source, [])))
        if len(years) == 1:
            return years[0]
    return None


def detect_best_single_year(
    source_file: str | Path,
    *,
    metadata_file: str | Path | None = None,
    priority: list[str] | None = None,
) -> tuple[str | None, dict[str, list[str]]]:
    """Return the best single year plus the evidence used to choose it."""
    sources = detect_year_sources(source_file, metadata_file=metadata_file)
    return choose_single_year(sources, priority=priority), sources
