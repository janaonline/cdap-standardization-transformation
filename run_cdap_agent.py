#!/usr/bin/env python3
"""
CDAP Agent - generic two-stage data-processing orchestrator.

Stage 1: source_to_intermediate
Stage 2: intermediate_to_final
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from converters.format_detector import detect_source_format, write_mapping_review_report
from converters.source_to_intermediate_converter import convert_source_to_intermediate
from standardization.intermediate_to_cdap_standardizer import run_intermediate_to_final_standardization
from utils.file_utils import ensure_dir, resolve_path
from validators.final_output_validator import validate_final_output_file
from validators.input_type_detector import INTERMEDIATE_FORMAT, SOURCE_FORMAT, UNKNOWN, detect_input_type
from validators.intermediate_validator import normalize_intermediate_file, validate_intermediate_file


class CDAPAgent:
    """Production-style orchestrator for source and intermediate input flows."""

    def __init__(self, config_path: str = "config.json"):
        self.project_root = Path(__file__).resolve().parent
        self.config_path = resolve_path(self.project_root, config_path)
        self.config: dict[str, Any] = {}
        self.summary: dict[str, Any] = {
            "input_type_selected": "",
            "detected_format": "",
            "parser_used": "",
            "years_detected": [],
            "intermediate_rows": 0,
            "final_rows": 0,
            "intermediate_warnings": 0,
            "final_warnings": 0,
            "final_output_path": "",
        }

    def path(self, value: str | Path) -> Path:
        """Resolve a config path from the project root."""
        return resolve_path(self.project_root, value)

    def load_config(self) -> bool:
        print("\n" + "=" * 80)
        print("CDAP AGENT - Starting generic processing run")
        print("=" * 80)
        if not self.config_path.exists():
            print(f"[ERROR] Config file not found: {self.config_path}")
            return False
        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                self.config = json.load(handle)
            print(f"[OK] Loaded config: {self.config_path}")
            return True
        except Exception as exc:
            print(f"[ERROR] Failed to load config: {exc}")
            return False

    def output_paths(self) -> dict[str, Path]:
        output_cfg = self.config.get("output", {})
        intermediate_dir = self.path(output_cfg.get("intermediate_dir", "output/intermediate"))
        final_dir = self.path(output_cfg.get("final_dir", "output/final"))
        reports_dir = self.path(output_cfg.get("reports_dir", "output/reports"))
        return {
            "intermediate_dir": intermediate_dir,
            "final_dir": final_dir,
            "reports_dir": reports_dir,
            "intermediate_file": intermediate_dir / output_cfg.get("intermediate_file", "intermediate_raw_dataset.xlsx"),
            "final_file": final_dir / output_cfg.get("final_file", "final_cdap_output.xlsx"),
            "final_csv_file": final_dir / output_cfg.get("final_csv_file", "final_cdap_output.csv"),
            "source_detection_report": reports_dir / "source_detection_report.xlsx",
            "intermediate_validation_report": reports_dir / "intermediate_validation_report.xlsx",
            "final_validation_report": reports_dir / "final_validation_report.xlsx",
            "mapping_review_report": reports_dir / "mapping_review_report.xlsx",
            "updated_indicators_file": final_dir / "Indicators_list_updated.xlsx",
            "updated_temporal_log_file": final_dir / "Temporal_indicator_log_updated.xlsx",
            "indicator_mapping_file": final_dir / "indicator_mapping_generated.xlsx",
            "metadata_mapping_file": final_dir / "metadata_year_mapping_used.xlsx",
        }

    def setup_output_dirs(self) -> bool:
        paths = self.output_paths()
        for key in ["intermediate_dir", "final_dir", "reports_dir"]:
            try:
                ensure_dir(paths[key])
                print(f"[OK] Output directory ready: {paths[key]}")
            except Exception as exc:
                print(f"[ERROR] Could not create {paths[key]}: {exc}")
                return False
        return True

    def validate_reference_files(self) -> bool:
        input_cfg = self.config.get("input", {})
        required = [
            "metadata_file",
            "taxonomy_file",
            "indicators_file",
            "temporal_log_file",
            "lat_long_file",
        ]
        ok = True
        print("\nValidating reusable reference files:")
        for key in required:
            value = input_cfg.get(key)
            if not value:
                print(f"  [ERROR] Missing config input.{key}")
                ok = False
                continue
            path = self.path(value)
            if path.exists():
                print(f"  [OK] {key}: {value}")
            else:
                print(f"  [ERROR] Missing {key}: {path}")
                ok = False
        return ok

    def choose_input(self) -> dict[str, Any]:
        """Pick intermediate input when valid and preferred; otherwise source."""
        input_cfg = self.config.get("input", {})
        detection_cfg = self.config.get("input_detection", {})
        mode = self.config.get("mode", "auto")
        prefer_intermediate = detection_cfg.get("prefer_intermediate_if_present", True)
        allow_source = detection_cfg.get("allow_source_file", True)
        allow_intermediate = detection_cfg.get("allow_intermediate_file", True)

        source_path = self.path(input_cfg.get("source_file", "input/source_data.xlsx"))
        intermediate_path = self.path(input_cfg.get("intermediate_file", "input/intermediate_raw_dataset.xlsx"))

        intermediate_detection = detect_input_type(intermediate_path) if allow_intermediate else {
            "input_type": UNKNOWN,
            "reason": "Intermediate input disabled by config.",
        }
        source_detection = detect_input_type(source_path) if allow_source else {
            "input_type": UNKNOWN,
            "reason": "Source input disabled by config.",
        }

        print("\nInput selection:")
        print(f"  Intermediate candidate: {intermediate_path} -> {intermediate_detection['input_type']}")
        print(f"  Source candidate: {source_path} -> {source_detection['input_type']}")

        if mode == "intermediate":
            if intermediate_detection["input_type"] == INTERMEDIATE_FORMAT:
                return {"selected_type": INTERMEDIATE_FORMAT, "path": intermediate_path, "details": intermediate_detection}
            return {"selected_type": UNKNOWN, "path": intermediate_path, "details": intermediate_detection}

        if mode == "source":
            if source_detection["input_type"] in {SOURCE_FORMAT, INTERMEDIATE_FORMAT}:
                return {"selected_type": source_detection["input_type"], "path": source_path, "details": source_detection}
            return {"selected_type": UNKNOWN, "path": source_path, "details": source_detection}

        if prefer_intermediate and intermediate_detection["input_type"] == INTERMEDIATE_FORMAT:
            return {"selected_type": INTERMEDIATE_FORMAT, "path": intermediate_path, "details": intermediate_detection}

        if source_detection["input_type"] == INTERMEDIATE_FORMAT:
            return {"selected_type": INTERMEDIATE_FORMAT, "path": source_path, "details": source_detection}

        if source_detection["input_type"] == SOURCE_FORMAT:
            return {"selected_type": SOURCE_FORMAT, "path": source_path, "details": source_detection}

        if intermediate_detection["input_type"] == INTERMEDIATE_FORMAT:
            return {"selected_type": INTERMEDIATE_FORMAT, "path": intermediate_path, "details": intermediate_detection}

        reason = (
            f"Intermediate: {intermediate_detection.get('reason', '')}; "
            f"Source: {source_detection.get('reason', '')}"
        )
        return {"selected_type": UNKNOWN, "path": source_path, "details": {"reason": reason}}

    def prepare_intermediate_from_existing(self, input_file: Path) -> bool:
        paths = self.output_paths()
        print("\nStage 1 skipped: input is already intermediate format.")
        try:
            normalize_intermediate_file(input_file, paths["intermediate_file"])
            self.summary["input_type_selected"] = INTERMEDIATE_FORMAT
            self.summary["detected_format"] = "intermediate"
            self.summary["parser_used"] = "not_applicable"
            print(f"[OK] Normalized intermediate file: {paths['intermediate_file']}")
            return True
        except Exception as exc:
            print(f"[ERROR] Could not normalize intermediate input: {exc}")
            return False

    def convert_source_to_intermediate(self, source_file: Path) -> bool:
        paths = self.output_paths()
        parser_cfg = self.config.get("parser_settings", {})
        threshold = float(parser_cfg.get("confidence_threshold", 0.7))
        print("\nStage 1: source_to_intermediate")
        detection = detect_source_format(source_file, report_file=paths["source_detection_report"])
        self.summary["detected_format"] = detection.get("detected_format", "unknown")
        print(
            f"  Detected format: {detection.get('detected_format')} "
            f"(confidence {detection.get('confidence')})"
        )
        print(f"  Reason: {detection.get('reason')}")

        if detection.get("detected_format") == "intermediate":
            return self.prepare_intermediate_from_existing(source_file)

        if detection.get("detected_format") == "unknown" or float(detection.get("confidence", 0)) < threshold:
            report = write_mapping_review_report(
                source_file,
                detection=detection,
                report_file=paths["mapping_review_report"],
            )
            print(f"[ERROR] Source format is unknown. Mapping review report written: {report}")
            return False

        try:
            result = convert_source_to_intermediate(
                source_file,
                paths["intermediate_file"],
                detection=detection,
                config=self.config,
            )
        except Exception as exc:
            print(f"[ERROR] Source conversion failed: {exc}")
            return False

        self.summary["input_type_selected"] = SOURCE_FORMAT
        self.summary["parser_used"] = result.get("parser", detection.get("detected_format", ""))
        self.summary["years_detected"] = result.get("years_detected", [])
        print(f"[OK] Stage 1 complete: {result.get('rows', 0)} rows -> {paths['intermediate_file']}")
        return bool(result.get("success"))

    def validate_intermediate(self) -> bool:
        paths = self.output_paths()
        result = validate_intermediate_file(
            paths["intermediate_file"],
            report_file=paths["intermediate_validation_report"],
        )
        self.summary["intermediate_rows"] = result.get("rows", 0)
        self.summary["intermediate_warnings"] = len(result.get("warnings", []))
        if not self.summary["years_detected"]:
            self.summary["years_detected"] = result.get("unique_years", [])
        print("\nIntermediate validation:")
        print(f"  Rows: {result.get('rows', 0)}")
        print(f"  Warnings: {len(result.get('warnings', []))}")
        print(f"  Report: {result.get('report_file')}")
        if result.get("errors"):
            for error in result["errors"]:
                print(f"  [ERROR] {error}")
        return bool(result.get("success"))

    def run_standardization(self) -> bool:
        paths = self.output_paths()
        input_cfg = self.config.get("input", {})
        print("\nStage 2: intermediate_to_final")
        result = run_intermediate_to_final_standardization(
            intermediate_file=str(paths["intermediate_file"]),
            metadata_file=str(self.path(input_cfg["metadata_file"])),
            taxonomy_file=str(self.path(input_cfg["taxonomy_file"])),
            indicators_file=str(self.path(input_cfg["indicators_file"])),
            temporal_log_file=str(self.path(input_cfg["temporal_log_file"])),
            lat_long_file=str(self.path(input_cfg["lat_long_file"])),
            final_output_file=str(paths["final_file"]),
            final_csv_file=str(paths["final_csv_file"]),
            updated_indicators_file=str(paths["updated_indicators_file"]),
            updated_temporal_log_file=str(paths["updated_temporal_log_file"]),
            indicator_mapping_file=str(paths["indicator_mapping_file"]),
            metadata_mapping_file=str(paths["metadata_mapping_file"]),
        )
        if not result.get("success"):
            print(f"[ERROR] Stage 2 failed: {result.get('error')}")
            return False
        self.summary["final_rows"] = result.get("rows_created", 0)
        self.summary["final_output_path"] = result.get("final_output_file", str(paths["final_file"]))
        print(f"[OK] Stage 2 complete: {self.summary['final_rows']} final rows")
        return True

    def validate_final(self) -> bool:
        paths = self.output_paths()
        final_path = Path(self.summary["final_output_path"] or paths["final_file"])
        result = validate_final_output_file(
            final_path,
            intermediate_rows=self.summary.get("intermediate_rows"),
            report_file=paths["final_validation_report"],
        )
        self.summary["final_warnings"] = len(result.get("warnings", []))
        print("\nFinal validation:")
        print(f"  Rows: {result.get('rows', 0)}")
        print(f"  Warnings: {len(result.get('warnings', []))}")
        print(f"  Report: {result.get('report_file')}")
        if result.get("errors"):
            for error in result["errors"]:
                print(f"  [ERROR] {error}")
        return bool(result.get("success"))

    def print_summary(self) -> None:
        print("\n" + "=" * 80)
        print("CDAP AGENT - Final summary")
        print("=" * 80)
        print(f"Input type selected: {self.summary['input_type_selected']}")
        print(f"Detected source format: {self.summary['detected_format']}")
        print(f"Parser used: {self.summary['parser_used']}")
        print(f"Years detected: {', '.join(map(str, self.summary['years_detected']))}")
        print(f"Intermediate rows: {self.summary['intermediate_rows']}")
        print(f"Final rows: {self.summary['final_rows']}")
        print(f"Intermediate validation warnings: {self.summary['intermediate_warnings']}")
        print(f"Final validation warnings: {self.summary['final_warnings']}")
        print(f"Final output path: {self.summary['final_output_path']}")

    def run(self) -> bool:
        if not self.load_config():
            return False
        if not self.setup_output_dirs():
            return False
        if not self.validate_reference_files():
            return False

        selection = self.choose_input()
        if selection["selected_type"] == UNKNOWN:
            paths = self.output_paths()
            write_mapping_review_report(
                selection["path"],
                detection={
                    "detected_format": "unknown",
                    "confidence": 0,
                    "reason": selection["details"].get("reason", "No usable input found."),
                },
                report_file=paths["mapping_review_report"],
            )
            print(f"[ERROR] No usable input found. See {paths['mapping_review_report']}")
            return False

        if selection["selected_type"] == INTERMEDIATE_FORMAT:
            if not self.prepare_intermediate_from_existing(selection["path"]):
                return False
        else:
            if not self.convert_source_to_intermediate(selection["path"]):
                return False

        if not self.validate_intermediate():
            return False
        if not self.run_standardization():
            return False
        if not self.validate_final():
            return False

        self.print_summary()
        return True


def main() -> None:
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    agent = CDAPAgent(config_file)
    sys.exit(0 if agent.run() else 1)


if __name__ == "__main__":
    main()
