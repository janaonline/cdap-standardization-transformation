"""Small text helpers shared by detectors, parsers, and validators."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


def clean_text(value: Any) -> str:
    """Return a compact string value while preserving real zeros."""
    if pd.isna(value):
        return ""
    text = str(value).replace("\xa0", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_column_name(value: Any) -> str:
    """Normalize a column label for tolerant matching."""
    text = clean_text(value).lower()
    text = text.replace("%", " pct ")
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def compact_key(value: Any) -> str:
    """Normalize text to alphanumeric only for alias lookups."""
    return re.sub(r"[^a-z0-9]+", "", normalize_column_name(value))


def is_blank(value: Any) -> bool:
    """True only for missing or empty values, not numeric zero."""
    return pd.isna(value) or clean_text(value) == ""


def contains_all(text: Any, needles: list[str]) -> bool:
    """Case-insensitive containment check for detector rules."""
    haystack = clean_text(text).lower()
    return all(needle.lower() in haystack for needle in needles)
