# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

from .settings import ProcessingSettings

@dataclass(frozen=True, slots=True)
class HardwareProfile:
    id: str
    name: str
    category: str
    summary: str
    data: dict[str, Any]

    @property
    def raster(self) -> dict[str, Any]:
        return dict(self.data.get("raster") or {})

    @property
    def palette(self) -> dict[str, Any]:
        return dict(self.data.get("palette") or {})

    @property
    def visual(self) -> dict[str, Any]:
        return dict(self.data.get("visual") or {})

    @property
    def strict(self) -> dict[str, Any]:
        return dict(self.data.get("strict") or {})

    @property
    def recommended_dither(self) -> str:
        return str(self.data.get("recommended_dither") or "Floyd-Steinberg")


def _profile_from_mapping(data: dict[str, Any]) -> HardwareProfile:
    profile_id = str(data.get("id") or "").strip()
    name = str(data.get("name") or "").strip()
    if not profile_id or not name:
        raise ValueError("Hardware profile requires non-empty id and name")
    return HardwareProfile(
        id=profile_id,
        name=name,
        category=str(data.get("category") or "Other"),
        summary=str(data.get("summary") or ""),
        data=deepcopy(data),
    )


def load_profile_file(path: str | Path) -> HardwareProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Hardware profile JSON must contain an object")
    return _profile_from_mapping(data)


def load_builtin_profiles() -> list[HardwareProfile]:
    profiles: list[HardwareProfile] = []
    package_root = resources.files("rastermint") / "data" / "hardware_profiles"
    try:
        entries = sorted(package_root.iterdir(), key=lambda item: item.name.lower())
    except (FileNotFoundError, ModuleNotFoundError):
        return []
    for entry in entries:
        if not entry.name.lower().endswith(".json"):
            continue
        try:
            raw = entry.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                profiles.append(_profile_from_mapping(data))
        except Exception:
            # One malformed optional profile must not prevent RasterMint from
            # starting. The custom-profile loader surfaces errors explicitly.
            continue
    return sorted(profiles, key=lambda p: (p.category.lower(), p.name.lower()))


def profile_map(profiles: Iterable[HardwareProfile] | None = None) -> dict[str, HardwareProfile]:
    return {p.id: p for p in (profiles if profiles is not None else load_builtin_profiles())}


def strict_supported(profile: HardwareProfile) -> bool:
    return bool(profile.strict.get("supported", False))


def profile_summary(profile: HardwareProfile, mode: str = "visual") -> str:
    raster = profile.raster
    width = int(raster.get("width") or 0)
    height = int(raster.get("height") or 0)
    par = raster.get("pixel_aspect") or [1.0, 1.0]
    tile = raster.get("tile") or [0, 0]
    palette = profile.palette
    colors = palette.get("colors") or []
    palette_text = f"{len(colors)} fixed colors" if colors else str(palette.get("description") or "native color depth")
    lines = [
        profile.summary or profile.name,
        f"Raster: {width} × {height}" if width and height else "Raster: profile-defined",
        f"Pixel aspect: {float(par[0]):g}:{float(par[1]):g}",
        f"Palette: {palette_text}",
    ]
    if len(tile) >= 2 and int(tile[0]) and int(tile[1]):
        lines.append(f"Tile/attribute geometry: {int(tile[0])} × {int(tile[1])}")
    if mode == "strict":
        lines.append("Strict constraints: available" if strict_supported(profile) else "Strict constraints: visual approximation only")
    return "\n".join(lines)


def _replace_stage_layer(stack: list[dict[str, Any]], kind: str, replacement: dict[str, Any] | None) -> list[dict[str, Any]]:
    kept = [step for step in stack if str(step.get("kind")) != kind]
    if replacement is not None:
        kept.append(replacement)
    return kept


def _palette_group_indices(groups: object, fixed_palette: list[str]) -> list[list[int]]:
    if not isinstance(groups, list) or not fixed_palette:
        return []
    lookup = {str(color).upper(): index for index, color in enumerate(fixed_palette)}
    result: list[list[int]] = []
    for group in groups:
        if not isinstance(group, list):
            continue
        indices = [lookup[str(color).upper()] for color in group if str(color).upper() in lookup]
        if indices:
            result.append(indices)
    return result


def apply_profile_to_settings(
    settings: ProcessingSettings,
    profile: HardwareProfile,
    *,
    mode: str = "visual",
    apply_resolution: bool = True,
    apply_palette: bool = True,
    apply_pixel_aspect: bool = True,
    apply_constraints: bool = True,
    apply_display: bool = True,
) -> ProcessingSettings:
    """Return a copy with the selected hardware profile applied.

    The profile is data, not code. This makes profiles user-extensible while
    keeping the processing engine generic. Strict mode is intentionally an
    image-constraint approximation, not console/PC emulation.
    """
    result = ProcessingSettings.from_dict(settings.to_dict())
    # Profiles may be applied by the CLI before a GUI/default stack has been
    # created. Normalize here so the profile can always configure Dither.
    from .effect_schema import new_effect, normalize_effect_stack
    result.effect_stack = normalize_effect_stack(result.effect_stack, result)
    mode = "strict" if mode == "strict" else "visual"
    result.hardware_profile_id = profile.id
    result.hardware_mode = mode

    raster = profile.raster
    if apply_resolution:
        width = int(raster.get("width") or 0)
        height = int(raster.get("height") or 0)
        if width > 0 and height > 0:
            result.target_enabled = True
            result.target_width = width
            result.target_height = height
            result.keep_aspect = False
            result.output_divisor = 1
            result.fit_mode = str(raster.get("fit_mode") or "fit")

    if apply_pixel_aspect:
        par = raster.get("pixel_aspect") or [1.0, 1.0]
        if isinstance(par, (list, tuple)) and len(par) >= 2:
            result.pixel_aspect_x = max(0.05, float(par[0]))
            result.pixel_aspect_y = max(0.05, float(par[1]))
            result.display_mode = "corrected"

    palette_info = profile.palette
    colors = palette_info.get("colors") if isinstance(palette_info, dict) else None
    if apply_palette and isinstance(colors, list) and colors:
        result.palette = [str(c) for c in colors[:256]]
        result.palette_locks = [False] * len(result.palette)
        result.palette_name = str(palette_info.get("name") or profile.name)
        result.palette_author = str(palette_info.get("author") or "RasterMint hardware profile")
        result.palette_source = f"hardware:{profile.id}"

    # Update the existing Dither node rather than adding duplicates.
    dither_step = next((s for s in result.effect_stack if s.get("kind") == "Dither"), None)
    if dither_step is not None:
        native_depth = str(palette_info.get("type") or "fixed") == "native-depth"
        if native_depth:
            # Full-color systems are better represented by their channel-depth
            # constraint than by an arbitrary tiny palette.
            dither_step["enabled"] = False
        else:
            dither_step["enabled"] = True
            dither_step.setdefault("params", {})["algorithm"] = profile.recommended_dither

    if apply_constraints:
        strict = profile.strict
        constraints = strict.get("constraints") if isinstance(strict, dict) else {}
        limits_step = None
        if strict_supported(profile) and isinstance(constraints, dict) and constraints:
            # Always materialize real hardware limits so users can inspect and
            # edit them in Layers. Visual mode leaves the stage disabled;
            # Strict mode enables it. This keeps Visual output unchanged while
            # making the previously hidden strict capabilities discoverable.
            limits_step = new_effect(
                "Hardware Limits",
                enabled=(mode == "strict"),
                effect_id="hardware-limits",
            )
            params = limits_step["params"]
            fixed_palette = [str(color) for color in list(constraints.get("fixed_palette") or [])]
            channel_bits = list(constraints.get("channel_bits") or [8, 8, 8])
            while len(channel_bits) < 3:
                channel_bits.append(channel_bits[-1] if channel_bits else 8)
            params.update(
                palette_source=("Active Palette" if apply_palette else "Profile Palette"),
                channel_r_bits=int(channel_bits[0]),
                channel_g_bits=int(channel_bits[1]),
                channel_b_bits=int(channel_bits[2]),
                max_colors_global=int(constraints.get("max_colors_global") or 0),
                tile_max_colors=int(constraints.get("tile_max_colors") or 0),
                tile_width=int(constraints.get("tile_width") or 8),
                tile_height=int(constraints.get("tile_height") or 8),
                use_profile_groups=bool(constraints.get("tile_palette_groups")),
                profile_palette_json=json.dumps(fixed_palette, ensure_ascii=False),
                profile_group_indices_json=json.dumps(
                    _palette_group_indices(constraints.get("tile_palette_groups"), fixed_palette),
                    ensure_ascii=False,
                ),
            )
        result.effect_stack = _replace_stage_layer(result.effect_stack, "Hardware Limits", limits_step)
    if apply_display:
        visual = profile.visual
        display = visual.get("display") if isinstance(visual, dict) else {}
        display_step = None
        if isinstance(display, dict) and display:
            display_step = new_effect("Hardware Display", effect_id="hardware-display")
            display_step["params"].update(
                gamma=float(display.get("gamma", 1.0)),
                color_bleed=float(display.get("color_bleed", 0.0)),
                blur=float(display.get("blur", 0.0)),
                scanlines=float(display.get("scanlines", 0.0)),
                lcd_grid=float(display.get("lcd_grid", 0.0)),
            )
        result.effect_stack = _replace_stage_layer(result.effect_stack, "Hardware Display", display_step)
        result.display_profile = {}
        result.display_mode = "display" if display_step is not None else "corrected"

    result.effect_stack = normalize_effect_stack(result.effect_stack, result)
    return result
