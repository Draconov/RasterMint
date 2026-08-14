# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from pathlib import Path

from .settings import ProcessingSettings

PRESET_FORMAT = "rastermint-preset"
PRESET_VERSION = 1


def save_preset(path: str | Path, settings: ProcessingSettings) -> None:
    payload = {
        "format": PRESET_FORMAT,
        "version": PRESET_VERSION,
        "settings": settings.to_dict(),
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_preset(path: str | Path) -> ProcessingSettings:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("format") != PRESET_FORMAT:
        raise ValueError("Not a RasterMint preset")
    if int(payload.get("version", 0)) > PRESET_VERSION:
        raise ValueError("Preset was created by a newer RasterMint version")
    return ProcessingSettings.from_dict(payload.get("settings", {}))
