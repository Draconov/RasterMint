# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from importlib.metadata import PackageNotFoundError, version as distribution_version
from pathlib import Path

__app_name__ = "RasterMint"


def _get_version() -> str:
    """Return the project version from the single VERSION source of truth."""
    # When running from a source checkout, use VERSION directly so changing the
    # file is reflected immediately without editing Python code.
    source_version = Path(__file__).resolve().parents[2] / "VERSION"
    if source_version.is_file():
        value = source_version.read_text(encoding="utf-8").strip()
        if value:
            return value

    # Installed/frozen builds receive the same version through package metadata.
    try:
        return distribution_version("rastermint")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _get_version()
