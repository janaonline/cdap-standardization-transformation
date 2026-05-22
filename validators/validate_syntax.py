#!/usr/bin/env python3
"""Compile all project Python files to catch syntax errors."""

from __future__ import annotations

import sys
from pathlib import Path


EXCLUDED_DIRS = {".git", ".venv", "__pycache__", "output"}


def iter_python_files(project_root: Path) -> list[Path]:
    """Return project Python files, excluding generated and environment folders."""
    files: list[Path] = []
    for path in project_root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(project_root).parts):
            continue
        files.append(path)
    return sorted(files)


def validate_python_syntax() -> bool:
    project_root = Path(__file__).resolve().parent.parent
    print("\n" + "=" * 80)
    print("CDAP AGENT - Python Syntax Validation")
    print("=" * 80 + "\n")

    all_valid = True
    for filepath in iter_python_files(project_root):
        relative = filepath.relative_to(project_root)
        try:
            with open(filepath, "r", encoding="utf-8") as handle:
                compile(handle.read(), str(filepath), "exec")
            print(f"[OK] {relative} - Syntax OK")
        except SyntaxError as exc:
            print(f"[ERROR] {relative} - SYNTAX ERROR: {exc}")
            all_valid = False
        except Exception as exc:
            print(f"[ERROR] {relative} - ERROR: {exc}")
            all_valid = False

    print("\n" + "=" * 80)
    print("[OK] ALL SCRIPTS VALID - Ready to run" if all_valid else "[ERROR] SOME SCRIPTS HAVE ERRORS")
    print("=" * 80 + "\n")
    return all_valid


if __name__ == "__main__":
    sys.exit(0 if validate_python_syntax() else 1)
