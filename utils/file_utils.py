"""Path and copy helpers for project-relative file operations."""

from __future__ import annotations

import shutil
from pathlib import Path


def resolve_path(project_root: Path, path_value: str | Path) -> Path:
    """Resolve a path from the project root unless it is already absolute."""
    path = Path(path_value)
    return path if path.is_absolute() else project_root / path


def ensure_dir(path: Path) -> Path:
    """Create a directory and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_parent(path: Path) -> Path:
    """Create a file's parent directory and return the file path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def copy_if_needed(source: Path, destination: Path) -> Path:
    """Copy when the destination is missing or older than the source."""
    ensure_parent(destination)
    if not destination.exists():
        shutil.copy2(source, destination)
        return destination

    source_stat = source.stat()
    destination_stat = destination.stat()
    if (
        source_stat.st_size != destination_stat.st_size
        or source_stat.st_mtime_ns > destination_stat.st_mtime_ns
    ):
        shutil.copy2(source, destination)
    return destination
