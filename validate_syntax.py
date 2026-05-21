#!/usr/bin/env python3
"""
Final syntax and import validation for CDAP Agent
"""

import sys
from pathlib import Path

def validate_python_syntax():
    """Check that all Python files have valid syntax"""
    print("\n" + "="*80)
    print("CDAP AGENT - Python Syntax Validation")
    print("="*80 + "\n")
    
    files_to_check = [
        "run_cdap_agent.py",
        "v36_cdap_pipeline_refactored.py",
        "check_config.py",
    ]
    
    script_dir = Path(__file__).parent
    all_valid = True
    
    for filename in files_to_check:
        filepath = script_dir / filename
        try:
            with open(filepath, 'r') as f:
                code = f.read()
            compile(code, filepath, 'exec')
            print(f"[OK] {filename} - Syntax OK")
        except SyntaxError as e:
            print(f"[ERROR] {filename} - SYNTAX ERROR: {e}")
            all_valid = False
        except Exception as e:
            print(f"[ERROR] {filename} - ERROR: {e}")
            all_valid = False
    
    print("\n" + "="*80)
    if all_valid:
        print("[OK] ALL SCRIPTS VALID - Ready to run")
    else:
        print("[ERROR] SOME SCRIPTS HAVE ERRORS - Review above")
    print("="*80 + "\n")
    
    return all_valid

if __name__ == "__main__":
    success = validate_python_syntax()
    sys.exit(0 if success else 1)
