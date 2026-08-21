# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from importlib import resources
import json
from pathlib import Path
import re
from typing import Any, Callable

from .palette_json import PALETTE_FORMAT, PALETTE_VERSION, normalize_palette_payload
from .settings import ProcessingSettings

PRESET_FORMAT = "rastermint-preset"
PRESET_VERSION = 1

_BUNDLED_INSTALLED = False
_BUNDLED_PRESET_FILES: dict[str, str] = {}
_ORIGINAL_BUILD_PRESET: Callable[..., ProcessingSettings] | None = None


def slugify_preset_name(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().casefold()).strip("-")
    return text or "preset"


def normalize_preset_payload(
    payload: dict[str, Any],
    *,
    fallback_id: str = "",
    fallback_name: str = "",
) -> dict[str, Any]:
    if payload.get("format") != PRESET_FORMAT:
        raise ValueError("Not a RasterMint preset")
    if int(payload.get("version", 0)) > PRESET_VERSION:
        raise ValueError("Preset was created by a newer RasterMint version")

    name = str(payload.get("name") or fallback_name).strip()
    preset_id = str(payload.get("id") or fallback_id).strip()
    if not preset_id and name:
        preset_id = slugify_preset_name(name)

    settings = payload.get("settings", {})
    if not isinstance(settings, dict):
        raise ValueError("Preset settings must be an object")

    return {
        "format": PRESET_FORMAT,
        "version": PRESET_VERSION,
        "id": preset_id,
        "name": name,
        "description": str(payload.get("description") or "").strip(),
        "settings": settings,
    }


def load_preset_payload(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Preset JSON must contain an object")
    return normalize_preset_payload(
        payload,
        fallback_id=source.stem,
        fallback_name=source.stem.replace("-", " ").title(),
    )


def save_preset(
    path: str | Path,
    settings: ProcessingSettings,
    *,
    preset_id: str = "",
    name: str = "",
    description: str = "",
) -> None:
    payload: dict[str, Any] = {
        "format": PRESET_FORMAT,
        "version": PRESET_VERSION,
    }
    if preset_id:
        payload["id"] = str(preset_id)
    if name:
        payload["name"] = str(name)
    if description:
        payload["description"] = str(description)
    payload["settings"] = settings.to_dict()
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_preset(path: str | Path) -> ProcessingSettings:
    payload = load_preset_payload(path)
    return ProcessingSettings.from_dict(payload["settings"])


def _load_bundled_preset(preset_id: str) -> ProcessingSettings:
    filename = _BUNDLED_PRESET_FILES[preset_id]
    resource = resources.files("rastermint").joinpath("data", "presets", filename)
    with resources.as_file(resource) as path:
        return load_preset(path)


def _merge_creative_settings(
    base: ProcessingSettings | None,
    preset: ProcessingSettings,
) -> ProcessingSettings:
    """Apply bundled creative settings without replacing source/animation state."""
    settings = ProcessingSettings.from_dict((base or ProcessingSettings()).to_dict())
    settings.effect_stack = preset.effect_stack
    settings.palette = list(preset.palette)
    settings.palette_locks = list(preset.palette_locks)
    settings.palette_name = preset.palette_name
    settings.palette_author = preset.palette_author
    settings.palette_source = preset.palette_source

    # Bundled creative presets intentionally leave crop, transforms, target
    # resolution, pixel aspect, grid, animation, and randomization preferences
    # alone. They do reset hardware/display simulation to a neutral canvas.
    settings.hardware_profile_id = preset.hardware_profile_id
    settings.hardware_mode = preset.hardware_mode
    settings.hardware_constraints_enabled = preset.hardware_constraints_enabled
    settings.hardware_constraints = dict(preset.hardware_constraints)
    settings.display_profile = dict(preset.display_profile)
    settings.display_mode = preset.display_mode
    return ProcessingSettings.from_dict(settings.to_dict())


def install_bundled_library() -> None:
    """Register data-driven palettes and built-in RasterMint preset JSON files."""
    global _BUNDLED_INSTALLED, _ORIGINAL_BUILD_PRESET, _BUNDLED_PRESET_FILES
    if _BUNDLED_INSTALLED:
        return

    from . import builtin_presets, palette_library

    palette_folder = resources.files("rastermint").joinpath(
        "data", "palettes", "extended"
    )

    existing_palette_ids = {item.id for item in palette_library.PALETTE_LIBRARY}
    additions = []
    if palette_folder.is_dir():
        for resource in sorted(palette_folder.iterdir(), key=lambda item: item.name.casefold()):
            if not resource.name.lower().endswith(".json"):
                continue
            payload = json.loads(resource.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("format") != PALETTE_FORMAT:
                continue
            if int(payload.get("version", 0)) > PALETTE_VERSION:
                continue
            raw = normalize_palette_payload(
                payload,
                fallback_id=resource.name.rsplit(".", 1)[0],
                fallback_name=resource.name.rsplit(".", 1)[0].replace("-", " ").title(),
            )
            palette_id = str(raw["id"])
            if palette_id in existing_palette_ids:
                continue
            additions.append(
                palette_library.PaletteRecord(
                    id=palette_id,
                    name=str(raw["name"]),
                    category=str(raw["category"]),
                    colors=tuple(raw["colors"]),
                    description=str(raw["description"]),
                    source=str(raw["source"] or "RasterMint palette library"),
                )
            )
            existing_palette_ids.add(palette_id)

    if additions:
        palette_library.PALETTE_LIBRARY = palette_library.PALETTE_LIBRARY + tuple(additions)
        palette_library.PALETTE_BY_ID = {
            item.id: item for item in palette_library.PALETTE_LIBRARY
        }
        palette_library.PALETTE_BY_NAME = {
            item.name: item for item in palette_library.PALETTE_LIBRARY
        }

    preset_folder = resources.files("rastermint").joinpath("data", "presets")
    existing_preset_ids = {item.id for item in builtin_presets.BUILTIN_PRESETS}
    preset_additions = []
    preset_files: dict[str, str] = {}

    if preset_folder.is_dir():
        for resource in sorted(preset_folder.iterdir(), key=lambda item: item.name.casefold()):
            if not resource.name.lower().endswith(".json"):
                continue
            try:
                payload = normalize_preset_payload(
                    json.loads(resource.read_text(encoding="utf-8")),
                    fallback_id=resource.name.rsplit(".", 1)[0],
                    fallback_name=resource.name.rsplit(".", 1)[0].replace("-", " ").title(),
                )
            except Exception:
                continue

            preset_id = str(payload["id"]).strip()
            name = str(payload["name"]).strip()
            if not preset_id or not name or preset_id in existing_preset_ids:
                continue

            preset_files[preset_id] = resource.name
            preset_additions.append(
                builtin_presets.BuiltinPreset(
                    preset_id,
                    name,
                    str(payload.get("description", "")),
                )
            )
            existing_preset_ids.add(preset_id)

    if preset_additions:
        builtin_presets.BUILTIN_PRESETS = (
            builtin_presets.BUILTIN_PRESETS + tuple(preset_additions)
        )

    _BUNDLED_PRESET_FILES = preset_files
    _ORIGINAL_BUILD_PRESET = builtin_presets.build_builtin_preset
    original = _ORIGINAL_BUILD_PRESET

    def build_builtin_preset_with_data(
        preset_id: str,
        base: ProcessingSettings | None = None,
    ) -> ProcessingSettings:
        if preset_id in _BUNDLED_PRESET_FILES:
            return _merge_creative_settings(base, _load_bundled_preset(preset_id))
        assert original is not None
        return original(preset_id, base)

    builtin_presets.build_builtin_preset = build_builtin_preset_with_data
    _BUNDLED_INSTALLED = True
