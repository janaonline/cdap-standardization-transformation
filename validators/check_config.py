#!/usr/bin/env python3
"""Validate CDAP Agent config paths and input-selection readiness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.file_utils import resolve_path
from validators.input_type_detector import INTERMEDIATE_FORMAT, SOURCE_FORMAT, detect_input_type


def check_files() -> bool:
    """Check required reference files and at least one usable input candidate."""
    project_root = PROJECT_ROOT
    config_file = project_root / "config.json"

    print("\n" + "=" * 80)
    print("CDAP AGENT - Configuration & File Check")
    print("=" * 80 + "\n")

    if not config_file.exists():
        print(f"[ERROR] config.json not found at {config_file}")
        return False

    try:
        with open(config_file, "r", encoding="utf-8") as handle:
            config = json.load(handle)
        print(f"[OK] Config loaded: {config_file}\n")
    except Exception as exc:
        print(f"[ERROR] Failed to parse config.json: {exc}")
        return False

    input_cfg = config.get("input", {})
    detection_cfg = config.get("input_detection", {})
    all_valid = True

    def path_for(key: str) -> Path:
        return resolve_path(project_root, input_cfg.get(key, ""))

    print("INPUT CANDIDATES:")
    source_path = path_for("source_file")
    intermediate_path = path_for("intermediate_file")
    source_detection = detect_input_type(source_path)
    intermediate_detection = detect_input_type(intermediate_path)

    if detection_cfg.get("allow_source_file", True):
        print(f"  [{source_detection['input_type']}] source_file: {source_path}")
    if detection_cfg.get("allow_intermediate_file", True):
        print(f"  [{intermediate_detection['input_type']}] intermediate_file: {intermediate_path}")

    usable_input = (
        source_detection["input_type"] in {SOURCE_FORMAT, INTERMEDIATE_FORMAT}
        or intermediate_detection["input_type"] == INTERMEDIATE_FORMAT
    )
    if not usable_input:
        print("  [ERROR] No source or intermediate input is currently usable.")
        all_valid = False

    print("\nREFERENCE FILES:")
    for key in [
        "metadata_file",
        "taxonomy_file",
        "indicators_file",
        "temporal_log_file",
        "lat_long_file",
    ]:
        file_path = path_for(key)
        status = "[OK]" if file_path.exists() else "[MISSING]"
        print(f"  {status} {key}: {file_path}")
        if not file_path.exists():
            all_valid = False

    sub_mapping = path_for("sub_indicator_mapping_file")
    status = "[OK]" if sub_mapping.exists() else "[MISSING]"
    print(f"  {status} sub_indicator_mapping_file: {sub_mapping}")
    if detection_cfg.get("allow_source_file", True) and source_path.exists() and not sub_mapping.exists():
        all_valid = False

    print("\nOUTPUT FOLDERS:")
    output_cfg = config.get("output", {})
    for key in ["intermediate_dir", "final_dir", "reports_dir"]:
        folder = resolve_path(project_root, output_cfg.get(key, ""))
        print(f"  [OK] {key}: {folder}")

    print("\n" + "=" * 80)
    if all_valid:
        print("[OK] CONFIGURATION READY - Run: python run_cdap_agent.py")
    else:
        print("[ERROR] CONFIGURATION NEEDS ATTENTION - Review missing files above")
    print("=" * 80 + "\n")
    return all_valid


if __name__ == "__main__":
    sys.exit(0 if check_files() else 1)
