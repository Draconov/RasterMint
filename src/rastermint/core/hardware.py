# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .color_utils import hex_to_rgb
from .hardware_profiles import (
    HardwareProfile,
    apply_profile_to_settings,
    load_builtin_profiles,
    load_profile_file,
    profile_map,
    profile_summary,
    strict_supported,
)
from .palette import palette_array, quantize_nearest

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


def apply_hardware_limits_layer(
    image: Image.Image,
    params: dict[str, Any],
    active_palette: list[str],
) -> Image.Image:
    """Apply an editable Hardware Limits layer using the live palette.

    Fixed-palette hardware profiles default to Active Palette after the profile
    applies its palette, so later swatch edits immediately change the strict
    remap instead of being silently overridden by a hidden profile snapshot.
    """
    palette_source = str(params.get("palette_source", "Active Palette"))
    profile_palette: list[str] = []
    try:
        raw_palette = json.loads(str(params.get("profile_palette_json", "[]") or "[]"))
        if isinstance(raw_palette, list):
            profile_palette = [str(color) for color in raw_palette if str(color).strip()]
    except (TypeError, ValueError, json.JSONDecodeError):
        profile_palette = []

    if not profile_palette:
        # Native-depth / channel-limit profiles have no hardware palette to
        # enforce. Palette selection is therefore not part of this stage.
        enforced_palette = []
    elif palette_source == "Profile Palette":
        enforced_palette = profile_palette
    else:  # Active Palette
        enforced_palette = [str(color) for color in active_palette]

    constraints: dict[str, Any] = {}
    if enforced_palette:
        constraints["fixed_palette"] = enforced_palette

    bits = [
        max(1, min(8, int(params.get("channel_r_bits", 8)))),
        max(1, min(8, int(params.get("channel_g_bits", 8)))),
        max(1, min(8, int(params.get("channel_b_bits", 8)))),
    ]
    if bits != [8, 8, 8]:
        constraints["channel_bits"] = bits

    max_global = max(0, min(256, int(params.get("max_colors_global", 0))))
    if max_global > 0:
        constraints["max_colors_global"] = max_global

    tile_limit = max(0, min(256, int(params.get("tile_max_colors", 0))))
    if tile_limit > 0:
        constraints["tile_max_colors"] = tile_limit
        constraints["tile_width"] = max(1, int(params.get("tile_width", 8)))
        constraints["tile_height"] = max(1, int(params.get("tile_height", 8)))

        if bool(params.get("use_profile_groups", False)):
            try:
                raw_groups = json.loads(str(params.get("profile_group_indices_json", "[]") or "[]"))
            except (TypeError, ValueError, json.JSONDecodeError):
                raw_groups = []
            source_palette = enforced_palette or profile_palette
            groups: list[list[str]] = []
            if isinstance(raw_groups, list) and source_palette:
                for raw_group in raw_groups:
                    if not isinstance(raw_group, list):
                        continue
                    colors = [
                        source_palette[index]
                        for index in raw_group
                        if isinstance(index, int) and 0 <= index < len(source_palette)
                    ]
                    if colors:
                        groups.append(colors)
            if groups:
                constraints["tile_palette_groups"] = groups

    return apply_hardware_constraints(image, constraints)


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
    display_profiles: list[dict[str, Any]] | None = None,
) -> Image.Image:
    mode = str(mode or settings.display_mode or "raw").lower()
    img = image.convert("RGB")
    par = settings.pixel_aspect_x / max(0.05, settings.pixel_aspect_y)
    if mode in {"corrected", "display"}:
        img = correct_pixel_aspect(img, settings.pixel_aspect_x, settings.pixel_aspect_y)
    if mode == "display":
        profiles = [settings.display_profile] if display_profiles is None else list(display_profiles)
        for profile in profiles:
            if profile:
                img = apply_display_simulation(img, profile)
    if include_grid and settings.grid_enabled:
        img = apply_grid_overlay(
            img,
            spacing=settings.grid_spacing,
            major_spacing=settings.grid_major_spacing,
            opacity=settings.grid_opacity,
            pixel_aspect_ratio=par if mode in {"corrected", "display"} else 1.0,
        )
    return img
