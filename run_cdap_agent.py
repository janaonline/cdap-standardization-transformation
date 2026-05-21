#!/usr/bin/env python3
"""
CDAP Agent - Orchestration Wrapper

Reads a configuration file and runs a complete CDAP pipeline:
1. Step 1: Transform raw PLFS extracted data into raw format
2. Step 2: Standardize and create final CDAP outputs

Usage:
    python run_cdap_agent.py [config_file]

If config_file is not provided, defaults to config.json
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import Any, Dict, List


class CDAPAgent:
    def __init__(self, config_path: str = "config.json"):
        """Initialize the CDAP agent with configuration."""
        self.config_path = Path(config_path)
        self.config = None
        self.script_dir = Path(__file__).parent

    def load_config(self) -> bool:
        """Load and validate configuration file."""
        print(f"\n{'='*80}")
        print("CDAP ORCHESTRATION AGENT - Starting")
        print(f"{'='*80}\n")

        if not self.config_path.exists():
            print(f"[ERROR] Config file not found: {self.config_path}")
            return False

        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            print(f"[OK] Loaded config: {self.config_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            return False

    def validate_files(self) -> bool:
        """Validate that all required input files exist."""
        print("\n" + "-" * 80)
        print("STEP 0: Validating input files")
        print("-" * 80)

        required_files = {}

        input_cfg = self.config.get("input", {})
        required_files["extracted_input_file"] = input_cfg.get("extracted_data_file")
        required_files["sub_indicator_mapping_file"] = input_cfg.get("sub_indicator_mapping_file")

        dep_cfg = self.config.get("dependency_files", {})
        required_files["metadata_file"] = dep_cfg.get("metadata_file")
        required_files["indicators_file"] = dep_cfg.get("indicators_file")
        required_files["lat_long_file"] = dep_cfg.get("lat_long_file")
        required_files["taxonomy_file"] = dep_cfg.get("taxonomy_file")
        required_files["temporal_log_file"] = dep_cfg.get("temporal_log_file")

        scripts_cfg = self.config.get("scripts", {})
        required_files["transformation_script"] = scripts_cfg.get("transformation_script")
        required_files["standardization_script"] = scripts_cfg.get("standardization_script")

        all_valid = True

        for file_key, file_name in required_files.items():
            if not file_name:
                print(f"  [ERROR] Missing config entry: {file_key}")
                all_valid = False
                continue

            file_path = self.script_dir / file_name
            if file_path.exists():
                print(f"  [OK] {file_key}: {file_name}")
            else:
                print(f"  [ERROR] File not found: {file_name} (expected at {file_path})")
                all_valid = False

        if not all_valid:
            print(f"\n[ERROR] Some required files are missing.")
            return False

        return True

    def setup_output_dirs(self) -> bool:
        """Create output directories if they don't exist."""
        output_cfg = self.config.get("output", {})
        intermediate_dir = output_cfg.get("intermediate_output_dir", "output/intermediate")
        final_dir = output_cfg.get("final_output_dir", "output/final")

        for dir_path in [intermediate_dir, final_dir]:
            output_path = self.script_dir / dir_path
            try:
                output_path.mkdir(parents=True, exist_ok=True)
                print(f"  [OK] Created/verified directory: {dir_path}")
            except Exception as e:
                print(f"  [ERROR] Failed to create directory {dir_path}: {e}")
                return False

        return True

    def run_transformation_step(self) -> bool:
        """Step 1: Run the PLFS to raw format transformation."""
        print("\n" + "-" * 80)
        print("STEP 1: Running transformation (PLFS extracted -> raw format)")
        print("-" * 80)

        input_cfg = self.config.get("input", {})
        scripts_cfg = self.config.get("scripts", {})
        output_cfg = self.config.get("output", {})

        extracted_file = input_cfg.get("extracted_data_file")
        mapping_file = input_cfg.get("sub_indicator_mapping_file")
        transformation_script = scripts_cfg.get("transformation_script")
        intermediate_dir = output_cfg.get("intermediate_output_dir", "output/intermediate")
        intermediate_output = output_cfg.get("intermediate_output_file", "transformed_raw_format.xlsx")

        extracted_path = self.script_dir / extracted_file
        mapping_path = self.script_dir / mapping_file
        script_path = self.script_dir / transformation_script
        output_path = self.script_dir / intermediate_dir / intermediate_output

        print(f"  Input: {extracted_file}")
        print(f"  Mapping: {mapping_file}")
        print(f"  Script: {transformation_script}")
        print(f"  Output: {intermediate_dir}/{intermediate_output}")

        try:
            cmd = [
                sys.executable,
                str(script_path),
                str(extracted_path),
                str(mapping_path),
                str(output_path),
            ]

            print(f"\n  Running: {' '.join(cmd)}\n")
            result = subprocess.run(cmd, cwd=self.script_dir, capture_output=True, text=True)

            print(result.stdout)
            if result.stderr:
                print("[STDERR]", result.stderr)

            if result.returncode != 0:
                print(f"[ERROR] Transformation script failed with return code {result.returncode}")
                return False

            if output_path.exists():
                print(f"\n[OK] Transformation produced: {output_path}")
                return True
            else:
                print(f"[ERROR] Could not find transformation output file: {output_path}")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to run transformation: {e}")
            return False

    def run_standardization_step(self, transformed_file: str) -> bool:
        """Step 2: Run the CDAP standardization pipeline."""
        print("\n" + "-" * 80)
        print("STEP 2: Running standardization (raw format -> final CDAP output)")
        print("-" * 80)

        scripts_cfg = self.config.get("scripts", {})
        dep_cfg = self.config.get("dependency_files", {})
        output_cfg = self.config.get("output", {})

        standardization_script = scripts_cfg.get("standardization_script")
        intermediate_dir = output_cfg.get("intermediate_output_dir", "output/intermediate")
        final_dir = output_cfg.get("final_output_dir", "output/final")
        final_output = output_cfg.get("final_output_file", "final_cdap_output.xlsx")

        metadata_file = dep_cfg.get("metadata_file")
        indicators_file = dep_cfg.get("indicators_file")
        latlong_file = dep_cfg.get("lat_long_file")
        taxonomy_file = dep_cfg.get("taxonomy_file")
        temporal_log_file = dep_cfg.get("temporal_log_file")

        transformed_path = self.script_dir / intermediate_dir / transformed_file
        script_path = self.script_dir / standardization_script
        metadata_path = self.script_dir / metadata_file
        indicators_path = self.script_dir / indicators_file
        latlong_path = self.script_dir / latlong_file
        taxonomy_path = self.script_dir / taxonomy_file
        temporal_log_path = self.script_dir / temporal_log_file
        final_output_path = self.script_dir / final_dir / final_output
        final_output_csv = self.script_dir / final_dir / final_output.replace(".xlsx", ".csv")

        print(f"  Transformed raw: {transformed_file}")
        print(f"  Dependency files:")
        print(f"    - {metadata_file}")
        print(f"    - {indicators_file}")
        print(f"    - {latlong_file}")
        print(f"    - {taxonomy_file}")
        print(f"    - {temporal_log_file}")
        print(f"  Script: {standardization_script}")
        print(f"  Final output: {final_dir}/{final_output}")

        try:
            cmd = [
                sys.executable,
                str(script_path),
                str(transformed_path),
                str(taxonomy_path),
                str(latlong_path),
                str(metadata_path),
                str(indicators_path),
                str(temporal_log_path),
                str(final_output_path),
                str(final_output_csv),
                str(self.script_dir / final_dir / "Indicators_list_updated.xlsx"),
                str(self.script_dir / final_dir / "Temporal_indicator_log_updated.xlsx"),
                str(self.script_dir / final_dir / "indicator_mapping_generated.xlsx"),
                str(self.script_dir / final_dir / "metadata_year_mapping_used.xlsx"),
            ]

            print(f"\n  Running: {' '.join(cmd)}\n")
            result = subprocess.run(cmd, cwd=self.script_dir, capture_output=True, text=True)

            print(result.stdout)
            if result.stderr:
                print("[STDERR]", result.stderr)

            if result.returncode != 0:
                print(f"[ERROR] Standardization script failed with return code {result.returncode}")
                return False

            if final_output_path.exists() or final_output_csv.exists():
                print(f"\n[OK] Standardization completed.")
                if final_output_path.exists():
                    print(f"     Final XLSX: {final_output_path}")
                if final_output_csv.exists():
                    print(f"     Final CSV: {final_output_csv}")
                return True
            else:
                print(f"[ERROR] Expected output file not found: {final_output_path}")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to run standardization: {e}")
            return False

    def run_full_pipeline(self) -> bool:
        """Execute the complete pipeline."""
        if not self.load_config():
            return False

        if not self.validate_files():
            return False

        if not self.setup_output_dirs():
            return False

        if not self.run_transformation_step():
            return False

        intermediate_output = self.config.get("output", {}).get(
            "intermediate_output_file", "transformed_raw_format.xlsx"
        )

        if not self.run_standardization_step(intermediate_output):
            return False

        print("\n" + "=" * 80)
        print("CDAP ORCHESTRATION AGENT - ALL STEPS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\nFinal outputs are in: {self.script_dir / self.config.get('output', {}).get('final_output_dir', 'output/final')}")
        return True


def main():
    """Main entry point."""
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"

    agent = CDAPAgent(config_path=config_file)
    success = agent.run_full_pipeline()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
