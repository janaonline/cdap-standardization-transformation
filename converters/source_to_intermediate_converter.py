"""Stage 1 dispatcher: source file to common intermediate raw dataset."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any


PARSER_MODULES = {
    "plfs_industry": "converters.plfs_industry_parser",
    "plfs_block": "converters.plfs_block_parser",
    "ncrb_district_section": "converters.ncrb_district_section_parser",
    "flat_state_table": "converters.flat_state_table_parser",
    "wide_year_columns": "converters.wide_year_columns_parser",
    "multi_sheet_year": "converters.multi_sheet_year_parser",
    "ndap_tidy": "converters.ndap_tidy_parser",
}


def convert_source_to_intermediate(
    source_file: str | Path,
    output_file: str | Path,
    *,
    detection: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Route the source file to the parser chosen by format detection."""
    detected_format = detection.get("detected_format", "unknown")
    module_name = PARSER_MODULES.get(detected_format)
    if not module_name:
        raise ValueError(f"No parser registered for detected format: {detected_format}")

    input_cfg = config.get("input", {})
    year_cfg = config.get("year_detection", {})
    parser_module = importlib.import_module(module_name)
    return parser_module.parse(
        source_file,
        output_file,
        detection=detection,
        sub_indicator_mapping_file=input_cfg.get("sub_indicator_mapping_file"),
        metadata_file=input_cfg.get("metadata_file"),
        year_detection_priority=year_cfg.get("priority"),
        work_dir=Path(output_file).parent / ".parser_work",
    )
