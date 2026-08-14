# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .palette import hex_to_rgb, palette_array, quantize_nearest
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
    from .effect_stack import normalize_effect_stack
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
        if mode == "strict" and strict_supported(profile) and isinstance(constraints, dict):
            result.hardware_constraints_enabled = True
            result.hardware_constraints = deepcopy(constraints)
        else:
            result.hardware_constraints_enabled = False
            result.hardware_constraints = {}

    if apply_display:
        visual = profile.visual
        display = visual.get("display") if isinstance(visual, dict) else {}
        result.display_profile = deepcopy(display) if isinstance(display, dict) else {}
        result.display_mode = "display" if result.display_profile else "corrected"

    return result


def _quantize_channel_bits(arr: np.ndarray, bits: list[int] | tuple[int, ...]) -> np.ndarray:
    out = arr.astype(np.float32, copy=True)
    for channel in range(3):
        b = int(bits[channel] if channel < len(bits) else bits[-1])
        b = max(1, min(8, b))
        levels = (1 << b) - 1
        out[..., channel] = np.rint(np.rint(out[..., channel] / 255.0 * levels) / levels * 255.0)
    return np.clip(out, 0, 255).astype(np.uint8)


def _limit_global_colors(image: Image.Image, count: int) -> Image.Image:
    count = max(2, min(256, int(count)))
    return image.convert("RGB").quantize(colors=count, method=Image.Quantize.FASTOCTREE).convert("RGB")


def _remap_region_to_palette(region: np.ndarray, palette: np.ndarray) -> np.ndarray:
    if palette.size == 0:
        return region
    flat = region.reshape(-1, 3).astype(np.float32)
    diff = flat[:, None, :] - palette[None, :, :]
    idx = np.argmin(np.sum(diff * diff, axis=2), axis=1)
    return palette[idx].reshape(region.shape).astype(np.uint8)


def _choose_region_colors(region: np.ndarray, limit: int) -> np.ndarray:
    pixels = region.reshape(-1, 3)
    colors, counts = np.unique(pixels, axis=0, return_counts=True)
    if len(colors) <= limit:
        return colors.astype(np.float32)
    order = np.argsort(counts)[::-1][:limit]
    return colors[order].astype(np.float32)


def _tile_color_limit(
    arr: np.ndarray,
    tile_width: int,
    tile_height: int,
    max_colors: int,
    palette_groups: list[list[str]] | None = None,
) -> np.ndarray:
    h, w, _ = arr.shape
    tw = max(1, int(tile_width))
    th = max(1, int(tile_height))
    limit = max(1, int(max_colors))
    out = arr.copy()
    groups_np = [palette_array(group) for group in (palette_groups or []) if group]

    for y in range(0, h, th):
        for x in range(0, w, tw):
            region = out[y : min(h, y + th), x : min(w, x + tw)]
            if groups_np:
                # ZX-style shared brightness groups: choose the palette group
                # with the smallest reconstruction error, then keep only the
                # requested number of colors inside that group.
                best_group: np.ndarray | None = None
                best_error = float("inf")
                for group in groups_np:
                    remapped = _remap_region_to_palette(region, group)
                    error = float(np.mean((region.astype(np.float32) - remapped.astype(np.float32)) ** 2))
                    if error < best_error:
                        best_error = error
                        best_group = group
                assert best_group is not None
                remapped = _remap_region_to_palette(region, best_group)
                chosen = _choose_region_colors(remapped, limit)
                region[:] = _remap_region_to_palette(region, chosen)
            else:
                chosen = _choose_region_colors(region, limit)
                region[:] = _remap_region_to_palette(region, chosen)
    return out


def apply_hardware_constraints(image: Image.Image, constraints: dict[str, Any]) -> Image.Image:
    if not constraints:
        return image.convert("RGB")
    img = image.convert("RGB")
    arr = np.asarray(img, dtype=np.uint8)

    fixed_palette = constraints.get("fixed_palette")
    if isinstance(fixed_palette, list) and fixed_palette:
        mapped = quantize_nearest(arr.astype(np.float32), palette_array(fixed_palette))
        arr = np.clip(mapped, 0, 255).astype(np.uint8)

    channel_bits = constraints.get("channel_bits")
    if isinstance(channel_bits, (list, tuple)) and channel_bits:
        arr = _quantize_channel_bits(arr, list(channel_bits))

    max_global = int(constraints.get("max_colors_global") or 0)
    if max_global > 0 and not fixed_palette:
        img = _limit_global_colors(Image.fromarray(arr, "RGB"), max_global)
        arr = np.asarray(img, dtype=np.uint8)

    tile_limit = int(constraints.get("tile_max_colors") or 0)
    if tile_limit > 0:
        tile_width = int(constraints.get("tile_width") or 8)
        tile_height = int(constraints.get("tile_height") or 8)
        groups = constraints.get("tile_palette_groups")
        groups = groups if isinstance(groups, list) else None
        arr = _tile_color_limit(arr, tile_width, tile_height, tile_limit, groups)

    return Image.fromarray(arr.astype(np.uint8), "RGB")


def correct_pixel_aspect(image: Image.Image, x: float, y: float) -> Image.Image:
    x = max(0.05, float(x))
    y = max(0.05, float(y))
    ratio = x / y
    if abs(ratio - 1.0) < 1e-6:
        return image.convert("RGB")
    width = max(1, round(image.width * ratio))
    return image.convert("RGB").resize((width, image.height), Image.Resampling.NEAREST)


def _gamma(image: Image.Image, gamma: float) -> Image.Image:
    gamma = max(0.1, min(4.0, float(gamma)))
    if abs(gamma - 1.0) < 1e-6:
        return image
    inv = 1.0 / gamma
    lut = [round(255 * ((i / 255.0) ** inv)) for i in range(256)]
    return image.point(lut * 3)


def _color_bleed(image: Image.Image, amount: float) -> Image.Image:
    amount = max(0.0, min(8.0, float(amount)))
    if amount <= 0:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    # Cheap horizontal chroma bleed: average neighbouring red/blue samples
    # while keeping green tighter. It is intentionally a display treatment,
    # not NTSC signal emulation.
    radius = max(1, round(amount))
    out = arr.copy()
    for channel in (0, 2):
        accum = np.zeros_like(arr[..., channel])
        count = 0
        for offset in range(-radius, radius + 1):
            accum += np.roll(arr[..., channel], offset, axis=1)
            count += 1
        out[..., channel] = accum / max(1, count)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def apply_display_simulation(image: Image.Image, profile: dict[str, Any]) -> Image.Image:
    if not profile:
        return image.convert("RGB")
    img = image.convert("RGB")
    gamma = float(profile.get("gamma", 1.0))
    img = _gamma(img, gamma)

    bleed = float(profile.get("color_bleed", 0.0))
    if bleed > 0:
        img = _color_bleed(img, bleed)

    blur = float(profile.get("blur", 0.0))
    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur))

    arr = np.asarray(img, dtype=np.float32).copy()
    scanlines = max(0.0, min(1.0, float(profile.get("scanlines", 0.0))))
    if scanlines > 0 and arr.shape[0] > 1:
        arr[1::2] *= 1.0 - scanlines

    lcd_grid = max(0.0, min(1.0, float(profile.get("lcd_grid", 0.0))))
    if lcd_grid > 0:
        arr[:, ::2] *= 1.0 - lcd_grid * 0.45
        arr[::2, :] *= 1.0 - lcd_grid * 0.35

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def apply_grid_overlay(
    image: Image.Image,
    *,
    spacing: int = 1,
    major_spacing: int = 8,
    opacity: float = 0.35,
    pixel_aspect_ratio: float = 1.0,
) -> Image.Image:
    spacing = max(1, int(spacing))
    major_spacing = max(0, int(major_spacing))
    opacity = max(0.0, min(1.0, float(opacity)))
    if opacity <= 0:
        return image.convert("RGB")

    img = image.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    par = max(0.05, float(pixel_aspect_ratio))
    sx = max(1, round(spacing * par))
    sy = max(1, spacing)
    # Avoid turning a huge downscaled preview into a solid grid. Grid lines are
    # shown only when there is at least one pixel between lines.
    if sx < 2 and sy < 2:
        return image.convert("RGB")

    minor_alpha = round(255 * opacity * 0.55)
    major_alpha = round(255 * opacity)
    for x in range(0, img.width, sx):
        logical = round(x / max(1, sx)) * spacing
        major = major_spacing > 0 and logical % major_spacing == 0
        draw.line((x, 0, x, img.height), fill=(255, 255, 255, major_alpha if major else minor_alpha), width=1)
    for y in range(0, img.height, sy):
        logical = round(y / max(1, sy)) * spacing
        major = major_spacing > 0 and logical % major_spacing == 0
        draw.line((0, y, img.width, y), fill=(255, 255, 255, major_alpha if major else minor_alpha), width=1)
    return Image.alpha_composite(img, overlay).convert("RGB")


def render_display_view(
    image: Image.Image,
    settings: ProcessingSettings,
    *,
    mode: str | None = None,
    include_grid: bool = False,
) -> Image.Image:
    mode = str(mode or settings.display_mode or "raw").lower()
    img = image.convert("RGB")
    par = settings.pixel_aspect_x / max(0.05, settings.pixel_aspect_y)
    if mode in {"corrected", "display"}:
        img = correct_pixel_aspect(img, settings.pixel_aspect_x, settings.pixel_aspect_y)
    if mode == "display":
        img = apply_display_simulation(img, settings.display_profile)
    if include_grid and settings.grid_enabled:
        img = apply_grid_overlay(
            img,
            spacing=settings.grid_spacing,
            major_spacing=settings.grid_major_spacing,
            opacity=settings.grid_opacity,
            pixel_aspect_ratio=par if mode in {"corrected", "display"} else 1.0,
        )
    return img
