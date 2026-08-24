# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .effect_schema import default_effect_stack, new_effect
from .hardware_profiles import apply_profile_to_settings, load_builtin_profiles
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
    BuiltinPreset("accurate-1to1", "Accurate 1:1 Colour", "50/50 palette-colour mixing for perceived intermediate colours while keeping the active palette."),
)


_PROFILE_CACHE = {profile.id: profile for profile in load_builtin_profiles()}


def _palette_config(
    palette: str,
    *,
    dither: str = "Nearest Palette",
    strength: float = 1.0,
    serpentine: bool | None = None,
    target: tuple[int, int] | None = None,
    pixel_aspect: tuple[float, float] | None = None,
    pixelate: int | None = None,
    effects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "palette": palette,
        "dither": {"algorithm": dither, "strength": strength, "serpentine": serpentine},
        "target": target,
        "pixel_aspect": pixel_aspect,
        "pixelate": pixelate,
        "effects": effects or [],
    }


def _profile_config(
    profile_id: str,
    *,
    mode: str = "strict",
    constraints: bool = True,
    display: bool = True,
    dither: str = "Nearest Palette",
    strength: float = 1.0,
    serpentine: bool | None = None,
    pixelate: int | None = None,
    effects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "profile": {
            "id": profile_id,
            "mode": mode,
            "constraints": constraints,
            "display": display,
        },
        "dither": {"algorithm": dither, "strength": strength, "serpentine": serpentine},
        "pixelate": pixelate,
        "effects": effects or [],
    }


def _effect(kind: str, *, index: int | None = None, enabled: bool = True, **params: Any) -> dict[str, Any]:
    return {"kind": kind, "index": index, "enabled": enabled, "params": params}


# Most presets are declarative. Adding another palette/hardware look should
# normally only require another entry here, not another branch in Python code.
PRESET_CONFIGS: dict[str, dict[str, Any]] = {
    "clean-quantize": _palette_config("Arcade 8"),
    "game-boy": _profile_config("game-boy", mode="visual", constraints=False, dither="Bayer 4x4"),
    "game-boy-pocket": _palette_config("Game Boy Pocket", dither="Bayer 4x4", target=(160, 144), pixelate=2),
    "game-boy-light": _palette_config("Game Boy Light", dither="Bayer 4x4", target=(160, 144), pixelate=2),
    "game-boy-color": _profile_config("game-boy-color", serpentine=False),
    "game-boy-advance": _profile_config(
        "game-boy-advance",
        serpentine=False,
        effects=[_effect("Local Contrast", index=1, amount=135, radius=1.6)],
    ),
    "virtual-boy": _palette_config("Virtual Boy", dither="Bayer 4x4", target=(384, 224), pixelate=2),
    "nes": _profile_config("nes", dither="Bayer 4x4", strength=0.95),
    "snes": _profile_config(
        "snes",
        serpentine=False,
        effects=[_effect("Sharpen", index=4, amount=1.2)],
    ),
    "master-system": _palette_config("Master System Reference 16", dither="Floyd-Steinberg", strength=0.9, target=(256, 192), pixel_aspect=(8, 7), pixelate=2),
    "game-gear": _palette_config("Game Gear Reference 16", dither="Floyd-Steinberg", strength=0.9, target=(160, 144), pixelate=2),
    "mega-drive": _profile_config(
        "mega-drive",
        serpentine=False,
        effects=[_effect("Local Contrast", index=1, amount=115, radius=1.4)],
    ),
    "playstation": _profile_config(
        "playstation",
        serpentine=False,
        effects=[_effect("Row Shift", amount=1, period=5)],
    ),
    "apple-ii-hgr": _profile_config("apple-ii-hgr", mode="visual", constraints=False, dither="Bayer 4x4"),
    "c64-multicolor": _profile_config("c64-multicolor", dither="Bayer 4x4", strength=0.9),
    "vic-20": _palette_config("VIC-20", dither="Atkinson", strength=0.85, target=(176, 184), pixel_aspect=(6, 5), pixelate=2),
    "plus4": _palette_config("Commodore Plus/4", dither="Floyd-Steinberg", strength=0.9, target=(320, 200), pixel_aspect=(5, 6), pixelate=2),
    "zx-spectrum": _profile_config("zx-spectrum", dither="Bayer 4x4", strength=0.9),
    "cga-neon": _profile_config("cga-320", dither="Bayer 4x4"),
    "ega-crisp": _profile_config("ega-320", dither="Floyd-Steinberg", strength=0.8),
    "amiga-ocs": _profile_config("amiga-ocs", serpentine=False),
    "amiga-wb13": _palette_config("Amiga Workbench 1.3", target=(320, 256), pixel_aspect=(1, 1), pixelate=2),
    "amiga-wb2": _palette_config("Amiga Workbench 2.x", target=(320, 256), pixelate=2),
    "amiga-wb3": _palette_config("Amiga Workbench 3.x", target=(320, 256), pixelate=2),
    "amstrad-cpc": _palette_config("Amstrad CPC 27", dither="Bayer 4x4", strength=0.95, target=(320, 200), pixel_aspect=(5, 6), pixelate=2),
    "msx": _palette_config("MSX 15", dither="Floyd-Steinberg", strength=0.9, target=(256, 192), pixel_aspect=(8, 7), pixelate=2),
    "ti994a": _palette_config("TI-99/4A", dither="Bayer 4x4", strength=0.9, target=(256, 192), pixel_aspect=(8, 7), pixelate=2),
    "crt-ntsc": _profile_config("crt-ntsc", mode="visual", constraints=False, pixelate=2),
    "crt-pal": _profile_config("crt-pal", mode="visual", constraints=False, pixelate=2),
    "monochrome-lcd": _profile_config("monochrome-lcd", dither="Bayer 4x4", pixelate=2),
    "green-crt": _palette_config(
        "MDA Green 4",
        dither="Atkinson",
        strength=0.85,
        effects=[
            _effect("Local Contrast", index=1, amount=150, radius=1.8),
            _effect("Scanlines", spacing=3, strength=0.18),
        ],
    ),
    "amber-monitor": _palette_config(
        "Amber Monitor 8",
        dither="Atkinson",
        strength=0.8,
        pixelate=2,
        effects=[_effect("Scanlines", spacing=3, strength=0.16)],
    ),
    "white-phosphor": _palette_config(
        "White Phosphor 8",
        dither="Atkinson",
        strength=0.8,
        pixelate=2,
        effects=[_effect("Scanlines", spacing=3, strength=0.14)],
    ),
    "halftone-print": {
        "palette_colors": ["#201A17", "#6F4A2F", "#C99255", "#F4E3B2"],
        "palette_name": "Warm Print 4",
        "palette_author": "RasterMint",
        "palette_source": "builtin",
        "dither": {"algorithm": "Halftone", "strength": 1.0},
        "effects": [_effect("Local Contrast", index=1, amount=150, radius=1.5)],
    },
    "mac-classic": _palette_config("Classic Macintosh 1-bit", dither="Atkinson", target=(512, 342), pixelate=2),
    "mac-gray": _palette_config("Macintosh Gray 4", dither="Bayer 4x4", target=(512, 342), pixelate=2),
    "atari-st": _palette_config("Atari ST 16", dither="Floyd-Steinberg", strength=0.85, target=(320, 200), pixel_aspect=(5, 6), pixelate=2),
    "atari-8bit": _palette_config("Atari 8-bit Reference 16", dither="Bayer 4x4", strength=0.9, target=(320, 192), pixel_aspect=(1, 1), pixelate=2),
    "teletext": _palette_config("Teletext 8", target=(240, 200), pixelate=3),
    "oric-atmos": _palette_config("Oric Atmos 8", dither="Bayer 4x4", strength=0.9, target=(240, 200), pixel_aspect=(1, 1), pixelate=2),
    "dragon-coco": _palette_config("Dragon / CoCo Reference 8", dither="Bayer 4x4", strength=0.9, target=(256, 192), pixel_aspect=(1, 1), pixelate=2),
    "coco3": _palette_config("CoCo 3 Reference 16", dither="Floyd-Steinberg", strength=0.85, target=(320, 225), pixel_aspect=(1, 1), pixelate=2),
    "pc98": _palette_config("PC-98 16", target=(640, 400), pixelate=2),
    "x68000": _palette_config("X68000 Reference 16", target=(512, 512), pixelate=2),
    "fmtowns": _palette_config("FM Towns Reference 16", target=(320, 240), pixelate=2),
    "sam-coupe": _palette_config("SAM Coupé 16", dither="Floyd-Steinberg", strength=0.85, target=(256, 192), pixelate=2),
    "thomson": _palette_config("Thomson TO7/MO5 16", dither="Bayer 4x4", strength=0.9, target=(320, 200), pixelate=2),
    "intellivision": _palette_config("Intellivision 16", dither="Bayer 4x4", strength=0.9, target=(320, 192), pixelate=2),
    "colecovision": _palette_config("ColecoVision 16", dither="Bayer 4x4", strength=0.9, target=(256, 192), pixelate=2),
    "neo-geo-pocket": _palette_config("Neo Geo Pocket Grayscale", dither="Atkinson", target=(160, 152), pixelate=2),
    "wonderswan": _palette_config("WonderSwan Grayscale", dither="Atkinson", target=(224, 144), pixelate=2),
    "pico-8": _palette_config("PICO-8", target=(128, 128), pixelate=4),
    "tic-80": _palette_config("TIC-80", target=(240, 136), pixelate=3),
    "vector": {
        "palette_colors": ["#0E1116", "#2B3A67", "#5C80BC", "#C3E0E5", "#F8F5F2"],
        "palette_name": "Vector Poster 5",
        "palette_author": "RasterMint",
        "palette_source": "builtin",
        "dither": {"algorithm": "Nearest Palette", "strength": 1.0, "mix": 1.0, "serpentine": False},
        "effects": [
            _effect("Local Contrast", index=1, amount=180, radius=2.0),
            _effect("Sharpen", index=5, amount=1.4),
            _effect("Posterize", index=6, levels=5),
        ],
    },
    "accurate-1to1": {
        "dither": {
            "algorithm": "1:1 Colour Mix",
            "strength": 1.0,
            "mix": 1.0,
            "serpentine": False,
            "color_mix_pattern": "Checker",
            "color_mix_distance": "OKLab",
            "color_mix_phase": 0,
        },
    },
}


# Escape hatch for genuinely procedural presets. Most presets should stay in
# PRESET_CONFIGS; only add a builder here when a data specification cannot
# express the effect correctly.
PresetBuilder = Callable[[ProcessingSettings], ProcessingSettings]
CUSTOM_PRESET_BUILDERS: dict[str, PresetBuilder] = {}


def _find_profile(profile_id: str):
    return _PROFILE_CACHE.get(profile_id)


def _set_palette(settings: ProcessingSettings, name: str) -> None:
    record = find_palette(name)
    if record:
        settings.palette = list(record.colors)
        settings.palette_name = record.name
        settings.palette_author = "RasterMint palette library"
        settings.palette_source = record.source
        settings.palette_locks = [False] * len(settings.palette)


def _set_dither(settings: ProcessingSettings, spec: dict[str, Any]) -> None:
    for step in settings.effect_stack:
        if step.get("kind") != "Dither":
            continue
        params = step.setdefault("params", {})
        params["algorithm"] = str(spec.get("algorithm") or "Nearest Palette")
        params["strength"] = float(spec.get("strength", 1.0))
        if spec.get("mix") is not None:
            params["mix"] = float(spec["mix"])
        if spec.get("serpentine") is not None:
            params["serpentine"] = bool(spec["serpentine"])
        if spec.get("color_mix_pattern") is not None:
            params["color_mix_pattern"] = str(spec["color_mix_pattern"])
        if spec.get("color_mix_distance") is not None:
            params["color_mix_distance"] = str(spec["color_mix_distance"])
        if spec.get("color_mix_phase") is not None:
            params["color_mix_phase"] = int(spec["color_mix_phase"])
        return


def _enable_pixelate(settings: ProcessingSettings, size: int) -> None:
    for step in settings.effect_stack:
        if step.get("kind") == "Pixelate":
            step["enabled"] = True
            step.setdefault("params", {})["size"] = int(size)
            return


def _apply_effect_specs(settings: ProcessingSettings, specs: list[dict[str, Any]]) -> None:
    for spec in specs:
        effect = new_effect(str(spec["kind"]), enabled=bool(spec.get("enabled", True)))
        effect["params"].update(dict(spec.get("params") or {}))
        index = spec.get("index")
        if index is None:
            settings.effect_stack.append(effect)
        else:
            settings.effect_stack.insert(int(index), effect)


def _apply_data_config(settings: ProcessingSettings, config: dict[str, Any]) -> ProcessingSettings:
    profile_spec = config.get("profile")
    if isinstance(profile_spec, dict):
        profile = _find_profile(str(profile_spec.get("id") or ""))
        if profile is not None:
            settings = apply_profile_to_settings(
                settings,
                profile,
                mode=str(profile_spec.get("mode") or "visual"),
                apply_resolution=True,
                apply_palette=True,
                apply_pixel_aspect=True,
                apply_constraints=bool(profile_spec.get("constraints", True)),
                apply_display=bool(profile_spec.get("display", True)),
            )

    palette_name = config.get("palette")
    if palette_name:
        _set_palette(settings, str(palette_name))

    palette_colors = config.get("palette_colors")
    if isinstance(palette_colors, list) and palette_colors:
        settings.palette = [str(color) for color in palette_colors]
        settings.palette_name = str(config.get("palette_name") or "Custom")
        settings.palette_author = str(config.get("palette_author") or "RasterMint")
        settings.palette_source = str(config.get("palette_source") or "builtin")
        settings.palette_locks = [False] * len(settings.palette)

    dither_spec = config.get("dither")
    if isinstance(dither_spec, dict):
        _set_dither(settings, dither_spec)

    target = config.get("target")
    if isinstance(target, (list, tuple)) and len(target) >= 2:
        settings.target_enabled = True
        settings.target_width = int(target[0])
        settings.target_height = int(target[1])

    pixel_aspect = config.get("pixel_aspect")
    if isinstance(pixel_aspect, (list, tuple)) and len(pixel_aspect) >= 2:
        settings.pixel_aspect_x = float(pixel_aspect[0])
        settings.pixel_aspect_y = float(pixel_aspect[1])

    if config.get("pixelate") is not None:
        _enable_pixelate(settings, int(config["pixelate"]))

    effects = config.get("effects")
    if isinstance(effects, list):
        _apply_effect_specs(settings, effects)

    return settings


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


def _new_preset_settings(base: ProcessingSettings | None) -> ProcessingSettings:
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
    return settings


def build_builtin_preset(preset_id: str, base: ProcessingSettings | None = None) -> ProcessingSettings:
    settings = _new_preset_settings(base)

    custom_builder = CUSTOM_PRESET_BUILDERS.get(preset_id)
    if custom_builder is not None:
        settings = custom_builder(settings)
    else:
        config = PRESET_CONFIGS.get(preset_id, PRESET_CONFIGS["clean-quantize"])
        settings = _apply_data_config(settings, config)

    # This preset is an algorithm recipe, not a palette preset. Preserve the
    # user's currently selected palette and lock state instead of replacing it.
    if preset_id == "accurate-1to1" and base is not None:
        settings.palette = list(base.palette)
        settings.palette_name = str(base.palette_name)
        settings.palette_author = str(base.palette_author)
        settings.palette_source = str(base.palette_source)
        settings.palette_locks = list(base.palette_locks) if base.palette_locks else [False] * len(settings.palette)

    return ProcessingSettings.from_dict(settings.to_dict())
