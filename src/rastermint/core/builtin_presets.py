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
    BuiltinPreset("game-boy-pocket", "Game Boy Pocket", "Silvery monochrome handheld look using the Pocket palette."),
    BuiltinPreset("game-boy-light", "Game Boy Light", "Mint-green backlit handheld look inspired by Game Boy Light."),
    BuiltinPreset("game-boy-color", "Game Boy Color", "Game Boy Color handheld look with RGB555 colour depth.", hardware_profile_id="game-boy-color", hardware_mode="strict"),
    BuiltinPreset("game-boy-advance", "Game Boy Advance", "Game Boy Advance RGB555 colour depth and handheld raster.", hardware_profile_id="game-boy-advance", hardware_mode="strict"),
    BuiltinPreset("virtual-boy", "Virtual Boy", "Red-on-black stereoscopic handheld palette."),
    BuiltinPreset("nes", "NES", "Nintendo Entertainment System palette with console-style raster limits.", hardware_profile_id="nes", hardware_mode="strict"),
    BuiltinPreset("snes", "SNES", "Super Nintendo / Super Famicom 15-bit colour look.", hardware_profile_id="snes", hardware_mode="strict"),
    BuiltinPreset("master-system", "Master System", "Sega Master System 16-colour look."),
    BuiltinPreset("game-gear", "Game Gear", "Sega Game Gear portable palette."),
    BuiltinPreset("mega-drive", "Mega Drive", "Sega Mega Drive / Genesis RGB333 arcade-ish look.", hardware_profile_id="mega-drive", hardware_mode="strict"),
    BuiltinPreset("playstation", "PlayStation", "Sony PlayStation RGB555-style colour depth and console raster.", hardware_profile_id="playstation", hardware_mode="strict"),
    BuiltinPreset("apple-ii-hgr", "Apple II HGR", "Apple II hi-res approximation with chunky dithered colour fringing.", hardware_profile_id="apple-ii-hgr", hardware_mode="visual"),
    BuiltinPreset("c64-multicolor", "C64 Multi", "Commodore 64 multicolor bitmap look with cell-based limits.", hardware_profile_id="c64-multicolor", hardware_mode="strict"),
    BuiltinPreset("vic-20", "VIC-20", "Commodore VIC-20 pastel 8-bit palette."),
    BuiltinPreset("plus4", "Plus/4", "Commodore Plus/4 palette with slightly softer retro colour."),
    BuiltinPreset("zx-spectrum", "ZX Spectrum", "Spectrum palette with 8×8 attribute-cell restrictions.", hardware_profile_id="zx-spectrum", hardware_mode="strict"),
    BuiltinPreset("cga-neon", "CGA Neon", "Cyan/magenta CGA high-intensity look with ordered dithering.", hardware_profile_id="cga-320", hardware_mode="strict"),
    BuiltinPreset("ega-crisp", "EGA Crisp", "Classic IBM EGA 16-colour conversion.", hardware_profile_id="ega-320", hardware_mode="strict"),
    BuiltinPreset("amiga-ocs", "Amiga OCS", "Amiga OCS low-res framebuffer with RGB444 colour quantisation.", hardware_profile_id="amiga-ocs", hardware_mode="strict"),
    BuiltinPreset("amiga-wb13", "Amiga WB 1.3", "Workbench 1.3-inspired desktop palette."),
    BuiltinPreset("amiga-wb2", "Amiga WB 2.x", "Workbench 2.x-inspired neutral Amiga palette."),
    BuiltinPreset("amiga-wb3", "Amiga WB 3.x", "Workbench 3.x-inspired colourful Amiga palette."),
    BuiltinPreset("amstrad-cpc", "Amstrad CPC", "Amstrad CPC vivid 27-colour microcomputer look."),
    BuiltinPreset("msx", "MSX", "MSX home-computer palette with saturated primaries."),
    BuiltinPreset("ti994a", "TI-99/4A", "Texas Instruments TI-99/4A palette look."),
    BuiltinPreset("crt-ntsc", "CRT NTSC", "NTSC 4:3 display treatment with blur, scanlines and colour bleed.", hardware_profile_id="crt-ntsc", hardware_mode="visual"),
    BuiltinPreset("crt-pal", "CRT PAL", "PAL 4:3 display treatment with non-square pixels and softer bleed.", hardware_profile_id="crt-pal", hardware_mode="visual"),
    BuiltinPreset("monochrome-lcd", "Mono LCD", "Monochrome LCD look with muted four-colour palette.", hardware_profile_id="monochrome-lcd", hardware_mode="strict"),
    BuiltinPreset("green-crt", "Green CRT", "Monochrome green phosphor palette with scanlines and local contrast."),
    BuiltinPreset("amber-monitor", "Amber Monitor", "Warm amber monochrome monitor look."),
    BuiltinPreset("white-phosphor", "White Phosphor", "Bright white phosphor monitor look."),
    BuiltinPreset("halftone-print", "Halftone", "Small warm print palette with halftone dithering."),
    BuiltinPreset("mac-classic", "Classic Mac", "Classic Macintosh 1-bit black-and-white look."),
    BuiltinPreset("mac-gray", "Mac Gray", "Compact Macintosh grayscale palette."),
    BuiltinPreset("atari-st", "Atari ST", "Atari ST 16-colour desktop-era look."),
    BuiltinPreset("atari-8bit", "Atari 8-bit", "Atari 8-bit home-computer palette."),
    BuiltinPreset("teletext", "Teletext", "Broadcast teletext-style limited palette look."),
    BuiltinPreset("oric-atmos", "Oric Atmos", "Oric Atmos 8-colour microcomputer look."),
    BuiltinPreset("dragon-coco", "Dragon / CoCo", "Dragon / TRS-80 CoCo reference palette look."),
    BuiltinPreset("coco3", "CoCo 3", "Color Computer 3 16-colour look."),
    BuiltinPreset("pc98", "PC-98", "Japanese PC-98 16-colour computer look."),
    BuiltinPreset("x68000", "X68000", "Sharp X68000 16-colour arcade-computer look."),
    BuiltinPreset("fmtowns", "FM Towns", "FM Towns late-80s multimedia-computer palette."),
    BuiltinPreset("sam-coupe", "SAM Coupé", "SAM Coupé colourful British microcomputer look."),
    BuiltinPreset("thomson", "Thomson TO7/MO5", "Thomson TO7/MO5 French microcomputer palette."),
    BuiltinPreset("intellivision", "Intellivision", "Mattel Intellivision console palette."),
    BuiltinPreset("colecovision", "ColecoVision", "ColecoVision console palette."),
    BuiltinPreset("neo-geo-pocket", "Neo Geo Pocket", "Neo Geo Pocket grayscale handheld look."),
    BuiltinPreset("wonderswan", "WonderSwan", "Bandai WonderSwan grayscale handheld look."),
    BuiltinPreset("pico-8", "PICO-8", "Fantasy-console 16-colour palette with crunchy contrast."),
    BuiltinPreset("tic-80", "TIC-80", "Fantasy-console TIC-80 palette with bright game-like colours."),
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


def _enable_pixelate(settings: ProcessingSettings, size: int) -> None:
    pixelate = next((step for step in settings.effect_stack if step.get("kind") == "Pixelate"), None)
    if pixelate:
        pixelate["enabled"] = True
        pixelate.setdefault("params", {})["size"] = int(size)


def _configure_palette_preset(
    settings: ProcessingSettings,
    palette_name: str,
    *,
    dither: str = "Nearest Palette",
    strength: float = 1.0,
    serpentine: bool | None = None,
    target: tuple[int, int] | None = None,
    pixel_aspect: tuple[float, float] | None = None,
    pixelate: int | None = None,
) -> None:
    _set_palette(settings, palette_name)
    _set_dither(settings, dither, strength, serpentine=serpentine)
    if target is not None:
        settings.target_enabled = True
        settings.target_width = int(target[0])
        settings.target_height = int(target[1])
    if pixel_aspect is not None:
        settings.pixel_aspect_x = float(pixel_aspect[0])
        settings.pixel_aspect_y = float(pixel_aspect[1])
    if pixelate is not None:
        _enable_pixelate(settings, pixelate)


def _clean_preset_base(base: ProcessingSettings | None) -> ProcessingSettings:
    settings = ProcessingSettings()
    if base is None:
        return settings

    # Preserve only source-transform / framing context and optional animation.
    settings.fit_mode = str(base.fit_mode)
    settings.position_x = float(base.position_x)
    settings.position_y = float(base.position_y)
    settings.rotation = int(base.rotation)
    settings.flip_horizontal = bool(base.flip_horizontal)
    settings.flip_vertical = bool(base.flip_vertical)
    settings.mirror_horizontal = bool(base.mirror_horizontal)
    settings.mirror_vertical = bool(base.mirror_vertical)
    settings.mirror_horizontal_axis = float(base.mirror_horizontal_axis)
    settings.mirror_vertical_axis = float(base.mirror_vertical_axis)
    settings.crop_left = float(base.crop_left)
    settings.crop_top = float(base.crop_top)
    settings.crop_right = float(base.crop_right)
    settings.crop_bottom = float(base.crop_bottom)

    settings.animation_duration = float(base.animation_duration)
    settings.animation_fps = int(base.animation_fps)
    settings.animation_loop = bool(base.animation_loop)
    settings.animation_tracks = [dict(track) for track in base.animation_tracks]
    return settings


def build_builtin_preset(preset_id: str, base: ProcessingSettings | None = None) -> ProcessingSettings:
    # Built-in presets must be deterministic. Start from a clean base and only
    # preserve source framing / transform context instead of inheriting the
    # previous preset's creative/render state.
    settings = _clean_preset_base(base)
    settings.effect_stack = default_effect_stack(settings)
    settings.hardware_profile_id = "custom"
    settings.hardware_mode = "visual"
    settings.hardware_constraints_enabled = False
    settings.hardware_constraints = {}
    settings.display_profile = {}
    settings.display_mode = "corrected"
    settings.display_export = False
    settings.target_enabled = False
    settings.target_width = 0
    settings.target_height = 0
    settings.pixel_aspect_x = 1.0
    settings.pixel_aspect_y = 1.0

    if preset_id == "game-boy":
        settings = _apply_profile(settings, "game-boy", mode="visual", apply_constraints=False, apply_display=True)
        _set_dither(settings, "Bayer 4x4", 1.0)
    elif preset_id == "game-boy-pocket":
        _configure_palette_preset(settings, "Game Boy Pocket", dither="Bayer 4x4", strength=1.0, target=(160, 144), pixelate=2)
    elif preset_id == "game-boy-light":
        _configure_palette_preset(settings, "Game Boy Light", dither="Bayer 4x4", strength=1.0, target=(160, 144), pixelate=2)
    elif preset_id == "game-boy-color":
        settings = _apply_profile(settings, "game-boy-color", mode="strict")
        _set_dither(settings, "Nearest Palette", 1.0, serpentine=False)
    elif preset_id == "game-boy-advance":
        settings = _apply_profile(settings, "game-boy-advance", mode="strict")
        _set_dither(settings, "Nearest Palette", 1.0, serpentine=False)
        contrast = new_effect("Local Contrast")
        contrast["params"].update(amount=135, radius=1.6)
        _insert_effect(settings, contrast, 1)
    elif preset_id == "virtual-boy":
        _configure_palette_preset(settings, "Virtual Boy", dither="Bayer 4x4", strength=1.0, target=(384, 224), pixelate=2)
    elif preset_id == "nes":
        settings = _apply_profile(settings, "nes", mode="strict")
        _set_dither(settings, "Bayer 4x4", 0.95)
    elif preset_id == "snes":
        settings = _apply_profile(settings, "snes", mode="strict")
        _set_dither(settings, "Nearest Palette", 1.0, serpentine=False)
        sharpen = new_effect("Sharpen")
        sharpen["enabled"] = True
        sharpen["params"]["amount"] = 1.2
        _insert_effect(settings, sharpen, 4)
    elif preset_id == "master-system":
        _configure_palette_preset(settings, "Master System Reference 16", dither="Floyd-Steinberg", strength=0.9, target=(256, 192), pixel_aspect=(8, 7), pixelate=2)
    elif preset_id == "game-gear":
        _configure_palette_preset(settings, "Game Gear Reference 16", dither="Floyd-Steinberg", strength=0.9, target=(160, 144), pixelate=2)
    elif preset_id == "mega-drive":
        settings = _apply_profile(settings, "mega-drive", mode="strict")
        _set_dither(settings, "Nearest Palette", 1.0, serpentine=False)
        contrast = new_effect("Local Contrast")
        contrast["params"].update(amount=115, radius=1.4)
        _insert_effect(settings, contrast, 1)
    elif preset_id == "playstation":
        settings = _apply_profile(settings, "playstation", mode="strict")
        _set_dither(settings, "Nearest Palette", 1.0, serpentine=False)
        row = new_effect("Row Shift")
        row["enabled"] = True
        row["params"].update(amount=1, period=5)
        _insert_effect(settings, row)
    elif preset_id == "apple-ii-hgr":
        settings = _apply_profile(settings, "apple-ii-hgr", mode="visual", apply_constraints=False)
        _set_dither(settings, "Bayer 4x4", 1.0)
    elif preset_id == "c64-multicolor":
        settings = _apply_profile(settings, "c64-multicolor", mode="strict")
        _set_dither(settings, "Bayer 4x4", 0.9)
    elif preset_id == "vic-20":
        _configure_palette_preset(settings, "VIC-20", dither="Atkinson", strength=0.85, target=(176, 184), pixel_aspect=(6, 5), pixelate=2)
    elif preset_id == "plus4":
        _configure_palette_preset(settings, "Commodore Plus/4", dither="Floyd-Steinberg", strength=0.9, target=(320, 200), pixel_aspect=(5, 6), pixelate=2)
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
    elif preset_id == "amiga-wb13":
        _configure_palette_preset(settings, "Amiga Workbench 1.3", dither="Nearest Palette", strength=1.0, target=(320, 256), pixel_aspect=(1, 1), pixelate=2)
    elif preset_id == "amiga-wb2":
        _configure_palette_preset(settings, "Amiga Workbench 2.x", dither="Nearest Palette", strength=1.0, target=(320, 256), pixelate=2)
    elif preset_id == "amiga-wb3":
        _configure_palette_preset(settings, "Amiga Workbench 3.x", dither="Nearest Palette", strength=1.0, target=(320, 256), pixelate=2)
    elif preset_id == "amstrad-cpc":
        _configure_palette_preset(settings, "Amstrad CPC 27", dither="Bayer 4x4", strength=0.95, target=(320, 200), pixel_aspect=(5, 6), pixelate=2)
    elif preset_id == "msx":
        _configure_palette_preset(settings, "MSX 15", dither="Floyd-Steinberg", strength=0.9, target=(256, 192), pixel_aspect=(8, 7), pixelate=2)
    elif preset_id == "ti994a":
        _configure_palette_preset(settings, "TI-99/4A", dither="Bayer 4x4", strength=0.9, target=(256, 192), pixel_aspect=(8, 7), pixelate=2)
    elif preset_id == "crt-ntsc":
        settings = _apply_profile(settings, "crt-ntsc", mode="visual", apply_constraints=False, apply_display=True)
        _set_dither(settings, "Nearest Palette", 1.0)
        _enable_pixelate(settings, 2)
    elif preset_id == "crt-pal":
        settings = _apply_profile(settings, "crt-pal", mode="visual", apply_constraints=False, apply_display=True)
        _set_dither(settings, "Nearest Palette", 1.0)
        _enable_pixelate(settings, 2)
    elif preset_id == "monochrome-lcd":
        settings = _apply_profile(settings, "monochrome-lcd", mode="strict")
        _set_dither(settings, "Bayer 4x4", 1.0)
        _enable_pixelate(settings, 2)
    elif preset_id == "green-crt":
        _set_palette(settings, "MDA Green 4")
        _set_dither(settings, "Atkinson", 0.85)
        local = new_effect("Local Contrast")
        local["params"].update(amount=150, radius=1.8)
        scan = new_effect("Scanlines")
        scan["params"].update(spacing=3, strength=0.18)
        _insert_effect(settings, local, 1)
        _insert_effect(settings, scan)
    elif preset_id == "amber-monitor":
        _configure_palette_preset(settings, "Amber Monitor 8", dither="Atkinson", strength=0.8, pixelate=2)
        scan = new_effect("Scanlines")
        scan["params"].update(spacing=3, strength=0.16)
        _insert_effect(settings, scan)
    elif preset_id == "white-phosphor":
        _configure_palette_preset(settings, "White Phosphor 8", dither="Atkinson", strength=0.8, pixelate=2)
        scan = new_effect("Scanlines")
        scan["params"].update(spacing=3, strength=0.14)
        _insert_effect(settings, scan)
    elif preset_id == "halftone-print":
        settings.palette = ["#201A17", "#6F4A2F", "#C99255", "#F4E3B2"]
        settings.palette_name = "Warm Print 4"
        settings.palette_author = "RasterMint"
        settings.palette_source = "builtin"
        settings.palette_locks = [False] * len(settings.palette)
        _set_dither(settings, "Halftone", 1.0)
        local = new_effect("Local Contrast")
        local["params"].update(amount=150, radius=1.5)
        _insert_effect(settings, local, 1)
    elif preset_id == "mac-classic":
        _configure_palette_preset(settings, "Classic Macintosh 1-bit", dither="Atkinson", strength=1.0, target=(512, 342), pixelate=2)
    elif preset_id == "mac-gray":
        _configure_palette_preset(settings, "Macintosh Gray 4", dither="Bayer 4x4", strength=1.0, target=(512, 342), pixelate=2)
    elif preset_id == "atari-st":
        _configure_palette_preset(settings, "Atari ST 16", dither="Floyd-Steinberg", strength=0.85, target=(320, 200), pixel_aspect=(5, 6), pixelate=2)
    elif preset_id == "atari-8bit":
        _configure_palette_preset(settings, "Atari 8-bit Reference 16", dither="Bayer 4x4", strength=0.9, target=(320, 192), pixel_aspect=(1, 1), pixelate=2)
    elif preset_id == "teletext":
        _configure_palette_preset(settings, "Teletext 8", dither="Nearest Palette", strength=1.0, target=(240, 200), pixelate=3)
    elif preset_id == "oric-atmos":
        _configure_palette_preset(settings, "Oric Atmos 8", dither="Bayer 4x4", strength=0.9, target=(240, 200), pixel_aspect=(1, 1), pixelate=2)
    elif preset_id == "dragon-coco":
        _configure_palette_preset(settings, "Dragon / CoCo Reference 8", dither="Bayer 4x4", strength=0.9, target=(256, 192), pixel_aspect=(1, 1), pixelate=2)
    elif preset_id == "coco3":
        _configure_palette_preset(settings, "CoCo 3 Reference 16", dither="Floyd-Steinberg", strength=0.85, target=(320, 225), pixel_aspect=(1, 1), pixelate=2)
    elif preset_id == "pc98":
        _configure_palette_preset(settings, "PC-98 16", dither="Nearest Palette", strength=1.0, target=(640, 400), pixelate=2)
    elif preset_id == "x68000":
        _configure_palette_preset(settings, "X68000 Reference 16", dither="Nearest Palette", strength=1.0, target=(512, 512), pixelate=2)
    elif preset_id == "fmtowns":
        _configure_palette_preset(settings, "FM Towns Reference 16", dither="Nearest Palette", strength=1.0, target=(320, 240), pixelate=2)
    elif preset_id == "sam-coupe":
        _configure_palette_preset(settings, "SAM Coupé 16", dither="Floyd-Steinberg", strength=0.85, target=(256, 192), pixelate=2)
    elif preset_id == "thomson":
        _configure_palette_preset(settings, "Thomson TO7/MO5 16", dither="Bayer 4x4", strength=0.9, target=(320, 200), pixelate=2)
    elif preset_id == "intellivision":
        _configure_palette_preset(settings, "Intellivision 16", dither="Bayer 4x4", strength=0.9, target=(320, 192), pixelate=2)
    elif preset_id == "colecovision":
        _configure_palette_preset(settings, "ColecoVision 16", dither="Bayer 4x4", strength=0.9, target=(256, 192), pixelate=2)
    elif preset_id == "neo-geo-pocket":
        _configure_palette_preset(settings, "Neo Geo Pocket Grayscale", dither="Atkinson", strength=1.0, target=(160, 152), pixelate=2)
    elif preset_id == "wonderswan":
        _configure_palette_preset(settings, "WonderSwan Grayscale", dither="Atkinson", strength=1.0, target=(224, 144), pixelate=2)
    elif preset_id == "pico-8":
        _configure_palette_preset(settings, "PICO-8", dither="Nearest Palette", strength=1.0, target=(128, 128), pixelate=4)
    elif preset_id == "tic-80":
        _configure_palette_preset(settings, "TIC-80", dither="Nearest Palette", strength=1.0, target=(240, 136), pixelate=3)
    elif preset_id == "vector":
        settings.palette = ["#0E1116", "#2B3A67", "#5C80BC", "#C3E0E5", "#F8F5F2"]
        settings.palette_name = "Vector Poster 5"
        settings.palette_author = "RasterMint"
        settings.palette_source = "builtin"
        settings.palette_locks = [False] * len(settings.palette)
        _set_dither(settings, "Nearest Palette", 1.0, mix=1.0, serpentine=False)
        posterize = new_effect("Posterize")
        posterize["enabled"] = True
        posterize["params"]["levels"] = 5
        local = new_effect("Local Contrast")
        local["params"].update(amount=180, radius=2.0)
        sharpen = new_effect("Sharpen")
        sharpen["enabled"] = True
        sharpen["params"]["amount"] = 1.4
        _insert_effect(settings, local, 1)
        _insert_effect(settings, sharpen, 5)
        _insert_effect(settings, posterize, 6)
    else:  # clean-quantize
        _set_palette(settings, "Arcade 8")
        _set_dither(settings, "Nearest Palette", 1.0)

    return ProcessingSettings.from_dict(settings.to_dict())
