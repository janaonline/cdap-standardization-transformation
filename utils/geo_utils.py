"""Geography-related detector helpers."""

from __future__ import annotations

from typing import Any

from utils.text_utils import normalize_column_name


STATE_COLUMN_NAMES = {"state", "state_ut", "state_union_territory", "state_name"}
DISTRICT_COLUMN_NAMES = {"district", "district_name"}


def is_state_column(value: Any) -> bool:
    name = normalize_column_name(value)
    return name in STATE_COLUMN_NAMES or name.startswith("state")


def is_district_column(value: Any) -> bool:
    name = normalize_column_name(value)
    return name in DISTRICT_COLUMN_NAMES or name.startswith("district")
