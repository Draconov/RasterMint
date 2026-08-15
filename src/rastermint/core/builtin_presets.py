# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from dataclasses import dataclass

from .effect_stack import default_effect_stack, new_effect
from .hardware import apply_profile_to_settings, load_builtin_profiles
from .palette_library import find_palette
from .settings import ProcessingSettings


@dataclass(frozen=True)
class BuiltinPreset:
    id: str
    name: str
    description: str


BUILTIN_PRESETS: tuple[BuiltinPreset, ...] = (
    BuiltinPreset("clean-quantize", "Clean", "Nearest-palette conversion with a restrained 8-color retro set."),
    BuiltinPreset("game-boy", "Game Boy", "DMG four-shade handheld look."),
    BuiltinPreset("cga-neon", "CGA Neon", "Cyan/magenta CGA high-intensity look with ordered dithering."),
    BuiltinPreset("ega-crisp", "EGA Crisp", "Classic 16-color RGBI/EGA conversion."),
    BuiltinPreset("zx-spectrum", "ZX Spectrum", "Spectrum palette with attribute-style strict limits."),
    BuiltinPreset("c64-multicolor", "C64 Multi", "C64 palette and multicolor-style cell constraints."),
    BuiltinPreset("halftone-print", "Halftone", "Small warm print palette with halftone dithering."),
    BuiltinPreset("green-crt", "Green CRT", "Monochrome green phosphor palette with scanlines and local contrast."),
)


def _find_profile(profile_id: str):
    return next((profile for profile in load_builtin_profiles() if profile.id == profile_id), None)


def _set_dither(settings: ProcessingSettings, algorithm: str, strength: float = 1.0) -> None:
    for step in settings.effect_stack:
        if step.get("kind") == "Dither":
            step.setdefault("params", {})["algorithm"] = algorithm
            step["params"]["strength"] = strength
            return


def _set_palette(settings: ProcessingSettings, name: str) -> None:
    record = find_palette(name)
    if record:
        settings.palette = list(record.colors)
        settings.palette_name = record.name
        settings.palette_author = "RasterMint palette library"
        settings.palette_source = record.source
        settings.palette_locks = [False] * len(settings.palette)


def build_builtin_preset(preset_id: str, base: ProcessingSettings | None = None) -> ProcessingSettings:
    settings = ProcessingSettings.from_dict((base or ProcessingSettings()).to_dict())
    # Presets replace the creative stack but preserve source crop/transform and animation.
    settings.effect_stack = default_effect_stack(settings)
    settings.hardware_profile_id = "custom"
    settings.hardware_mode = "visual"
    settings.hardware_constraints_enabled = False
    settings.hardware_constraints = {}
    settings.display_profile = {}
    settings.display_mode = "corrected"

    if preset_id == "game-boy":
        profile = _find_profile("game-boy")
        if profile:
            settings = apply_profile_to_settings(settings, profile, mode="visual", apply_resolution=True, apply_palette=True, apply_pixel_aspect=True, apply_constraints=False, apply_display=True)
        _set_dither(settings, "Bayer 4x4", 1.0)
    elif preset_id == "cga-neon":
        _set_palette(settings, "CGA Palette 1 High")
        settings.target_enabled = True; settings.target_width = 320; settings.target_height = 200
        settings.pixel_aspect_x = 5.0; settings.pixel_aspect_y = 6.0
        _set_dither(settings, "Bayer 4x4", 1.0)
    elif preset_id == "ega-crisp":
        _set_palette(settings, "EGA 16")
        settings.target_enabled = True; settings.target_width = 320; settings.target_height = 200
        settings.pixel_aspect_x = 5.0; settings.pixel_aspect_y = 6.0
        _set_dither(settings, "Floyd-Steinberg", 0.8)
    elif preset_id == "zx-spectrum":
        profile = _find_profile("zx-spectrum")
        if profile:
            settings = apply_profile_to_settings(settings, profile, mode="strict", apply_resolution=True, apply_palette=True, apply_pixel_aspect=True, apply_constraints=True, apply_display=True)
        _set_dither(settings, "Bayer 4x4", 0.9)
    elif preset_id == "c64-multicolor":
        profile = _find_profile("c64-multicolor")
        if profile:
            settings = apply_profile_to_settings(settings, profile, mode="strict", apply_resolution=True, apply_palette=True, apply_pixel_aspect=True, apply_constraints=True, apply_display=True)
        _set_dither(settings, "Bayer 4x4", 0.9)
    elif preset_id == "halftone-print":
        settings.palette = ["#201A17", "#6F4A2F", "#C99255", "#F4E3B2"]
        settings.palette_name = "Warm Print 4"; settings.palette_author = "RasterMint"
        _set_dither(settings, "Halftone", 1.0)
        local = new_effect("Local Contrast"); local["params"].update(amount=150, radius=1.5)
        settings.effect_stack.insert(1, local)
    elif preset_id == "green-crt":
        _set_palette(settings, "MDA Green 4")
        _set_dither(settings, "Atkinson", 0.85)
        local = new_effect("Local Contrast"); local["params"].update(amount=150, radius=1.8)
        scan = new_effect("Scanlines"); scan["params"].update(spacing=3, strength=0.18)
        settings.effect_stack.insert(1, local); settings.effect_stack.insert(-1, scan)
    else:  # clean-quantize
        _set_palette(settings, "Arcade 8")
        _set_dither(settings, "Nearest Palette", 1.0)
    return ProcessingSettings.from_dict(settings.to_dict())
