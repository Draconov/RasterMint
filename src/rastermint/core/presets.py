# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from .settings import ProcessingSettings

PRESET_FORMAT = "rastermint-preset"
PRESET_VERSION = 2


def slugify_preset_name(value: str) -> str:
    """Return a filesystem/id-safe preset slug.

    Kept in the core module because the persistent preset library uses the same
    naming rules for ids and filenames.
    """
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "preset"


def _hardware_reference(settings: ProcessingSettings) -> dict[str, str] | None:
    profile_id = str(settings.hardware_profile_id or "").strip()
    if not profile_id or profile_id == "custom":
        return None
    mode = str(settings.hardware_mode or "visual").strip().lower()
    if mode not in {"visual", "strict"}:
        mode = "visual"
    return {"profile_id": profile_id, "mode": mode}


def _validate_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("RasterMint preset JSON must contain an object")
    if payload.get("format") != PRESET_FORMAT:
        raise ValueError("Not a RasterMint preset")

    try:
        version = int(payload.get("version", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Preset has an invalid version") from exc
    if version < 1:
        raise ValueError("Preset has an invalid version")
    if version > PRESET_VERSION:
        raise ValueError("Preset was created by a newer RasterMint version")

    settings = payload.get("settings")
    if not isinstance(settings, dict):
        raise ValueError("Preset is missing its settings object")

    result = dict(payload)
    result["version"] = version
    result["settings"] = dict(settings)

    for key in ("id", "name", "description"):
        if key in result and result[key] is not None:
            result[key] = str(result[key])

    reference = result.get("hardware_reference")
    if reference is not None:
        if not isinstance(reference, dict):
            result.pop("hardware_reference", None)
        else:
            profile_id = str(reference.get("profile_id") or "").strip()
            mode = str(reference.get("mode") or "visual").strip().lower()
            if mode not in {"visual", "strict"}:
                mode = "visual"
            if profile_id:
                result["hardware_reference"] = {
                    "profile_id": profile_id,
                    "mode": mode,
                }
            else:
                result.pop("hardware_reference", None)
    return result


def load_preset_payload(path: str | Path) -> dict[str, Any]:
    """Load and validate a preset while preserving its library metadata."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return _validate_payload(payload)


def save_preset(
    path: str | Path,
    settings: ProcessingSettings,
    *,
    preset_id: str | None = None,
    name: str | None = None,
    description: str | None = None,
) -> None:
    """Save a RasterMint preset.

    The metadata arguments are optional so normal File > Save Preset usage and
    the persistent user preset library share one compatible file format.
    """
    payload: dict[str, Any] = {
        "format": PRESET_FORMAT,
        "version": PRESET_VERSION,
        "settings": settings.to_dict(),
    }

    if preset_id is not None:
        clean_id = str(preset_id).strip()
        if clean_id:
            payload["id"] = clean_id
    if name is not None:
        clean_name = str(name).strip()
        if clean_name:
            payload["name"] = clean_name
    if description is not None:
        payload["description"] = str(description).strip()

    reference = _hardware_reference(settings)
    if reference is not None:
        payload["hardware_reference"] = reference

    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_preset(path: str | Path) -> ProcessingSettings:
    payload = load_preset_payload(path)
    settings_data = payload["settings"]
    settings = ProcessingSettings.from_dict(settings_data)

    # Version 2 stores an explicit hardware reference as metadata as well as a
    # full settings snapshot. Let the explicit reference win so library presets
    # remain correctly associated with their intended hardware profile.
    reference = payload.get("hardware_reference")
    if isinstance(reference, dict):
        profile_id = str(reference.get("profile_id") or "").strip()
        mode = str(reference.get("mode") or "visual").strip().lower()
        if profile_id:
            settings.hardware_profile_id = profile_id
        if mode in {"visual", "strict"}:
            settings.hardware_mode = mode

    return settings
