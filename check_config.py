#!/usr/bin/env python3
"""
Quick validation script to check CDAP Agent configuration and file setup
"""

import json
import sys
from pathlib import Path

def check_files():
    """Check if all required files exist"""
    print("\n" + "="*80)
    print("CDAP AGENT - Configuration & File Check")
    print("="*80 + "\n")
    
    script_dir = Path(__file__).parent
    
    # Load config
    config_file = script_dir / "config.json"
    if not config_file.exists():
        print(f"[ERROR] config.json not found at {config_file}")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"[OK] Config loaded: {config_file}\n")
    except Exception as e:
        print(f"[ERROR] Failed to parse config.json: {e}")
        return False
    
    all_exist = True
    
    # Check input files
    print("INPUT FILES:")
    for key, filename in config.get("input", {}).items():
        file_path = script_dir / filename
        status = "[OK]" if file_path.exists() else "[MISSING]"
        print(f"  {status} {key}: {filename}")
        if not file_path.exists():
            all_exist = False
    
    # Check dependency files
    print("\nDEPENDENCY FILES:")
    for key, filename in config.get("dependency_files", {}).items():
        file_path = script_dir / filename
        status = "[OK]" if file_path.exists() else "[MISSING]"
        print(f"  {status} {key}: {filename}")
        if not file_path.exists():
            all_exist = False
    
    # Check scripts
    print("\nSCRIPTS:")
    for key, filename in config.get("scripts", {}).items():
        file_path = script_dir / filename
        status = "[OK]" if file_path.exists() else "[MISSING]"
        print(f"  {status} {key}: {filename}")
        if not file_path.exists():
            all_exist = False
    
    # Check orchestration script
    orchestrator = script_dir / "run_cdap_agent.py"
    status = "[OK]" if orchestrator.exists() else "[MISSING]"
    print(f"\nORCHESTRATOR:")
    print(f"  {status} run_cdap_agent.py")
    if not orchestrator.exists():
        all_exist = False
    
    print("\n" + "="*80)
    if all_exist:
        print("[OK] ALL FILES PRESENT - Ready to run: python run_cdap_agent.py")
        print("="*80 + "\n")
        return True
    else:
        print("[ERROR] MISSING FILES - Check paths in config.json or verify files are in the same folder")
        print("="*80 + "\n")
        return False

if __name__ == "__main__":
    success = check_files()
    sys.exit(0 if success else 1)
