"""Adapter for the proven PLFS industry parser."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from utils.file_utils import ensure_dir, ensure_parent
from utils.year_utils import detect_best_single_year


def _load_legacy_module():
    legacy_path = Path(__file__).resolve().parent.parent / "legacy" / "convert_plfs_industry_to_raw_dynamic.py"
    spec = importlib.util.spec_from_file_location("legacy_plfs_industry", legacy_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load legacy PLFS parser from {legacy_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_with_year_name(source_file: Path, year: str, work_dir: Path) -> Path:
    """Legacy parser reads year from filename, so provide a local alias when needed."""
    if year in source_file.name:
        return source_file
    ensure_dir(work_dir)
    alias = work_dir / f"{source_file.stem}_{year}{source_file.suffix}"
    if not alias.exists() or alias.stat().st_mtime_ns < source_file.stat().st_mtime_ns:
        shutil.copy2(source_file, alias)
    return alias


def parse(
    source_file: str | Path,
    output_file: str | Path,
    *,
    sub_indicator_mapping_file: str | Path,
    metadata_file: str | Path | None = None,
    year_detection_priority: list[str] | None = None,
    work_dir: str | Path | None = None,
    detection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the current successful PLFS industry conversion into the bridge schema."""
    source_path = Path(source_file)
    output_path = ensure_parent(Path(output_file))
    working_dir = Path(work_dir) if work_dir else output_path.parent / ".parser_work"

    year, year_sources = detect_best_single_year(
        source_path,
        metadata_file=metadata_file,
        priority=year_detection_priority,
    )
    if not year:
        raise ValueError(
            "Could not detect a single source year for PLFS industry data. "
            "Review source_detection_report.xlsx and metadata UID values."
        )

    legacy = _load_legacy_module()
    parser_input = _source_with_year_name(source_path, year, working_dir)
    df = legacy.convert_plfs_to_raw_format(
        extracted_data_file=parser_input,
        sub_indicator_mapping_file=sub_indicator_mapping_file,
        output_file=output_path,
        sheet_name=0,
        include_all_column=False,
    )

    return {
        "success": True,
        "parser": "plfs_industry",
        "rows": int(len(df)),
        "output_file": str(output_path),
        "years_detected": [year],
        "year_sources": year_sources,
        "detection": detection or {},
    }
