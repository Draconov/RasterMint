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
    hardware_profile_id: str = ""
    hardware_mode: str = "visual"


BUILTIN_PRESETS: tuple[BuiltinPreset, ...] = (
    BuiltinPreset("clean-quantize", "Clean", "Nearest-palette conversion with a restrained 8-color retro set."),
    BuiltinPreset("game-boy", "Game Boy", "DMG four-shade handheld look.", hardware_profile_id="game-boy", hardware_mode="visual"),
    BuiltinPreset("game-boy-color", "Game Boy Color", "Game Boy Color handheld look with RGB555 colour depth.", hardware_profile_id="game-boy-color", hardware_mode="strict"),
    BuiltinPreset("game-boy-advance", "Game Boy Advance", "Game Boy Advance RGB555 colour depth and handheld raster.", hardware_profile_id="game-boy-advance", hardware_mode="strict"),
    BuiltinPreset("nes", "NES", "Nintendo Entertainment System palette with console-style raster limits.", hardware_profile_id="nes", hardware_mode="strict"),
    BuiltinPreset("snes", "SNES", "Super Nintendo / Super Famicom 15-bit colour look.", hardware_profile_id="snes", hardware_mode="strict"),
    BuiltinPreset("mega-drive", "Mega Drive", "Sega Mega Drive / Genesis RGB333 arcade-ish look.", hardware_profile_id="mega-drive", hardware_mode="strict"),
    BuiltinPreset("playstation", "PlayStation", "Sony PlayStation RGB555-style colour depth and console raster.", hardware_profile_id="playstation", hardware_mode="strict"),
    BuiltinPreset("apple-ii-hgr", "Apple II HGR", "Apple II hi-res approximation with chunky dithered colour fringing.", hardware_profile_id="apple-ii-hgr", hardware_mode="visual"),
    BuiltinPreset("c64-multicolor", "C64 Multi", "Commodore 64 multicolor bitmap look with cell-based limits.", hardware_profile_id="c64-multicolor", hardware_mode="strict"),
    BuiltinPreset("zx-spectrum", "ZX Spectrum", "Spectrum palette with 8×8 attribute-cell restrictions.", hardware_profile_id="zx-spectrum", hardware_mode="strict"),
    BuiltinPreset("cga-neon", "CGA Neon", "Cyan/magenta CGA high-intensity look with ordered dithering.", hardware_profile_id="cga-320", hardware_mode="strict"),
    BuiltinPreset("ega-crisp", "EGA Crisp", "Classic IBM EGA 16-colour conversion.", hardware_profile_id="ega-320", hardware_mode="strict"),
    BuiltinPreset("amiga-ocs", "Amiga OCS", "Amiga OCS low-res framebuffer with RGB444 colour quantisation.", hardware_profile_id="amiga-ocs", hardware_mode="strict"),
    BuiltinPreset("crt-ntsc", "CRT NTSC", "NTSC 4:3 display treatment with blur, scanlines and colour bleed.", hardware_profile_id="crt-ntsc", hardware_mode="visual"),
    BuiltinPreset("crt-pal", "CRT PAL", "PAL 4:3 display treatment with non-square pixels and softer bleed.", hardware_profile_id="crt-pal", hardware_mode="visual"),
    BuiltinPreset("monochrome-lcd", "Mono LCD", "Monochrome LCD look with muted four-colour palette.", hardware_profile_id="monochrome-lcd", hardware_mode="strict"),
    BuiltinPreset("halftone-print", "Halftone", "Small warm print palette with halftone dithering."),
    BuiltinPreset("green-crt", "Green CRT", "Monochrome green phosphor palette with scanlines and local contrast."),
    BuiltinPreset("vector", "Vector", "Posterized clean-line render inspired by vectorised retro poster art."),
)


_PROFILE_CACHE = {profile.id: profile for profile in load_builtin_profiles()}


def _find_profile(profile_id: str):
    return _PROFILE_CACHE.get(profile_id)


def _set_dither(settings: ProcessingSettings, algorithm: str, strength: float = 1.0, *, mix: float | None = None, serpentine: bool | None = None) -> None:
    for step in settings.effect_stack:
        if step.get("kind") == "Dither":
            params = step.setdefault("params", {})
            params["algorithm"] = algorithm
            params["strength"] = strength
            if mix is not None:
                params["mix"] = mix
            if serpentine is not None:
                params["serpentine"] = bool(serpentine)
            return


def _set_palette(settings: ProcessingSettings, name: str) -> None:
    record = find_palette(name)
    if record:
        settings.palette = list(record.colors)
        settings.palette_name = record.name
        settings.palette_author = "RasterMint palette library"
        settings.palette_source = record.source
        settings.palette_locks = [False] * len(settings.palette)


def _apply_profile(
    settings: ProcessingSettings,
    profile_id: str,
    *,
    mode: str = "visual",
    apply_constraints: bool = True,
    apply_display: bool = True,
) -> ProcessingSettings:
    profile = _find_profile(profile_id)
    if not profile:
        return settings
    return apply_profile_to_settings(
        settings,
        profile,
        mode=mode,
        apply_resolution=True,
        apply_palette=True,
        apply_pixel_aspect=True,
        apply_constraints=apply_constraints,
        apply_display=apply_display,
    )


def _insert_effect(settings: ProcessingSettings, effect: dict, index: int | None = None) -> None:
    if index is None:
        settings.effect_stack.append(effect)
    else:
        settings.effect_stack.insert(index, effect)


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
        settings = _apply_profile(settings, "game-boy", mode="visual", apply_constraints=False, apply_display=True)
        _set_dither(settings, "Bayer 4x4", 1.0)
    elif preset_id == "game-boy-color":
        settings = _apply_profile(settings, "game-boy-color", mode="strict")
        _set_dither(settings, "Nearest Palette", 1.0, serpentine=False)
    elif preset_id == "game-boy-advance":
        settings = _apply_profile(settings, "game-boy-advance", mode="strict")
        _set_dither(settings, "Nearest Palette", 1.0, serpentine=False)
        contrast = new_effect("Local Contrast"); contrast["params"].update(amount=135, radius=1.6)
        _insert_effect(settings, contrast, 1)
    elif preset_id == "nes":
        settings = _apply_profile(settings, "nes", mode="strict")
        _set_dither(settings, "Bayer 4x4", 0.95)
    elif preset_id == "snes":
        settings = _apply_profile(settings, "snes", mode="strict")
        _set_dither(settings, "Nearest Palette", 1.0, serpentine=False)
        sharpen = new_effect("Sharpen"); sharpen["enabled"] = True; sharpen["params"]["amount"] = 1.2
        _insert_effect(settings, sharpen, 4)
    elif preset_id == "mega-drive":
        settings = _apply_profile(settings, "mega-drive", mode="strict")
        _set_dither(settings, "Nearest Palette", 1.0, serpentine=False)
        contrast = new_effect("Local Contrast"); contrast["params"].update(amount=115, radius=1.4)
        _insert_effect(settings, contrast, 1)
    elif preset_id == "playstation":
        settings = _apply_profile(settings, "playstation", mode="strict")
        _set_dither(settings, "Nearest Palette", 1.0, serpentine=False)
        row = new_effect("Row Shift"); row["enabled"] = True; row["params"].update(amount=1, period=5)
        _insert_effect(settings, row)
    elif preset_id == "apple-ii-hgr":
        settings = _apply_profile(settings, "apple-ii-hgr", mode="visual", apply_constraints=False)
        _set_dither(settings, "Bayer 4x4", 1.0)
    elif preset_id == "c64-multicolor":
        settings = _apply_profile(settings, "c64-multicolor", mode="strict")
        _set_dither(settings, "Bayer 4x4", 0.9)
    elif preset_id == "zx-spectrum":
        settings = _apply_profile(settings, "zx-spectrum", mode="strict")
        _set_dither(settings, "Bayer 4x4", 0.9)
    elif preset_id == "cga-neon":
        settings = _apply_profile(settings, "cga-320", mode="strict")
        _set_dither(settings, "Bayer 4x4", 1.0)
    elif preset_id == "ega-crisp":
        settings = _apply_profile(settings, "ega-320", mode="strict")
        _set_dither(settings, "Floyd-Steinberg", 0.8)
    elif preset_id == "amiga-ocs":
        settings = _apply_profile(settings, "amiga-ocs", mode="strict")
        _set_dither(settings, "Nearest Palette", 1.0, serpentine=False)
    elif preset_id == "crt-ntsc":
        settings = _apply_profile(settings, "crt-ntsc", mode="visual", apply_constraints=False, apply_display=True)
        _set_dither(settings, "Nearest Palette", 1.0)
        pixelate = next((step for step in settings.effect_stack if step.get("kind") == "Pixelate"), None)
        if pixelate:
            pixelate["enabled"] = True
            pixelate.setdefault("params", {})["size"] = 2
    elif preset_id == "crt-pal":
        settings = _apply_profile(settings, "crt-pal", mode="visual", apply_constraints=False, apply_display=True)
        _set_dither(settings, "Nearest Palette", 1.0)
        pixelate = next((step for step in settings.effect_stack if step.get("kind") == "Pixelate"), None)
        if pixelate:
            pixelate["enabled"] = True
            pixelate.setdefault("params", {})["size"] = 2
    elif preset_id == "monochrome-lcd":
        settings = _apply_profile(settings, "monochrome-lcd", mode="strict")
        _set_dither(settings, "Bayer 4x4", 1.0)
        pixelate = next((step for step in settings.effect_stack if step.get("kind") == "Pixelate"), None)
        if pixelate:
            pixelate["enabled"] = True
            pixelate.setdefault("params", {})["size"] = 2
    elif preset_id == "halftone-print":
        settings.palette = ["#201A17", "#6F4A2F", "#C99255", "#F4E3B2"]
        settings.palette_name = "Warm Print 4"; settings.palette_author = "RasterMint"; settings.palette_source = "builtin"
        settings.palette_locks = [False] * len(settings.palette)
        _set_dither(settings, "Halftone", 1.0)
        local = new_effect("Local Contrast"); local["params"].update(amount=150, radius=1.5)
        _insert_effect(settings, local, 1)
    elif preset_id == "green-crt":
        _set_palette(settings, "MDA Green 4")
        _set_dither(settings, "Atkinson", 0.85)
        local = new_effect("Local Contrast"); local["params"].update(amount=150, radius=1.8)
        scan = new_effect("Scanlines"); scan["params"].update(spacing=3, strength=0.18)
        _insert_effect(settings, local, 1)
        _insert_effect(settings, scan)
    elif preset_id == "vector":
        settings.palette = ["#0E1116", "#2B3A67", "#5C80BC", "#C3E0E5", "#F8F5F2"]
        settings.palette_name = "Vector Poster 5"; settings.palette_author = "RasterMint"; settings.palette_source = "builtin"
        settings.palette_locks = [False] * len(settings.palette)
        _set_dither(settings, "Nearest Palette", 1.0, mix=1.0, serpentine=False)
        posterize = new_effect("Posterize"); posterize["enabled"] = True; posterize["params"]["levels"] = 5
        local = new_effect("Local Contrast"); local["params"].update(amount=180, radius=2.0)
        sharpen = new_effect("Sharpen"); sharpen["enabled"] = True; sharpen["params"]["amount"] = 1.4
        _insert_effect(settings, local, 1)
        _insert_effect(settings, sharpen, 5)
        _insert_effect(settings, posterize, 6)
    else:  # clean-quantize
        _set_palette(settings, "Arcade 8")
        _set_dither(settings, "Nearest Palette", 1.0)

    return ProcessingSettings.from_dict(settings.to_dict())
