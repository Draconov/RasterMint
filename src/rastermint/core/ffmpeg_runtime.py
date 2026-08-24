# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""Locate RasterMint's deliberately lean bundled FFmpeg at runtime.

The release build may replace imageio-ffmpeg's much larger wheel-provided
executable with a smaller FFmpeg built specifically for RasterMint.  Keeping
this helper dependency-free means configuring FFmpeg does not pull the media
stack into application startup.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys


def _usable_executable(value: str | os.PathLike[str] | None) -> Path | None:
    if not value:
        return None
    try:
        path = Path(value).expanduser()
        return path if path.is_file() else None
    except (OSError, TypeError, ValueError):
        return None


def bundled_ffmpeg_path() -> Path | None:
    """Return RasterMint's lean FFmpeg if one is available.

    ``RASTERMINT_FFMPEG_EXE`` is useful for development/testing.  Frozen
    PyInstaller builds place the validated executable in ``rastermint_ffmpeg``
    beneath ``sys._MEIPASS``.
    """

    explicit = _usable_executable(os.environ.get("RASTERMINT_FFMPEG_EXE"))
    if explicit is not None:
        return explicit

    frozen_root = getattr(sys, "_MEIPASS", None)
    if not frozen_root:
        return None

    root = Path(frozen_root) / "rastermint_ffmpeg"
    names = ("ffmpeg.exe", "ffmpeg") if sys.platform == "win32" else ("ffmpeg", "ffmpeg.exe")
    for name in names:
        candidate = _usable_executable(root / name)
        if candidate is not None:
            return candidate
    # Keep explicit custom-build overrides robust even if their source basename
    # was versioned before PyInstaller copied it into the private folder.
    for pattern in (("ffmpeg*.exe", "ffmpeg*") if sys.platform == "win32" else ("ffmpeg*", "ffmpeg*.exe")):
        for candidate_path in sorted(root.glob(pattern)):
            candidate = _usable_executable(candidate_path)
            if candidate is not None:
                return candidate
    return None


def configure_bundled_ffmpeg() -> str | None:
    """Point imageio-ffmpeg at RasterMint's lean executable when present.

    Respect an explicit ``IMAGEIO_FFMPEG_EXE`` override.  Otherwise set it only
    if RasterMint's validated executable exists; imageio-ffmpeg then naturally
    falls back to its own wheel binary in development and non-optimized builds.
    """

    existing = _usable_executable(os.environ.get("IMAGEIO_FFMPEG_EXE"))
    if existing is not None:
        return str(existing)

    bundled = bundled_ffmpeg_path()
    if bundled is None:
        return None

    os.environ["IMAGEIO_FFMPEG_EXE"] = str(bundled)
    return str(bundled)
