"""Parser entrypoint for PLFS-like block tables."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from converters.plfs_industry_parser import parse as parse_plfs_industry


def parse(
    source_file: str | Path,
    output_file: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    """Use the proven PLFS industry adapter for compatible block tables."""
    result = parse_plfs_industry(source_file, output_file, **kwargs)
    result["parser"] = "plfs_block"
    return result
