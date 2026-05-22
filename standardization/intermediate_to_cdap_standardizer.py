"""Stage 2 adapter for the current CDAP standardization business logic."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_legacy_standardizer():
    legacy_path = Path(__file__).resolve().parent.parent / "legacy" / "v36_cdap_pipeline_refactored.py"
    spec = importlib.util.spec_from_file_location("legacy_cdap_standardizer", legacy_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load legacy standardizer from {legacy_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_intermediate_to_final_standardization(
    intermediate_file: str,
    metadata_file: str,
    taxonomy_file: str,
    indicators_file: str,
    temporal_log_file: str,
    lat_long_file: str,
    final_output_file: str,
    final_csv_file: str,
    updated_indicators_file: str,
    updated_temporal_log_file: str,
    indicator_mapping_file: str,
    metadata_mapping_file: str,
) -> dict[str, Any]:
    """Run Stage 2 while preserving the proven standardization rules."""
    standardizer = _load_legacy_standardizer()
    result = standardizer.run_cdap_pipeline(
        raw_file=intermediate_file,
        taxonomy_file=taxonomy_file,
        latlong_file=lat_long_file,
        metadata_file=metadata_file,
        indicator_master_file=indicators_file,
        temporal_log_file=temporal_log_file,
        output_final_xlsx=final_output_file,
        output_final_csv=final_csv_file,
        output_indicator_master_xlsx=updated_indicators_file,
        output_temporal_log_xlsx=updated_temporal_log_file,
        output_mapping_xlsx=indicator_mapping_file,
        output_metadata_mapping_xlsx=metadata_mapping_file,
    )
    return {
        "success": bool(result.get("success")),
        "rows_created": int(result.get("rows_created", 0) or 0),
        "final_output_file": result.get("final_output") or final_output_file,
        "final_csv_file": result.get("final_output_csv") or final_csv_file,
        "error": result.get("error"),
        "intermediate_outputs": result.get("intermediate_outputs", []),
    }
