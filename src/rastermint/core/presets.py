# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from pathlib import Path

from .settings import ProcessingSettings

PRESET_FORMAT = "rastermint-preset"
PRESET_VERSION = 2


def _hardware_reference(settings: ProcessingSettings) -> dict[str, str] | None:
    profile_id = str(settings.hardware_profile_id or "").strip()
    if not profile_id or profile_id == "custom":
        return None
    return {
        "profile_id": profile_id,
        "mode": str(settings.hardware_mode or "visual"),
    }


def save_preset(path: str | Path, settings: ProcessingSettings) -> None:
    payload = {
        "format": PRESET_FORMAT,
        "version": PRESET_VERSION,
        "settings": settings.to_dict(),
    }
    reference = _hardware_reference(settings)
    if reference is not None:
        payload["hardware_reference"] = reference
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_preset(path: str | Path) -> ProcessingSettings:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("format") != PRESET_FORMAT:
        raise ValueError("Not a RasterMint preset")
    if int(payload.get("version", 0)) > PRESET_VERSION:
        raise ValueError("Preset was created by a newer RasterMint version")
    settings = ProcessingSettings.from_dict(payload.get("settings", {}))
    reference = payload.get("hardware_reference")
    if isinstance(reference, dict):
        profile_id = str(reference.get("profile_id") or "").strip()
        if profile_id and settings.hardware_profile_id == "custom":
            settings.hardware_profile_id = profile_id
        mode = str(reference.get("mode") or "").strip().lower()
        if mode in {"visual", "strict"} and settings.hardware_mode not in {"visual", "strict"}:
            settings.hardware_mode = mode
    return settings
