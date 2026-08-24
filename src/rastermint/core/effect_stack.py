# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from functools import lru_cache
import math
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from .color_utils import hex_to_rgb
from .dither import apply_dither
from .effect_schema import (
    EFFECT_DEFINITIONS,
    animatable_targets,
    default_effect_stack,
    effect_categories,
    new_effect,
    normalize_effect_stack,
    scale_stack_for_preview,
)
from .palette import palette_array

def _temporal_pattern(
    image: Image.Image,
    pattern: str,
    amount: float,
    speed: float,
    scale: float,
    phase: float,
    frame_time: float,
    seed: int,
) -> Image.Image:
    amount = max(0.0, min(1.0, float(amount)))
    if amount <= 0.0:
        return image

    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    scale = max(1.0, float(scale))
    theta = 2.0 * np.pi * (max(0.0, float(speed)) * float(frame_time) + float(phase))

    if pattern == "Pulse":
        field = np.full((h, w), np.sin(theta), dtype=np.float32)
    elif pattern == "Wave Y":
        field = np.sin((yy / scale) * 2.0 * np.pi + theta)
    elif pattern == "Diagonal Wave":
        field = np.sin(((xx + yy) / scale) * 2.0 * np.pi + theta)
    elif pattern == "Checker Phase":
        offset = theta / (2.0 * np.pi) * scale
        cells = (np.floor((xx + offset) / scale) + np.floor((yy + offset) / scale)).astype(np.int32)
        field = np.where((cells & 1) == 0, 1.0, -1.0).astype(np.float32)
    elif pattern == "Scan Sweep":
        center = ((float(frame_time) * max(0.0, float(speed)) + float(phase)) % 1.0) * max(1.0, float(h))
        distance = np.abs(yy - center)
        distance = np.minimum(distance, max(1.0, float(h)) - distance)
        field = np.clip(1.0 - distance / max(1.0, scale), 0.0, 1.0) * 2.0 - 1.0
    elif pattern == "Noise Drift":
        # Smooth deterministic pseudo-noise; no per-frame random allocation is
        # required, so scrubbing to the same time reproduces the same frame.
        base = xx * 12.9898 + yy * 78.233 + float(seed) * 0.12345
        field = np.sin(base + theta + np.sin(base * 0.17 + theta * 0.37))
    elif pattern == "Alternating":
        field = np.full((h, w), 1.0 if int(np.floor(max(0.0, speed) * frame_time + phase)) % 2 == 0 else -1.0, dtype=np.float32)
    elif pattern == "Radial Pulse":
        cx = (w - 1) * 0.5
        cy = (h - 1) * 0.5
        radius = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        field = np.sin((radius / scale) * 2.0 * np.pi - theta)
    else:  # Wave X
        field = np.sin((xx / scale) * 2.0 * np.pi + theta)

    gain = 1.0 + field[..., None] * (amount * 0.5)
    out = np.clip(arr * gain, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")


def _seed(params: dict[str, Any], frame_index: int) -> int:
    seed = int(params.get("seed", 1))
    if bool(params.get("temporal", False)):
        seed += int(frame_index) * 1009
    return seed & 0xFFFFFFFF


def _hue_rotate(image: Image.Image, degrees: int) -> Image.Image:
    if degrees % 360 == 0:
        return image
    hsv = np.asarray(image.convert("HSV"), dtype=np.uint8).copy()
    shift = int(round((degrees % 360) / 360.0 * 255.0))
    hsv[..., 0] = (hsv[..., 0].astype(np.uint16) + shift) % 256
    return Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")


def _levels(image: Image.Image, black_point: int, white_point: int, gamma: float) -> Image.Image:
    black = max(0, min(254, int(black_point)))
    white = max(black + 1, min(255, int(white_point)))
    gamma = max(0.1, min(4.0, float(gamma)))
    if black == 0 and white == 255 and abs(gamma - 1.0) <= 1e-6:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    normalized = np.clip((arr - black) / max(1.0, float(white - black)), 0.0, 1.0)
    normalized = np.power(normalized, 1.0 / gamma)
    return Image.fromarray(np.clip(np.rint(normalized * 255.0), 0, 255).astype(np.uint8), "RGB")


def _local_contrast(image: Image.Image, amount: int, radius: float, threshold: int) -> Image.Image:
    if amount <= 0:
        return image
    return image.filter(ImageFilter.UnsharpMask(radius=max(0.1, radius), percent=max(0, amount), threshold=max(0, threshold)))


def _glow(image: Image.Image, radius: float, intensity: float) -> Image.Image:
    if radius <= 0.0 or intensity <= 0.0:
        return image
    base = np.asarray(image.convert("RGB"), dtype=np.float32)
    blurred = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=radius)), dtype=np.float32)
    glow = np.clip(blurred * intensity, 0.0, 255.0)
    out = base + glow - (base * glow / 255.0)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _soft_threshold_weight(luminance: np.ndarray, threshold: float, softness: float) -> np.ndarray:
    threshold = max(0.0, min(1.0, float(threshold)))
    softness = max(0.0, min(1.0, float(softness)))
    if softness <= 1e-6:
        return (luminance >= threshold).astype(np.float32)
    knee = max(1e-6, softness * 0.5)
    lo = threshold - knee
    hi = threshold + knee
    t = np.clip((luminance - lo) / max(1e-6, hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _bloom(
    image: Image.Image,
    threshold: float,
    soft_knee: float,
    radius: float,
    intensity: float,
    blend: str,
) -> Image.Image:
    """Bloom bright image regions and blend the result over the source.

    Unlike Glow, Bloom first extracts highlights using a luminance threshold.
    ``soft_knee`` controls how gradually pixels enter the bloom around that
    threshold, which avoids a harsh visible cutoff on gradients and photos.
    """
    radius = max(0.0, float(radius))
    intensity = max(0.0, float(intensity))
    if radius <= 0.0 or intensity <= 0.0:
        return image

    threshold = max(0.0, min(1.0, float(threshold)))
    soft_knee = max(0.0, min(1.0, float(soft_knee)))

    base = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    luminance = 0.2126 * base[..., 0] + 0.7152 * base[..., 1] + 0.0722 * base[..., 2]
    weight = _soft_threshold_weight(luminance, threshold, soft_knee)

    highlights = np.clip(base * weight[..., None] * 255.0, 0.0, 255.0).astype(np.uint8)
    highlight_image = Image.fromarray(highlights, "RGB")
    blurred = np.asarray(
        highlight_image.filter(ImageFilter.GaussianBlur(radius=radius)),
        dtype=np.float32,
    ) / 255.0

    bloom = np.clip(blurred * intensity, 0.0, 1.0)
    if str(blend) == "Add":
        out = np.clip(base + bloom, 0.0, 1.0)
    else:  # Screen is the safer/default photographic blend.
        out = 1.0 - (1.0 - base) * (1.0 - bloom)

    return Image.fromarray(np.clip(np.rint(out * 255.0), 0, 255).astype(np.uint8), "RGB")


def _dither_glow(
    image: Image.Image,
    threshold: float,
    softness: float,
    radius: float,
    spread: int,
    intensity: float,
    blend: str,
    glow_color_mode: str,
    glow_color: str,
    preserve_core: bool,
) -> Image.Image:
    radius = max(0.0, float(radius))
    intensity = max(0.0, float(intensity))
    spread = max(0, int(spread))
    if radius <= 0.0 or intensity <= 0.0:
        return image

    base = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    luminance = 0.2126 * base[..., 0] + 0.7152 * base[..., 1] + 0.0722 * base[..., 2]
    weight = _soft_threshold_weight(luminance, threshold, softness)

    mode = str(glow_color_mode or "Source")
    if mode == "Custom Tint":
        tint = np.asarray(hex_to_rgb(glow_color), dtype=np.float32) / 255.0
        emit = weight[..., None] * tint[None, None, :]
    else:
        emit = base * weight[..., None]

    emit_img = Image.fromarray(np.clip(np.rint(emit * 255.0), 0, 255).astype(np.uint8), "RGB")
    if spread > 0:
        emit_img = emit_img.filter(ImageFilter.MaxFilter(size=max(3, spread * 2 + 1)))
    blurred = np.asarray(emit_img.filter(ImageFilter.GaussianBlur(radius=radius)), dtype=np.float32) / 255.0
    glow = np.clip(blurred * intensity, 0.0, 1.0)

    if preserve_core:
        work = base
    else:
        work = np.clip(base * (1.0 - 0.35 * weight[..., None]), 0.0, 1.0)

    if str(blend) == "Add":
        out = np.clip(work + glow, 0.0, 1.0)
    else:
        out = 1.0 - (1.0 - work) * (1.0 - glow)

    if preserve_core:
        out = np.maximum(out, base)
    return Image.fromarray(np.clip(np.rint(out * 255.0), 0, 255).astype(np.uint8), "RGB")


def _jpeg_compression(image: Image.Image, quality: int) -> Image.Image:
    quality = max(5, min(95, int(quality)))
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality, subsampling=2, optimize=False)
    buffer.seek(0)
    with Image.open(buffer) as decoded:
        decoded.load()
        return decoded.convert("RGB")


def _chromatic_shift(image: Image.Image, amount: int) -> Image.Image:
    return _rgb_split(image, amount, 0)


def _rgb_split(image: Image.Image, x: int, y: int) -> Image.Image:
    x, y = int(x), int(y)
    if x == 0 and y == 0:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    out[..., 0] = np.roll(np.roll(arr[..., 0], y, axis=0), x, axis=1)
    out[..., 2] = np.roll(np.roll(arr[..., 2], -y, axis=0), -x, axis=1)
    return Image.fromarray(out, "RGB")


def _posterize(image: Image.Image, levels: int) -> Image.Image:
    levels = max(2, min(64, int(levels)))
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    step = 255.0 / (levels - 1)
    return Image.fromarray(np.clip(np.rint(arr / step) * step, 0, 255).astype(np.uint8), "RGB")


def _scanlines(image: Image.Image, spacing: int, strength: float) -> Image.Image:
    spacing = max(2, int(spacing))
    strength = max(0.0, min(1.0, float(strength)))
    if strength <= 0:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32).copy()
    arr[::spacing] *= 1.0 - strength
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _interlace(image: Image.Image, offset: int, darken: float) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.float32).copy()
    arr[1::2] = np.roll(arr[1::2], int(offset), axis=1)
    arr[1::2] *= 1.0 - max(0.0, min(1.0, float(darken)))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _noise(image: Image.Image, amount: float, seed: int) -> Image.Image:
    amount = max(0.0, float(amount))
    if amount <= 0.0:
        return image
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    noise = rng.normal(0.0, amount, size=arr.shape[:2])[:, :, None]
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8), "RGB")


def _flicker(image: Image.Image, amount: float, speed: float, time_seconds: float) -> Image.Image:
    amount = max(0.0, min(1.0, float(amount)))
    if amount <= 0:
        return image
    phase = np.sin(2.0 * np.pi * max(0.0, float(speed)) * max(0.0, float(time_seconds)))
    return ImageEnhance.Brightness(image).enhance(max(0.0, 1.0 + amount * phase))


def _pixel_aspect_ratio(image: Image.Image, x: float, y: float, resample: str) -> Image.Image:
    """Stretch pixel width at this point in the layer stack.

    This is intentionally an image-space layer, separate from RasterMint's
    framebuffer/display PAR metadata. Its position therefore participates in
    layer ordering just like blur, dither, or chromatic shift.
    """
    x = max(0.25, min(4.0, float(x)))
    y = max(0.25, min(4.0, float(y)))
    ratio = x / y
    target_width = max(1, round(image.width * ratio))
    if target_width == image.width:
        return image
    methods = {
        "Nearest": Image.Resampling.NEAREST,
        "Bilinear": Image.Resampling.BILINEAR,
        "Bicubic": Image.Resampling.BICUBIC,
        "Lanczos": Image.Resampling.LANCZOS,
    }
    method = methods.get(str(resample), Image.Resampling.NEAREST)
    return image.resize((target_width, image.height), method)


def _pixelate(image: Image.Image, size: int) -> Image.Image:
    size = max(1, int(size))
    if size <= 1:
        return image
    w, h = image.size
    small = image.resize((max(1, w // size), max(1, h // size)), Image.Resampling.BOX)
    return small.resize((w, h), Image.Resampling.NEAREST)


def _pixel_sort(image: Image.Image, threshold: float, direction: str, reverse: bool) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    if direction == "Vertical":
        arr = np.transpose(arr, (1, 0, 2))
    lum = (0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]) / 255.0
    for y in range(arr.shape[0]):
        mask = lum[y] >= float(threshold)
        starts = np.flatnonzero(mask & np.r_[True, ~mask[:-1]])
        ends = np.flatnonzero(mask & np.r_[~mask[1:], True]) + 1
        for start, end in zip(starts, ends, strict=False):
            if end - start < 2:
                continue
            segment = arr[y, start:end]
            key = 0.2126 * segment[:, 0] + 0.7152 * segment[:, 1] + 0.0722 * segment[:, 2]
            order = np.argsort(key)
            if reverse:
                order = order[::-1]
            arr[y, start:end] = segment[order]
    if direction == "Vertical":
        arr = np.transpose(arr, (1, 0, 2))
    return Image.fromarray(arr, "RGB")


def _screen_melt(image: Image.Image, amount: int, column_width: int, seed: int) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    rng = np.random.default_rng(seed)
    width = max(1, int(column_width))
    max_drop = max(0, int(amount))
    if max_drop == 0:
        return image
    for x in range(0, arr.shape[1], width):
        drop = int(rng.integers(0, max_drop + 1))
        if drop:
            out[:, x:x + width] = np.roll(arr[:, x:x + width], drop, axis=0)
    return Image.fromarray(out, "RGB")


def _block_shuffle(image: Image.Image, block: int, amount: float, seed: int) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    b = max(2, int(block))
    coords = [(y, x) for y in range(0, arr.shape[0], b) for x in range(0, arr.shape[1], b)]
    if len(coords) < 2:
        return image
    rng = np.random.default_rng(seed)
    count = max(0, min(len(coords), round(len(coords) * max(0.0, min(1.0, amount)))))
    selected = list(rng.choice(len(coords), size=count, replace=False)) if count else []
    shuffled = selected.copy()
    rng.shuffle(shuffled)
    for dst_i, src_i in zip(selected, shuffled, strict=False):
        dy, dx = coords[dst_i]
        sy, sx = coords[src_i]
        h = min(b, arr.shape[0] - dy, arr.shape[0] - sy)
        w = min(b, arr.shape[1] - dx, arr.shape[1] - sx)
        out[dy:dy + h, dx:dx + w] = arr[sy:sy + h, sx:sx + w]
    return Image.fromarray(out, "RGB")


def _pixel_scatter(image: Image.Image, distance: int, density: float, seed: int) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    rng = np.random.default_rng(seed)
    h, w = arr.shape[:2]
    mask = rng.random((h, w)) < max(0.0, min(1.0, density))
    ys, xs = np.nonzero(mask)
    d = max(0, int(distance))
    if d == 0 or not len(xs):
        return image
    dx = rng.integers(-d, d + 1, size=len(xs))
    dy = rng.integers(-d, d + 1, size=len(xs))
    tx = np.clip(xs + dx, 0, w - 1)
    ty = np.clip(ys + dy, 0, h - 1)
    out[ty, tx] = arr[ys, xs]
    return Image.fromarray(out, "RGB")


def _data_shift(image: Image.Image, amount: int, band_height: int, seed: int) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    rng = np.random.default_rng(seed)
    band = max(1, int(band_height))
    amount = max(0, int(amount))
    for y in range(0, arr.shape[0], band):
        shift = int(rng.integers(-amount, amount + 1)) if amount else 0
        arr[y:y + band] = np.roll(arr[y:y + band], shift, axis=1)
    return Image.fromarray(arr, "RGB")


def _periodic_shift(image: Image.Image, amount: int, period: int, axis: int) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    amount = max(0, int(amount))
    period = max(1, int(period))
    if axis == 0:  # rows shifted horizontally
        for y in range(arr.shape[0]):
            shift = round(np.sin(y / period * np.pi) * amount)
            arr[y] = np.roll(arr[y], shift, axis=0)
    else:  # columns shifted vertically
        for x in range(arr.shape[1]):
            shift = round(np.sin(x / period * np.pi) * amount)
            arr[:, x] = np.roll(arr[:, x], shift, axis=0)
    return Image.fromarray(arr, "RGB")


def _cellular_automata(image: Image.Image, threshold: float, steps: int, blend: float) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    lum = (0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]) / 255.0
    cells = lum >= float(threshold)
    for _ in range(max(1, int(steps))):
        neighbors = np.zeros_like(cells, dtype=np.uint8)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                neighbors += np.roll(np.roll(cells, dy, axis=0), dx, axis=1)
        cells = (neighbors == 3) | (cells & (neighbors == 2))
    bw = np.where(cells[..., None], 255.0, 0.0)
    alpha = max(0.0, min(1.0, float(blend)))
    out = arr * (1.0 - alpha) + bw * alpha
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _databend(image: Image.Image, quality: int, shift: int, seed: int) -> Image.Image:
    compressed = _jpeg_compression(image, quality)
    return _data_shift(compressed, shift, max(2, compressed.height // 24), seed)


def _channel_swap(image: Image.Image, order: str) -> Image.Image:
    order = order if order in {"RGB", "RBG", "GRB", "GBR", "BRG", "BGR"} else "RGB"
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    index = {"R": 0, "G": 1, "B": 2}
    return Image.fromarray(arr[..., [index[c] for c in order]], "RGB")


def _material_sample(arr: np.ndarray, x: int, y: int, cell: int) -> tuple[int, int, int]:
    region = arr[y:min(arr.shape[0], y + cell), x:min(arr.shape[1], x + cell)]
    mean = np.mean(region.reshape(-1, 3), axis=0) if region.size else np.array([0, 0, 0])
    return tuple(int(v) for v in mean)


def _pixel_material(image: Image.Image, style: str, cell_size: int, gap: int, background: str, sprite_path: str) -> Image.Image:
    cell = max(2, int(cell_size))
    gap = max(0, min(cell // 2, int(gap)))
    bg = hex_to_rgb(background)
    source = np.asarray(image.convert("RGB"), dtype=np.uint8)
    canvas = Image.new("RGB", image.size, bg)
    draw = ImageDraw.Draw(canvas)
    sprite_mask: Image.Image | None = None
    if style == "Custom Sprite" and sprite_path:
        try:
            with Image.open(Path(sprite_path).expanduser()) as sprite:
                sprite_mask = sprite.convert("RGBA")
        except Exception:
            sprite_mask = None
    try:
        ascii_font = ImageFont.load_default(size=max(6, cell - gap * 2))
    except TypeError:  # Pillow fallback on older installations
        ascii_font = ImageFont.load_default()
    chars = " .:-=+*#%@"

    for y in range(0, image.height, cell):
        for x in range(0, image.width, cell):
            color = _material_sample(source, x, y, cell)
            x0, y0 = x + gap, y + gap
            x1, y1 = min(image.width - 1, x + cell - gap - 1), min(image.height - 1, y + cell - gap - 1)
            if x1 < x0 or y1 < y0:
                continue
            if style == "Flat":
                draw.rectangle((x0, y0, x1, y1), fill=color)
            elif style in {"Round Dots", "LED"}:
                draw.ellipse((x0, y0, x1, y1), fill=color)
                if style == "LED":
                    hi = tuple(min(255, c + 60) for c in color)
                    r = max(1, (x1 - x0) // 5)
                    draw.ellipse((x0 + r, y0 + r, x0 + r * 2, y0 + r * 2), fill=hi)
            elif style == "LCD":
                dark = tuple(max(0, int(c * 0.72)) for c in color)
                draw.rounded_rectangle((x0, y0, x1, y1), radius=max(1, cell // 8), fill=color, outline=dark)
            elif style == "Fuse Bead":
                draw.ellipse((x0, y0, x1, y1), fill=color)
                hole = max(1, cell // 6)
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                draw.ellipse((cx - hole, cy - hole, cx + hole, cy + hole), fill=bg)
            elif style == "Cross Stitch":
                width = max(1, cell // 6)
                draw.line((x0, y0, x1, y1), fill=color, width=width)
                draw.line((x1, y0, x0, y1), fill=color, width=width)
            elif style == "Brick":
                dark = tuple(max(0, int(c * 0.65)) for c in color)
                light = tuple(min(255, c + 35) for c in color)
                draw.rounded_rectangle((x0, y0, x1, y1), radius=max(1, cell // 8), fill=color, outline=dark)
                draw.line((x0 + 1, y0 + 1, x1 - 1, y0 + 1), fill=light, width=1)
            elif style == "Mosaic":
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                draw.polygon([(cx, y0), (x1, cy), (cx, y1), (x0, cy)], fill=color)
            elif style == "Halftone Dot":
                lum = (0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]) / 255.0
                radius = max(1, round((1.0 - lum * 0.55) * (x1 - x0 + 1) / 2))
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)
            elif style == "CRT Phosphor":
                width = max(1, (x1 - x0 + 1) // 3)
                channels = [(color[0], 0, 0), (0, color[1], 0), (0, 0, color[2])]
                for i, c in enumerate(channels):
                    sx0 = x0 + i * width
                    if sx0 > x1:
                        continue
                    sx1 = x1 if i == 2 else min(x1, sx0 + width - 1)
                    if sx1 >= sx0:
                        draw.rectangle((sx0, y0, sx1, y1), fill=c)
            elif style == "ASCII Tile":
                lum = (0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]) / 255.0
                char = chars[min(len(chars) - 1, round(lum * (len(chars) - 1)))]
                draw.text((x0, y0), char, font=ascii_font, fill=color)
            elif style == "Custom Sprite" and sprite_mask is not None:
                tile = sprite_mask.resize((max(1, x1 - x0 + 1), max(1, y1 - y0 + 1)), Image.Resampling.NEAREST)
                alpha = tile.getchannel("A")
                tint = Image.new("RGB", tile.size, color)
                canvas.paste(tint, (x0, y0), alpha)
            else:
                draw.rectangle((x0, y0, x1, y1), fill=color)
    return canvas



_FONT_FILES: dict[str, tuple[str, ...]] = {
    # DejaVu is common on Linux; the following candidates are standard fonts
    # on Windows/macOS. The old implementation tried only DejaVu names, which
    # made every option silently fall back to Pillow's default font on a
    # typical Windows RasterMint build.
    "Mono": ("DejaVuSansMono.ttf", "consola.ttf", "cour.ttf", "Courier New.ttf", "Menlo.ttc", "LiberationMono-Regular.ttf"),
    "Sans": ("DejaVuSans.ttf", "segoeui.ttf", "arial.ttf", "Arial.ttf", "Helvetica.ttc", "LiberationSans-Regular.ttf"),
    "Serif": ("DejaVuSerif.ttf", "times.ttf", "Times New Roman.ttf", "georgia.ttf", "Times.ttc", "LiberationSerif-Regular.ttf"),
    # Internal-only fallback family for Unicode symbols used by the ASCII/Glyph
    # sets. It is not exposed as a normal text-font option; it only fills a
    # missing glyph when the selected font cannot draw that character.
    "Symbol": (
        "seguisym.ttf", "Segoe UI Symbol.ttf", "seguiemj.ttf",
        "NotoSansSymbols2-Regular.ttf", "NotoSansSymbols-Regular.ttf",
        "Apple Symbols.ttf", "Arial Unicode.ttf", "Arial Unicode MS.ttf",
        "DejaVuSans.ttf", "FreeSerif.ttf",
    ),
}


def _font_search_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    windows_root = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
    if windows_root:
        roots.append(Path(windows_root) / "Fonts")
    roots.extend((
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation2"),
        Path("/usr/share/fonts/truetype/liberation"),
        Path("/usr/share/fonts/truetype/noto"),
        Path("/usr/share/fonts/truetype/freefont"),
        Path("/usr/share/fonts/opentype/noto"),
        Path("/System/Library/Fonts"),
        Path("/System/Library/Fonts/Supplemental"),
        Path("/Library/Fonts"),
    ))
    return tuple(roots)


@lru_cache(maxsize=8)
def _resolve_text_font_path(font_name: str) -> str | None:
    candidates = _FONT_FILES.get(str(font_name), _FONT_FILES["Mono"])
    for filename in candidates:
        for root in _font_search_roots():
            path = root / filename
            if path.is_file():
                return str(path)
        # Pillow also knows the native font lookup rules on some platforms.
        # Keep that path as a final resolver before falling back.
        try:
            probe = ImageFont.truetype(filename, size=12)
            resolved = getattr(probe, "path", None)
            if resolved:
                return str(resolved)
            return filename
        except (OSError, ValueError):
            continue
    return None

_GLYPH_SET_CATEGORIES: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("ASCII & Punctuation", (
        ("Classic ASCII", " .:-=+*#%@"),
        ("Dense ASCII", " .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"),
        ("Minimal ASCII", " .-+*#@"),
        ("Punctuation", " .'`,:;!iI|/\\()[]{}<>?*#@"),
        ("Typewriter", " .,:;i1tfLCG08@"),
        ("Technical", " ._-~=+<>[]{}()|/\\*#%@"),
    )),
    ("Numbers", (
        ("Binary", "01"),
        ("Decimal", " 0123456789"),
        ("Hex", " 0123456789ABCDEF"),
        ("Roman", " .IVXLCDM"),
        ("Digital", " .1470253689"),
    )),
    ("Blocks", (
        ("Blocks", " ░▒▓█"),
        ("Shade Blocks", " ░▒▓█"),
        ("Half Blocks", " ▂▄▆█"),
        ("Vertical Blocks", " ▁▂▃▄▅▆▇█"),
        ("Quadrants", " ▖▗▘▝▚▞▙▛▜▟█"),
    )),
    ("Braille", (
        ("Braille Low", " ⠂⠃⠇⠏⠟⠿⣿"),
        ("Braille Dense", " ⠁⠉⠋⠛⠟⠿⣿"),
        ("Braille Dots", " ⠂⠆⠇⠧⠷⠿⣿"),
        ("Braille Cells", " ⠀⠐⠒⠖⠶⠾⣿"),
    )),
    ("Geometric", (
        ("Squares", " ·▫▪□▣■"),
        ("Circles", " ·∘○◌◍●"),
        ("Diamonds", " ·◇◈◆"),
        ("Triangles", " ·△▽◁▷▲▼◀▶"),
        ("Mixed Geometry", " ·○□◇△◌◍▣◆●■"),
    )),
    ("Symbols", (
        ("Arrows", " ·←↑→↓↔↕⇐⇑⇒⇓"),
        ("Math", " .−+=×÷≈≠≤≥∞∑∫√"),
        ("Stars", " ·⋆✦✧★✹✺✸"),
        ("Currency", " .¢$€£¥₩₽₹"),
        ("Cards", " ·♤♡♢♧♠♥♦♣"),
    )),
    ("Line Art", (
        ("Box Light", " ·─│┌┐└┘├┤┬┴┼"),
        ("Box Heavy", " ·━┃┏┓┗┛┣┫┳┻╋"),
        ("Corners", " ·╭╮╰╯┌┐└┘"),
        ("Diagonals", " ./\\╱╲╳×#"),
    )),
    ("Letters", (
        ("Latin Lower", " .abcdefghijklmnopqrstuvwxyz"),
        ("Latin Upper", " .ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        ("Mixed Letters", " .ilIjtfrxvucszXYUJCLQOZmwqpdbkhaoMW"),
        ("Greek", " .ιτγλνχκπρσφωΨΩ"),
        ("Cyrillic", " .іґлптчжкмшщюяФЖШЩЮ"),
    )),
    ("Retro", (
        ("Terminal", " .,:;+*xX#%@"),
        ("DOS", " .░▒▓█"),
        ("Teletext", " .▖▗▘▝▚▞▙▛▜▟█"),
        ("LCD", " ._-:=+*#█"),
    )),
    ("Decorative", (
        ("Dots", " .·•∙●"),
        ("Crosses", " .+×✕✖✚✜"),
        ("Sparkles", " .·✧✦⋆★✹"),
        ("Flowers", " .·❀✿❁✾✽"),
        ("Music", " .·♪♫♩♬♭♯"),
    )),
    ("Custom", (
        ("Custom", ""),
    )),
)

_GLYPH_SETS = {
    name: chars
    for _category, sets in _GLYPH_SET_CATEGORIES
    for name, chars in sets
    if name != "Custom"
}

# Some character sets intentionally contain a zero-ink glyph as an additional
# darkest tone. U+2800 BRAILLE PATTERN BLANK is a real assigned character, but
# fonts correctly render it with no pixels. Treating "no ink" as "unsupported"
# drops it on Linux font stacks and makes the built-in set platform-dependent.
_INTENTIONAL_BLANK_GLYPHS = frozenset({" ", "⠀"})


def glyph_set_categories() -> list[dict[str, object]]:
    return [
        {
            "name": category,
            "sets": [
                {
                    "name": name,
                    "preview": (chars[:28] + ("…" if len(chars) > 28 else "")) if chars else "Your characters",
                }
                for name, chars in sets
            ],
        }
        for category, sets in _GLYPH_SET_CATEGORIES
    ]


def _decode_custom_glyphs(value: str) -> str:
    text = str(value or "")
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt == "s":
                out.append(" ")
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
            if nxt == "u" and i + 5 < len(text):
                token = text[i + 2:i + 6]
                try:
                    out.append(chr(int(token, 16)))
                    i += 6
                    continue
                except ValueError:
                    pass
        if ch not in "\r\n\t" and (ord(ch) >= 32 or ch == " "):
            out.append(ch)
        i += 1

    deduped: list[str] = []
    seen: set[str] = set()
    for ch in out:
        if ch not in seen:
            deduped.append(ch)
            seen.add(ch)
    return "".join(deduped)


def _glyph_chars(character_set: str, custom_chars: str, inject_chars: str = "") -> str:
    if str(character_set) == "Custom":
        chars = _decode_custom_glyphs(custom_chars)
    else:
        chars = _GLYPH_SETS.get(str(character_set), _GLYPH_SETS["Classic ASCII"])

    injected = _decode_custom_glyphs(inject_chars)
    if injected:
        merged: list[str] = []
        seen: set[str] = set()
        for ch in chars + injected:
            if ch not in seen:
                merged.append(ch)
                seen.add(ch)
        chars = "".join(merged)

    return chars if len(chars) >= 2 else _GLYPH_SETS["Classic ASCII"]


@lru_cache(maxsize=32)
def _font_candidate_refs(font_name: str) -> tuple[str, ...]:
    refs: list[str] = []
    seen: set[str] = set()
    for filename in _FONT_FILES.get(str(font_name), _FONT_FILES["Mono"]):
        found = False
        for root in _font_search_roots():
            path = root / filename
            if path.is_file():
                ref = str(path)
                key = ref.casefold()
                if key not in seen:
                    refs.append(ref)
                    seen.add(key)
                found = True
        if found:
            continue
        try:
            probe = ImageFont.truetype(filename, size=12)
            ref = str(getattr(probe, "path", None) or filename)
            key = ref.casefold()
            if key not in seen:
                refs.append(ref)
                seen.add(key)
        except (OSError, ValueError):
            continue
    return tuple(refs)


def _glyph_mask_fingerprint(font: ImageFont.ImageFont, font_size: int, ch: str) -> tuple[int, int, bytes] | None:
    if ch in _INTENTIONAL_BLANK_GLYPHS:
        return None
    canvas_size = max(24, int(font_size) * 2)
    mask = Image.new("L", (canvas_size, canvas_size), 0)
    draw = ImageDraw.Draw(mask)
    bbox = draw.textbbox((0, 0), ch, font=font)
    width = max(0, bbox[2] - bbox[0])
    height = max(0, bbox[3] - bbox[1])
    if width <= 0 or height <= 0:
        return None
    draw.text(
        ((canvas_size - width) / 2 - bbox[0], (canvas_size - height) / 2 - bbox[1]),
        ch,
        font=font,
        fill=255,
    )
    arr = np.asarray(mask, dtype=np.uint8)
    ys, xs = np.nonzero(arr)
    if ys.size == 0 or xs.size == 0:
        return None
    cropped = arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return (int(cropped.shape[0]), int(cropped.shape[1]), cropped.tobytes())


@lru_cache(maxsize=1024)
def _font_ref_supports_char(font_ref: str, font_size: int, ch: str) -> bool:
    if ch in _INTENTIONAL_BLANK_GLYPHS:
        return True
    try:
        font = ImageFont.truetype(font_ref, size=max(6, int(font_size)))
    except (OSError, ValueError):
        return False
    fingerprint = _glyph_mask_fingerprint(font, font_size, ch)
    if fingerprint is None:
        return False
    # Compare against unassigned/non-character code points. Fonts normally
    # render all unsupported code points using the same .notdef/tofu glyph.
    sentinels = ("\u0378", "\u0380", "\uFDD0")
    missing = {
        value for value in (_glyph_mask_fingerprint(font, font_size, item) for item in sentinels)
        if value is not None
    }
    return fingerprint not in missing


@lru_cache(maxsize=1024)
def _glyph_font_ref(font_name: str, font_size: int, ch: str) -> str | None:
    groups: list[str] = [str(font_name)] if str(font_name) in _FONT_FILES else ["Mono"]
    for fallback in ("Symbol", "Sans", "Serif", "Mono"):
        if fallback not in groups:
            groups.append(fallback)
    for group in groups:
        for ref in _font_candidate_refs(group):
            if _font_ref_supports_char(ref, font_size, ch):
                return ref
    return None


def _load_glyph_font(font_name: str, font_size: int, ch: str) -> ImageFont.ImageFont:
    size = max(2, int(font_size))
    if str(font_name) == "Pixel":
        try:
            primary = ImageFont.load_default(size=size)
        except TypeError:
            primary = ImageFont.load_default()
        if ch in _INTENTIONAL_BLANK_GLYPHS:
            return primary
        fingerprint = _glyph_mask_fingerprint(primary, size, ch)
        missing = {
            value for value in (
                _glyph_mask_fingerprint(primary, size, item)
                for item in ("\u0378", "\u0380", "\uFDD0")
            ) if value is not None
        }
        if fingerprint is not None and fingerprint not in missing:
            return primary
    ref = _glyph_font_ref(str(font_name), size, ch)
    if ref:
        try:
            return ImageFont.truetype(ref, size=size)
        except (OSError, ValueError):
            pass
    return _load_text_font(font_name, size)


@lru_cache(maxsize=256)
def ascii_available_chars(
    character_set: str,
    custom_chars: str,
    font_name: str,
    font_size: int,
    inject_chars: str = "",
) -> str:
    raw = _glyph_chars(character_set, custom_chars, inject_chars)
    supported: list[str] = []
    seen: set[str] = set()
    for ch in raw:
        if ch in seen:
            continue
        seen.add(ch)
        if ch in _INTENTIONAL_BLANK_GLYPHS:
            supported.append(ch)
            continue
        if _glyph_font_ref(str(font_name), max(6, int(font_size)), ch) is not None:
            supported.append(ch)
            continue
        if str(font_name) == "Pixel":
            font = _load_glyph_font("Pixel", max(6, int(font_size)), ch)
            fp = _glyph_mask_fingerprint(font, font_size, ch)
            if fp is not None:
                supported.append(ch)

    chars = "".join(supported)
    visible = [ch for ch in chars if not ch.isspace()]
    if len(visible) >= 2:
        return chars
    fallback = _GLYPH_SETS["Classic ASCII"]
    return fallback if len(fallback) >= 2 else " .:-=+*#%@"


def ascii_depth_max(
    character_set: str,
    custom_chars: str,
    font_name: str,
    font_size: int,
    inject_chars: str = "",
) -> int:
    """Maximum Character depth, counting visible glyphs only.

    A leading space is a useful transparent/empty tone but is not a visible
    symbol, so it must not turn Decimal's ten digits into an apparent depth of
    eleven or Diamonds' four visible marks into five. Injected glyphs are
    included after de-duplication and font fallback checks.
    """
    chars = ascii_available_chars(character_set, custom_chars, font_name, font_size, inject_chars)
    return max(2, len([ch for ch in chars if ch not in _INTENTIONAL_BLANK_GLYPHS]))


@lru_cache(maxsize=256)
def _glyph_density_order(chars: str, font_name: str, font_size: int) -> str:
    canvas_size = max(24, int(font_size) * 2)
    scored: list[tuple[float, int, str]] = []
    for index, ch in enumerate(chars):
        if ch in _INTENTIONAL_BLANK_GLYPHS:
            scored.append((0.0, index, ch))
            continue
        font = _load_glyph_font(font_name, max(6, int(font_size)), ch)
        mask = Image.new("L", (canvas_size, canvas_size), 0)
        draw = ImageDraw.Draw(mask)
        bbox = draw.textbbox((0, 0), ch, font=font)
        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])
        draw.text(
            ((canvas_size - width) / 2 - bbox[0], (canvas_size - height) / 2 - bbox[1]),
            ch,
            font=font,
            fill=255,
        )
        arr = np.asarray(mask, dtype=np.float32) / 255.0
        scored.append((float(arr.mean()), index, ch))
    scored.sort(key=lambda item: (item[0], item[1]))
    return "".join(item[2] for item in scored)


def _ascii_supersampling_factor(value: str | int | float) -> int:
    text = str(value or "1").strip().lower().replace("×", "x")
    if text.startswith("4"):
        return 4
    if text.startswith("2"):
        return 2
    return 1


@lru_cache(maxsize=2048)
def _glyph_visual_mask(
    font_name: str,
    font_size: int,
    ch: str,
    supersampling: int = 1,
) -> np.ndarray:
    """Render a glyph into a tightly cropped alpha mask.

    High-detail ASCII renders glyphs above final resolution and downsamples the
    mask, improving tiny serif/Unicode shapes without changing the output
    raster size. The returned mask may be larger than the nominal cell so glyph
    scale above 1.0 can still overlap neighbouring cells naturally.
    """
    if ch in _INTENTIONAL_BLANK_GLYPHS:
        return np.zeros((1, 1), dtype=np.uint8)

    ss = max(1, min(4, int(supersampling)))
    hi_size = max(2, int(font_size) * ss)
    font = _load_glyph_font(font_name, hi_size, ch)
    probe_size = max(24, hi_size * 4)
    probe = Image.new("L", (probe_size, probe_size), 0)
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), ch, font=font)
    width = max(1, bbox[2] - bbox[0])
    height = max(1, bbox[3] - bbox[1])
    pad = max(2, ss * 2)
    mask = Image.new("L", (width + pad * 2, height + pad * 2), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text((pad - bbox[0], pad - bbox[1]), ch, font=font, fill=255)

    arr = np.asarray(mask, dtype=np.uint8)
    ys, xs = np.nonzero(arr)
    if ys.size == 0 or xs.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    cropped = Image.fromarray(
        arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1],
        mode="L",
    )
    if ss > 1:
        cropped = cropped.resize(
            (
                max(1, round(cropped.width / ss)),
                max(1, round(cropped.height / ss)),
            ),
            Image.Resampling.LANCZOS,
        )
    return np.asarray(cropped, dtype=np.uint8).copy()


@lru_cache(maxsize=4096)
def _glyph_cell_mask(
    font_name: str,
    font_size: int,
    ch: str,
    cell_width: int,
    cell_height: int,
    supersampling: int,
) -> np.ndarray:
    """Return a glyph mask clipped to one ASCII source cell."""
    width = max(1, int(cell_width))
    height = max(1, int(cell_height))
    canvas = np.zeros((height, width), dtype=np.uint8)
    if ch in _INTENTIONAL_BLANK_GLYPHS:
        return canvas

    glyph = _glyph_visual_mask(font_name, font_size, ch, supersampling)
    gh, gw = glyph.shape
    left = round((width - gw) / 2)
    top = round((height - gh) / 2)

    src_x0 = max(0, -left)
    src_y0 = max(0, -top)
    dst_x0 = max(0, left)
    dst_y0 = max(0, top)
    copy_w = min(gw - src_x0, width - dst_x0)
    copy_h = min(gh - src_y0, height - dst_y0)
    if copy_w > 0 and copy_h > 0:
        canvas[dst_y0:dst_y0 + copy_h, dst_x0:dst_x0 + copy_w] = glyph[
            src_y0:src_y0 + copy_h,
            src_x0:src_x0 + copy_w,
        ]
    return canvas


def _ascii_cell_geometry(
    chars: str,
    font_name: str,
    font_size: int,
    cell_size: int,
    spacing_x: int,
    spacing_y: int,
    auto_cell_aspect: bool,
) -> tuple[int, int, int, int]:
    cell_height = max(4, int(cell_size))
    cell_width = cell_height
    if auto_cell_aspect:
        ratios: list[float] = []
        for ch in chars:
            if ch in _INTENTIONAL_BLANK_GLYPHS:
                continue
            glyph = _glyph_visual_mask(font_name, font_size, ch, 1)
            gh, gw = glyph.shape
            if gh > 0 and gw > 0:
                ratios.append(float(gw) / float(gh))
        if ratios:
            # The median is resistant to unusually wide glyphs while still
            # reflecting the selected font/set. Most text fonts naturally land
            # around 0.5-0.7, producing denser columns without stretching the
            # source image.
            aspect = float(np.median(np.asarray(ratios, dtype=np.float32)))
            aspect = max(0.35, min(1.0, aspect))
            cell_width = max(2, round(cell_height * aspect))

    pitch_x = max(1, cell_width + int(spacing_x))
    pitch_y = max(1, cell_height + int(spacing_y))
    return cell_width, cell_height, pitch_x, pitch_y


@lru_cache(maxsize=512)
def _ascii_structure_templates(
    chars: str,
    font_name: str,
    font_size: int,
    cell_width: int,
    cell_height: int,
    supersampling: int,
    match_size: int = 8,
) -> tuple[np.ndarray, np.ndarray]:
    size = max(4, int(match_size))
    templates: list[np.ndarray] = []
    densities: list[float] = []
    for ch in chars:
        mask = _glyph_cell_mask(
            font_name,
            font_size,
            ch,
            cell_width,
            cell_height,
            supersampling,
        )
        if mask.shape != (size, size):
            sample = Image.fromarray(mask, mode="L").resize(
                (size, size),
                Image.Resampling.BILINEAR,
            )
            arr = np.asarray(sample, dtype=np.float32) / 255.0
        else:
            arr = mask.astype(np.float32) / 255.0
        templates.append(arr.reshape(-1))
        densities.append(float(arr.mean()))
    return np.asarray(templates, dtype=np.float32), np.asarray(densities, dtype=np.float32)


def _sample_ascii_structure(
    luminance: np.ndarray,
    alpha: np.ndarray,
    *,
    size: int = 8,
    invert: bool = False,
    local_detail: float = 0.0,
) -> np.ndarray:
    """Sample a source cell into a small structure descriptor.

    Area averaging is used instead of point sampling so one-pixel/thin edges
    cannot disappear just because they fall between the 8x8 sample positions.
    """
    h, w = luminance.shape
    if h <= 0 or w <= 0:
        return np.zeros(size * size, dtype=np.float32)

    source_luminance = np.clip(luminance.astype(np.float32), 0.0, 1.0)
    source_alpha = np.clip(alpha.astype(np.float32), 0.0, 1.0)
    weighted = (1.0 - source_luminance if invert else source_luminance) * source_alpha
    if h < size or w < size:
        sampled = np.asarray(
            Image.fromarray(np.clip(np.rint(weighted * 255.0), 0, 255).astype(np.uint8), mode="L").resize(
                (size, size),
                Image.Resampling.BILINEAR,
            ),
            dtype=np.float32,
        ) / 255.0
    else:
        y_edges = np.rint(np.linspace(0, h, size + 1)).astype(np.int32)
        x_edges = np.rint(np.linspace(0, w, size + 1)).astype(np.int32)
        integral = np.pad(weighted.cumsum(axis=0).cumsum(axis=1), ((1, 0), (1, 0)))
        y0, y1 = y_edges[:-1], y_edges[1:]
        x0, x1 = x_edges[:-1], x_edges[1:]
        sums = (
            integral[y1[:, None], x1[None, :]]
            - integral[y0[:, None], x1[None, :]]
            - integral[y1[:, None], x0[None, :]]
            + integral[y0[:, None], x0[None, :]]
        )
        areas = np.maximum(1, (y1 - y0)[:, None] * (x1 - x0)[None, :])
        sampled = sums / areas

    detail = max(0.0, min(1.0, float(local_detail) / 100.0))
    if detail > 0.0:
        mean = float(sampled.mean())
        gain = 1.0 + 3.0 * detail
        enhanced = np.clip(mean + (sampled - mean) * gain, 0.0, 1.0)
        sampled = sampled * (1.0 - detail) + enhanced * detail
    return sampled.reshape(-1).astype(np.float32)


def _ascii_weighted_colour(
    rgb: np.ndarray,
    alpha: np.ndarray,
    char: str,
    *,
    font_name: str,
    font_size: int,
    cell_width: int,
    cell_height: int,
    supersampling: int,
    fallback: np.ndarray,
) -> np.ndarray:
    if char in _INTENTIONAL_BLANK_GLYPHS:
        return fallback
    mask = _glyph_cell_mask(
        font_name,
        font_size,
        char,
        cell_width,
        cell_height,
        supersampling,
    ).astype(np.float32) / 255.0
    h, w = rgb.shape[:2]
    mask = mask[:h, :w]
    weights = mask * alpha[:mask.shape[0], :mask.shape[1]]
    denom = float(weights.sum())
    if denom <= 1e-6:
        return fallback
    sampled_rgb = rgb[:mask.shape[0], :mask.shape[1]]
    return (sampled_rgb * weights[..., None]).sum(axis=(0, 1)) / denom


def _load_text_font(font_name: str, size: int) -> ImageFont.ImageFont:
    size = max(6, int(size))
    if font_name == "Pixel":
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    resolved = _resolve_text_font_path(str(font_name))
    if resolved:
        try:
            return ImageFont.truetype(resolved, size=size)
        except (OSError, ValueError):
            # A system font can disappear between resolution and rendering;
            # retry the remaining semantic candidates before giving up.
            pass
    for filename in _FONT_FILES.get(str(font_name), _FONT_FILES["Mono"]):
        try:
            return ImageFont.truetype(filename, size=size)
        except (OSError, ValueError):
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _text_line_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, letter_spacing: int = 0) -> int:
    if not text:
        return 0
    if letter_spacing == 0:
        return max(1, int(round(draw.textlength(text, font=font))))
    widths = [float(draw.textlength(ch, font=font)) for ch in text]
    return max(1, int(round(sum(widths) + max(0, len(text) - 1) * letter_spacing)))


def _wrap_text_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, letter_spacing: int = 0) -> list[str]:
    max_width = max(1, int(max_width))
    result: list[str] = []
    for paragraph in str(text).splitlines() or [""]:
        words = paragraph.split(" ")
        if not words:
            result.append("")
            continue
        line = ""
        for word in words:
            candidate = word if not line else f"{line} {word}"
            if not line or _text_line_width(draw, candidate, font, letter_spacing) <= max_width:
                line = candidate
                continue
            result.append(line)
            line = word
            if _text_line_width(draw, line, font, letter_spacing) > max_width:
                piece = ""
                for ch in line:
                    candidate_piece = piece + ch
                    if piece and _text_line_width(draw, candidate_piece, font, letter_spacing) > max_width:
                        result.append(piece)
                        piece = ch
                    else:
                        piece = candidate_piece
                line = piece
        result.append(line)
    return result or [""]


def _draw_spaced_line(
    draw: ImageDraw.ImageDraw,
    pos: tuple[int, int],
    text: str,
    *,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    letter_spacing: int = 0,
    stroke_width: int = 0,
    stroke_fill: tuple[int, int, int] | tuple[int, int, int, int] = (0, 0, 0),
) -> None:
    x, y = pos
    if letter_spacing == 0:
        draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        return
    cursor = float(x)
    for ch in text:
        draw.text((round(cursor), y), ch, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        cursor += float(draw.textlength(ch, font=font)) + letter_spacing


def _spaced_line_bbox(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font: ImageFont.ImageFont,
    letter_spacing: int = 0,
    stroke_width: int = 0,
) -> tuple[int, int, int, int]:
    """Return the visual bounds of a line drawn at origin.

    Pillow's default text anchor is not the visual top-left: large fonts can
    have a sizeable positive top offset and descenders can extend below the
    nominal line height. Measuring those offsets explicitly prevents the
    temporary text layer from clipping glyphs when the font size changes.
    """
    value = str(text)
    if not value:
        return draw.textbbox((0, 0), "Mg", font=font, stroke_width=max(0, int(stroke_width)))
    if int(letter_spacing) == 0:
        return draw.textbbox((0, 0), value, font=font, stroke_width=max(0, int(stroke_width)))

    cursor = 0.0
    left = top = None
    right = bottom = None
    for ch in value:
        bbox = draw.textbbox(
            (round(cursor), 0),
            ch,
            font=font,
            stroke_width=max(0, int(stroke_width)),
        )
        left = bbox[0] if left is None else min(left, bbox[0])
        top = bbox[1] if top is None else min(top, bbox[1])
        right = bbox[2] if right is None else max(right, bbox[2])
        bottom = bbox[3] if bottom is None else max(bottom, bbox[3])
        cursor += float(draw.textlength(ch, font=font)) + int(letter_spacing)
    return (
        int(math.floor(left or 0)),
        int(math.floor(top or 0)),
        int(math.ceil(right or 0)),
        int(math.ceil(bottom or 0)),
    )


def _render_text_block(
    text: str,
    *,
    size: int,
    color: str,
    font_name: str,
    max_width: int,
    alignment: str = "Center",
    letter_spacing: int = 0,
    line_spacing: int = 0,
    outline: int = 0,
    shadow: int = 0,
) -> Image.Image:
    font = _load_text_font(font_name, size)
    # textbbox/textlength do not depend on the backing canvas dimensions. A
    # tiny probe avoids allocating a large throwaway image for big text sizes.
    probe = Image.new("L", (2, 2), 0)
    measure = ImageDraw.Draw(probe)
    lines = _wrap_text_lines(measure, str(text), font, max_width, letter_spacing)
    outline_px = max(0, int(outline))
    shadow_px = max(0, int(shadow))
    gap = max(0, int(line_spacing))

    metrics: list[tuple[tuple[int, int, int, int], int, int]] = []
    for line in lines:
        bbox = _spaced_line_bbox(
            measure,
            line,
            font=font,
            letter_spacing=int(letter_spacing),
            stroke_width=outline_px,
        )
        visual_width = 0 if not line else max(1, bbox[2] - bbox[0])
        visual_height = max(1, bbox[3] - bbox[1])
        metrics.append((bbox, visual_width, visual_height))

    content_width = max(1, max((item[1] for item in metrics), default=1))
    content_height = max(
        1,
        sum(item[2] for item in metrics) + max(0, len(metrics) - 1) * gap,
    )
    # Wrapping constrains the layout width, but the visual bounds may extend a
    # few pixels beyond that width because of glyph overhang, outline or a
    # single glyph larger than max_width. Never crop those pixels.
    block_width = max(1, content_width + shadow_px)
    block_height = max(1, content_height + shadow_px)
    layer = Image.new("RGBA", (block_width, block_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    fill = (*hex_to_rgb(color), 255)
    stroke = (0, 0, 0, 255)

    visual_y = 0
    for line, (bbox, visual_width, visual_height) in zip(lines, metrics, strict=False):
        if alignment == "Left":
            visual_x = 0
        elif alignment == "Right":
            visual_x = max(0, content_width - visual_width)
        else:
            visual_x = max(0, (content_width - visual_width) // 2)

        # Convert desired visual top-left coordinates back to Pillow's default
        # text origin by subtracting the measured glyph offsets.
        x = round(visual_x - bbox[0])
        y = round(visual_y - bbox[1])
        if line:
            if shadow_px > 0:
                _draw_spaced_line(
                    draw,
                    (x + shadow_px, y + shadow_px),
                    line,
                    font=font,
                    fill=(0, 0, 0, 200),
                    letter_spacing=letter_spacing,
                    stroke_width=outline_px,
                    stroke_fill=stroke,
                )
            _draw_spaced_line(
                draw,
                (x, y),
                line,
                font=font,
                fill=fill,
                letter_spacing=letter_spacing,
                stroke_width=outline_px,
                stroke_fill=stroke,
            )
        visual_y += visual_height + gap
    return layer

def _paste_centered_rgba(base: Image.Image, layer: Image.Image, x_percent: float, y_percent: float) -> Image.Image:
    canvas = base.convert("RGBA")
    px = round(canvas.width * max(0.0, min(100.0, float(x_percent))) / 100.0)
    py = round(canvas.height * max(0.0, min(100.0, float(y_percent))) / 100.0)
    pos = (round(px - layer.width / 2), round(py - layer.height / 2))
    canvas.alpha_composite(layer, dest=pos)
    return canvas.convert("RGB")


def _ascii_mapping_chars(
    character_set: str,
    custom_chars: str,
    depth: int,
    offset: int,
    auto_density: bool,
    font_name: str,
    font_size: int,
    inject_chars: str = "",
) -> str:
    chars = ascii_available_chars(
        character_set,
        custom_chars,
        font_name,
        max(6, int(font_size)),
        inject_chars,
    )
    if auto_density:
        chars = _glyph_density_order(chars, font_name, max(6, int(font_size)))

    # Character depth describes visible symbols. Space remains an optional
    # empty/dark tone but no longer consumes one depth slot in the UI.
    blanks = "".join(ch for ch in chars if ch in _INTENTIONAL_BLANK_GLYPHS)
    visible = "".join(ch for ch in chars if ch not in _INTENTIONAL_BLANK_GLYPHS)
    depth = max(2, min(len(visible), int(depth)))
    if len(visible) > depth:
        indices = np.linspace(0, len(visible) - 1, depth).round().astype(int)
        visible = "".join(visible[i] for i in indices)

    # Keep only one regular space as the conventional empty tone. Other
    # intentional zero-ink glyphs (for example Braille blank) remain available
    # as real user-selected symbols.
    has_space = " " in blanks
    nonspace_blanks = "".join(ch for ch in blanks if ch != " ")
    chars = ((" " if has_space else "") + nonspace_blanks + visible) or " .:-=+*#%@"
    shift = int(offset) % len(chars)
    if shift:
        chars = chars[-shift:] + chars[:-shift]
    return chars


def _ascii_grid_data(
    image: Image.Image,
    character_set: str,
    custom_chars: str,
    cell_size: int,
    spacing_x: int,
    spacing_y: int,
    depth: int,
    offset: int,
    invert: bool,
    auto_density: bool,
    font_name: str,
    font_scale: float,
    *,
    inject_chars: str = "",
    mapping: str = "Density",
    structure: float = 75.0,
    density_influence: float = 25.0,
    local_detail: float = 35.0,
    auto_cell_aspect: bool = True,
    supersampling: str = "4×",
    color_sampling: str = "Glyph Weighted",
) -> tuple[list[str], list[list[np.ndarray]], dict[str, int | str | bool]]:
    cell_height = max(4, int(cell_size))
    font_size = max(2, round(cell_height * max(0.4, min(1.5, float(font_scale)))))
    chars = _ascii_mapping_chars(
        character_set,
        custom_chars,
        depth,
        offset,
        auto_density,
        font_name,
        font_size,
        inject_chars,
    )
    high_detail = str(mapping) == "Structure Match"
    ss = _ascii_supersampling_factor(supersampling) if high_detail else 1
    cell_width, cell_height, pitch_x, pitch_y = _ascii_cell_geometry(
        chars,
        font_name,
        font_size,
        cell_height,
        spacing_x,
        spacing_y,
        bool(auto_cell_aspect) if high_detail else False,
    )

    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    rgb_all = rgba[..., :3].astype(np.float32)
    alpha_all = rgba[..., 3].astype(np.float32) / 255.0
    lum_all = (
        0.2126 * rgb_all[..., 0]
        + 0.7152 * rgb_all[..., 1]
        + 0.0722 * rgb_all[..., 2]
    ) / 255.0

    rows: list[list[dict[str, object]]] = []
    opaque_records: list[dict[str, object]] = []
    for y in range(0, image.height, pitch_y):
        row_records: list[dict[str, object]] = []
        for x in range(0, image.width, pitch_x):
            y1 = min(rgba.shape[0], y + cell_height)
            x1 = min(rgba.shape[1], x + cell_width)
            region_rgb = rgb_all[y:y1, x:x1]
            region_alpha = alpha_all[y:y1, x:x1]
            if not region_rgb.size:
                continue

            alpha_mean = float(region_alpha.mean())
            weights = region_alpha[..., None]
            denom = max(1e-6, float(weights.sum()))
            mean = (region_rgb * weights).sum(axis=(0, 1)) / denom if alpha_mean > 0.01 else np.zeros(3, dtype=np.float32)
            record: dict[str, object] = {
                "x": x,
                "y": y,
                "rgb": region_rgb,
                "alpha": region_alpha,
                "mean": mean.astype(np.float32),
                "char": " ",
            }

            if alpha_mean > 0.01:
                if high_detail:
                    target = _sample_ascii_structure(
                        lum_all[y:y1, x:x1],
                        region_alpha,
                        invert=bool(invert),
                        local_detail=float(local_detail),
                    )
                    record["target"] = target
                    opaque_records.append(record)
                else:
                    lum = float(
                        0.2126 * mean[0] + 0.7152 * mean[1] + 0.0722 * mean[2]
                    ) / 255.0
                    if invert:
                        lum = 1.0 - lum
                    index = max(0, min(len(chars) - 1, int(round(lum * (len(chars) - 1)))))
                    record["char"] = chars[index]
            row_records.append(record)
        rows.append(row_records)

    if high_detail and opaque_records:
        templates, template_density = _ascii_structure_templates(
            chars,
            font_name,
            font_size,
            cell_width,
            cell_height,
            ss,
        )
        targets = np.asarray([record["target"] for record in opaque_records], dtype=np.float32)
        structure_weight = max(0.0, min(1.0, float(structure) / 100.0))
        density_weight = max(0.0, min(1.0, float(density_influence) / 100.0))
        if structure_weight <= 1e-6 and density_weight <= 1e-6:
            structure_weight = 1.0

        template_sq = np.sum(templates * templates, axis=1)
        chosen = np.empty(len(targets), dtype=np.int32)
        chunk_size = max(256, min(8192, 2_000_000 // max(1, len(chars))))
        for begin in range(0, len(targets), chunk_size):
            finish = min(len(targets), begin + chunk_size)
            chunk = targets[begin:finish]
            chunk_sq = np.sum(chunk * chunk, axis=1, keepdims=True)
            # Mean squared structure difference using the expanded
            # ||a-b||² identity keeps the temporary matrix bounded.
            structure_error = (
                chunk_sq + template_sq[None, :] - 2.0 * (chunk @ templates.T)
            ) / max(1, templates.shape[1])
            target_density = chunk.mean(axis=1, keepdims=True)
            density_error = (target_density - template_density[None, :]) ** 2
            score = structure_weight * structure_error + density_weight * density_error
            chosen[begin:finish] = np.argmin(score, axis=1)

        for record, index in zip(opaque_records, chosen, strict=True):
            record["char"] = chars[int(index)]

    lines: list[str] = []
    colors: list[list[np.ndarray]] = []
    glyph_weighted = high_detail and str(color_sampling) == "Glyph Weighted"
    for row_records in rows:
        line_chars: list[str] = []
        line_colors: list[np.ndarray] = []
        for record in row_records:
            char = str(record["char"])
            mean = np.asarray(record["mean"], dtype=np.float32)
            if glyph_weighted and char not in _INTENTIONAL_BLANK_GLYPHS:
                mean = _ascii_weighted_colour(
                    np.asarray(record["rgb"], dtype=np.float32),
                    np.asarray(record["alpha"], dtype=np.float32),
                    char,
                    font_name=font_name,
                    font_size=font_size,
                    cell_width=cell_width,
                    cell_height=cell_height,
                    supersampling=ss,
                    fallback=mean,
                ).astype(np.float32)
            line_chars.append(char)
            line_colors.append(mean)
        lines.append("".join(line_chars).rstrip())
        colors.append(line_colors)

    while lines and lines[-1] == "":
        lines.pop()
        colors.pop()

    layout: dict[str, int | str | bool] = {
        "cell_width": cell_width,
        "cell_height": cell_height,
        "pitch_x": pitch_x,
        "pitch_y": pitch_y,
        "font_size": font_size,
        "supersampling": ss,
        "high_detail": high_detail,
    }
    return lines or [""], colors or [[]], layout

def ascii_text_grid(
    image: Image.Image,
    *,
    character_set: str,
    custom_chars: str,
    cell_size: int,
    spacing_x: int,
    spacing_y: int,
    depth: int,
    offset: int,
    invert: bool,
    auto_density: bool,
    font_name: str,
    font_scale: float,
    inject_chars: str = "",
    mapping: str = "Density",
    structure: float = 75.0,
    density_influence: float = 25.0,
    local_detail: float = 35.0,
    auto_cell_aspect: bool = True,
    supersampling: str = "4×",
    color_sampling: str = "Glyph Weighted",
) -> str:
    lines, _colors, _layout = _ascii_grid_data(
        image,
        character_set,
        custom_chars,
        cell_size,
        spacing_x,
        spacing_y,
        depth,
        offset,
        invert,
        auto_density,
        font_name,
        font_scale,
        inject_chars=inject_chars,
        mapping=mapping,
        structure=structure,
        density_influence=density_influence,
        local_detail=local_detail,
        auto_cell_aspect=auto_cell_aspect,
        supersampling=supersampling,
        color_sampling=color_sampling,
    )
    return "\n".join(lines) + "\n"


def ascii_text_grid_for_stack(
    image: Image.Image,
    stack: list[dict[str, Any]],
    palette: list[str],
    *,
    frame_time: float = 0.0,
    frame_index: int = 0,
) -> str | None:
    normalized = normalize_effect_stack(stack)
    target_index = -1
    for index, step in enumerate(normalized):
        if step.get("enabled", True) and step.get("kind") == "ASCII / Glyph":
            target_index = index
    if target_index < 0:
        return None
    if target_index == 0:
        before = image
    else:
        before = apply_effect_stack(
            image,
            normalized[:target_index],
            palette,
            frame_time=frame_time,
            frame_index=frame_index,
        )
    p = normalized[target_index]["params"]
    return ascii_text_grid(
        before,
        character_set=str(p.get("character_set", "Classic ASCII")),
        custom_chars=str(p.get("custom_chars", " .:-=+*#%@")),
        inject_chars=str(p.get("inject_chars", "")),
        mapping=str(p.get("mapping", "Density")),
        cell_size=int(p.get("cell_size", 10)),
        spacing_x=int(p.get("spacing_x", 0)),
        spacing_y=int(p.get("spacing_y", 0)),
        depth=int(p.get("depth", 9)),
        offset=int(p.get("offset", 0)),
        invert=bool(p.get("invert", False)),
        auto_density=bool(p.get("auto_density", True)),
        structure=float(p.get("structure", 75.0)),
        density_influence=float(p.get("density_influence", 25.0)),
        local_detail=float(p.get("local_detail", 35.0)),
        auto_cell_aspect=bool(p.get("auto_cell_aspect", True)),
        supersampling=str(p.get("supersampling", "4×")),
        color_sampling=str(p.get("color_sampling", "Glyph Weighted")),
        font_name=str(p.get("font", "Mono")),
        font_scale=float(p.get("font_scale", 0.9)),
    )


def _ascii_glyph(
    image: Image.Image,
    character_set: str,
    custom_chars: str,
    auto_density: bool,
    cell_size: int,
    spacing_x: int,
    spacing_y: int,
    depth: int,
    offset: int,
    invert: bool,
    color_mode: str,
    foreground: str,
    background_mode: str,
    background: str,
    font_name: str,
    font_scale: float,
    palette_np: np.ndarray,
    *,
    inject_chars: str = "",
    mapping: str = "Density",
    structure: float = 75.0,
    density_influence: float = 25.0,
    local_detail: float = 35.0,
    auto_cell_aspect: bool = True,
    supersampling: str = "4×",
    color_sampling: str = "Glyph Weighted",
) -> Image.Image:
    lines, mean_colors, layout = _ascii_grid_data(
        image,
        character_set,
        custom_chars,
        cell_size,
        spacing_x,
        spacing_y,
        depth,
        offset,
        invert,
        auto_density,
        font_name,
        font_scale,
        inject_chars=inject_chars,
        mapping=mapping,
        structure=structure,
        density_influence=density_influence,
        local_detail=local_detail,
        auto_cell_aspect=auto_cell_aspect,
        supersampling=supersampling,
        color_sampling=color_sampling,
    )

    mode = str(background_mode)
    if mode == "Transparent":
        canvas = Image.new("RGBA", image.size, (0, 0, 0, 0))
    elif mode == "Source Image":
        canvas = image.convert("RGBA")
    else:
        canvas = Image.new("RGBA", image.size, (*hex_to_rgb(background), 255))

    draw = ImageDraw.Draw(canvas)
    cell_width = int(layout["cell_width"])
    cell_height = int(layout["cell_height"])
    pitch_x = int(layout["pitch_x"])
    pitch_y = int(layout["pitch_y"])
    font_size = int(layout["font_size"])
    ss = int(layout["supersampling"])
    high_detail = bool(layout["high_detail"])
    single = hex_to_rgb(foreground)

    for row, line in enumerate(lines):
        y = row * pitch_y
        row_colors = mean_colors[row] if row < len(mean_colors) else []
        for col, char in enumerate(line):
            x = col * pitch_x
            mean = row_colors[col] if col < len(row_colors) else np.array(single, dtype=np.float32)
            if color_mode == "Single Colour":
                color = single
            elif color_mode == "Palette" and palette_np.size:
                diff = palette_np.astype(np.float32) - mean.astype(np.float32)
                color = tuple(int(v) for v in palette_np[int(np.argmin(np.sum(diff * diff, axis=1)))])
            else:
                color = tuple(int(round(v)) for v in mean)

            if char in _INTENTIONAL_BLANK_GLYPHS:
                continue

            if high_detail:
                glyph = _glyph_visual_mask(font_name, font_size, char, ss)
                glyph_image = Image.fromarray(glyph, mode="L")
                layer = Image.new("RGBA", glyph_image.size, (*color, 0))
                layer.putalpha(glyph_image)
                gx = round(x + (cell_width - glyph_image.width) / 2)
                gy = round(y + (cell_height - glyph_image.height) / 2)
                canvas.alpha_composite(layer, dest=(gx, gy))
            else:
                font = _load_glyph_font(font_name, font_size, char)
                bbox = draw.textbbox((0, 0), char, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                draw.text(
                    (
                        x + (cell_width - tw) / 2,
                        y + (cell_height - th) / 2 - bbox[1],
                    ),
                    char,
                    font=font,
                    fill=(*color, 255),
                )
    return canvas


def _pixel_text(
    image: Image.Image,
    text: str,
    x: float,
    y: float,
    size: int,
    color: str,
    font_name: str,
    alignment: str,
    wrap_width: float,
    letter_spacing: int,
    line_spacing: int,
    rotation: float,
    outline: int,
    shadow: int,
) -> Image.Image:
    max_width = max(16, round(image.width * max(0.1, min(1.0, float(wrap_width) / 100.0))))
    layer = _render_text_block(
        text,
        size=size,
        color=color,
        font_name=font_name,
        max_width=max_width,
        alignment=alignment,
        letter_spacing=int(letter_spacing),
        line_spacing=int(line_spacing),
        outline=int(outline),
        shadow=int(shadow),
    )
    if abs(float(rotation)) > 1e-6:
        layer = layer.rotate(-float(rotation), resample=Image.Resampling.NEAREST, expand=True)
    return _paste_centered_rgba(image, layer, x, y)


def _text_pattern(image: Image.Image, text: str, size: int, color: str, font_name: str, spacing_x: int, spacing_y: int, offset_x: int, rotation: float, opacity: float) -> Image.Image:
    font = _load_text_font(font_name, size)
    rgb = hex_to_rgb(color)
    alpha = round(255 * max(0.0, min(1.0, float(opacity))))
    sx = max(12, int(spacing_x))
    sy = max(12, int(spacing_y))
    angle = float(rotation)

    # Rotating an image-sized overlay in place produces transparent corner
    # wedges. Render the pattern on the inverse-rotation bounding rectangle,
    # rotate that larger surface, then crop the centered source-sized region.
    # This keeps the repeating pattern continuous all the way to every edge.
    radians = math.radians(angle)
    cos_a = abs(math.cos(radians))
    sin_a = abs(math.sin(radians))
    cover_width = max(1, math.ceil(image.width * cos_a + image.height * sin_a))
    cover_height = max(1, math.ceil(image.width * sin_a + image.height * cos_a))

    probe = Image.new("L", (2, 2), 0)
    probe_draw = ImageDraw.Draw(probe)
    text_bbox = probe_draw.textbbox((0, 0), str(text) or " ", font=font)
    text_width = max(1, text_bbox[2] - text_bbox[0])
    text_height = max(1, text_bbox[3] - text_bbox[1])
    if abs(angle) > 1e-6:
        margin_x = max(sx, abs(int(offset_x)), max(12, int(size) * 2))
        margin_y = max(sy, max(12, int(size) * 2))
        work_width = cover_width + margin_x * 2
        work_height = cover_height + margin_y * 2
    else:
        work_width = image.width
        work_height = image.height

    overlay = Image.new("RGBA", (work_width, work_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    row = 0
    start_y = -sy - text_height
    end_y = work_height + sy + text_height
    start_x = -sx - text_width - abs(int(offset_x))
    end_x = work_width + sx + text_width + abs(int(offset_x))
    for yy in range(start_y, end_y, sy):
        shift = int(offset_x) if row % 2 else 0
        # Make yy represent the visual top of the glyphs rather than Pillow's
        # baseline-relative origin, keeping row spacing stable across fonts.
        draw_y = yy - text_bbox[1]
        for xx in range(start_x, end_x, sx):
            draw.text((xx + shift - text_bbox[0], draw_y), str(text), font=font, fill=(*rgb, alpha))
        row += 1

    if abs(angle) > 1e-6:
        overlay = overlay.rotate(-angle, resample=Image.Resampling.BICUBIC, expand=False)

    left = max(0, (overlay.width - image.width) // 2)
    top = max(0, (overlay.height - image.height) // 2)
    overlay = overlay.crop((left, top, left + image.width, top + image.height))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

def _text_mask(
    image: Image.Image,
    text: str,
    x: float,
    y: float,
    size: int,
    font_name: str,
    mode: str,
    background_mode: str,
    background: str,
    threshold: float,
    feather: float,
    invert: bool,
    rotation: float,
) -> Image.Image:
    font = _load_text_font(font_name, size)
    temp = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(temp)
    bbox = draw.multiline_textbbox((0, 0), str(text), font=font, align="center")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    px = round(image.width * max(0.0, min(100.0, float(x))) / 100.0)
    py = round(image.height * max(0.0, min(100.0, float(y))) / 100.0)
    draw.multiline_text((px - tw / 2, py - th / 2 - bbox[1]), str(text), font=font, fill=255, align="center")
    if abs(float(rotation)) > 1e-6:
        temp = temp.rotate(-float(rotation), resample=Image.Resampling.BICUBIC, expand=False)
    threshold_value = max(0.0, min(1.0, float(threshold)))
    if threshold_value > 0:
        cutoff = round(threshold_value * 255)
        temp = temp.point(lambda value: 255 if value >= cutoff else 0)
    if feather > 0:
        temp = temp.filter(ImageFilter.GaussianBlur(radius=max(0.0, float(feather))))
    if invert:
        temp = ImageOps.invert(temp)
    mask = temp if str(mode) == "Keep Inside" else ImageOps.invert(temp)

    foreground = image.convert("RGBA")
    if str(background_mode) == "Transparent":
        bg = Image.new("RGBA", image.size, (0, 0, 0, 0))
    else:
        bg = Image.new("RGBA", image.size, (*hex_to_rgb(background), 255))
    return Image.composite(foreground, bg, mask)


def _wave_jitter_text(image: Image.Image, text: str, x: float, y: float, size: int, color: str, font_name: str, amplitude: float, wavelength: float, jitter: float, speed: float, seed: int, frame_time: float) -> Image.Image:
    img = image.convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    font = _load_text_font(font_name, size)
    value = str(text)
    widths = [float(draw.textlength(ch, font=font)) for ch in value]
    total = sum(widths)
    start_x = image.width * max(0.0, min(100.0, float(x))) / 100.0 - total / 2
    center_y = image.height * max(0.0, min(100.0, float(y))) / 100.0
    rng = np.random.default_rng(int(seed))
    jit = max(0.0, float(jitter))
    amp = max(0.0, float(amplitude))
    wave = max(1.0, float(wavelength))
    phase = float(frame_time) * max(0.0, float(speed)) * math.tau
    cursor = start_x
    fill = hex_to_rgb(color)
    for index, (ch, width) in enumerate(zip(value, widths, strict=False)):
        jx = float(rng.uniform(-jit, jit)) if jit else 0.0
        jy = float(rng.uniform(-jit, jit)) if jit else 0.0
        wy = math.sin((index / wave) * math.tau + phase) * amp
        bbox = draw.textbbox((0, 0), ch or " ", font=font)
        th = bbox[3] - bbox[1]
        draw.text((round(cursor + jx), round(center_y - th / 2 + wy + jy - bbox[1])), ch, font=font, fill=fill)
        cursor += width
    return img


def _typewriter_text(
    image: Image.Image,
    text: str,
    x: float,
    y: float,
    size: int,
    color: str,
    font_name: str,
    progress: float,
    reveal_mode: str,
    cursor: bool,
    cursor_char: str,
    cursor_blink: bool,
    cursor_blink_speed: float,
    frame_time: float,
) -> Image.Image:
    value = str(text)
    amount = max(0.0, min(100.0, float(progress))) / 100.0
    mode = str(reveal_mode)
    if mode == "Words":
        import re
        parts = re.findall(r"\S+\s*", value)
        count = max(0, min(len(parts), round(len(parts) * amount)))
        shown = "".join(parts[:count])
        complete = count >= len(parts)
    elif mode == "Lines":
        parts = value.splitlines(keepends=True)
        if not parts:
            parts = [value]
        count = max(0, min(len(parts), round(len(parts) * amount)))
        shown = "".join(parts[:count])
        complete = count >= len(parts)
    else:
        count = max(0, min(len(value), round(len(value) * amount)))
        shown = value[:count]
        complete = count >= len(value)

    cursor_visible = bool(cursor) and not complete
    if cursor_visible and cursor_blink:
        speed = max(0.1, float(cursor_blink_speed))
        cursor_visible = int(math.floor(float(frame_time) * speed * 2.0)) % 2 == 0
    if cursor_visible:
        shown += (str(cursor_char) or "_")[:1]
    layer = _render_text_block(
        shown,
        size=size,
        color=color,
        font_name=font_name,
        max_width=max(16, round(image.width * 0.9)),
        alignment="Center",
    )
    return _paste_centered_rgba(image, layer, x, y)


def _text_glitch(
    image: Image.Image,
    text: str,
    x: float,
    y: float,
    size: int,
    color: str,
    font_name: str,
    rgb_offset: int,
    slice_shift: int,
    slice_height: int,
    vertical_jitter: int,
    dropout: float,
    opacity: float,
    temporal: bool,
    seed: int,
    frame_index: int,
) -> Image.Image:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = _load_text_font(font_name, size)
    bbox = draw.textbbox((0, 0), str(text), font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    px = round(image.width * max(0.0, min(100.0, float(x))) / 100.0)
    py = round(image.height * max(0.0, min(100.0, float(y))) / 100.0)
    pos = (round(px - tw / 2), round(py - th / 2 - bbox[1]))
    draw.text(pos, str(text), font=font, fill=(*hex_to_rgb(color), 255))
    arr = np.asarray(layer, dtype=np.uint8).copy()
    offset = max(0, int(rgb_offset))
    if offset:
        alpha = arr[..., 3]
        red_alpha = np.roll(alpha, offset, axis=1)
        blue_alpha = np.roll(alpha, -offset, axis=1)
        rgb = np.zeros_like(arr)
        rgb[..., 0] = np.roll(arr[..., 0], offset, axis=1)
        rgb[..., 1] = arr[..., 1]
        rgb[..., 2] = np.roll(arr[..., 2], -offset, axis=1)
        rgb[..., 3] = np.maximum.reduce([red_alpha, alpha, blue_alpha])
        arr = rgb

    effective_seed = int(seed) + (int(frame_index) * 7919 if temporal else 0)
    rng = np.random.default_rng(effective_seed)
    shift = max(0, int(slice_shift))
    band = max(1, int(slice_height))
    vjit = max(0, int(vertical_jitter))
    drop = max(0.0, min(1.0, float(dropout)))
    top = max(0, pos[1] - band)
    bottom = min(image.height, pos[1] + th + band)
    original = arr.copy()
    for yy in range(top, bottom, band):
        y2 = min(image.height, yy + band)
        band_pixels = original[yy:y2].copy()
        if drop > 0 and float(rng.random()) < drop:
            arr[yy:y2] = 0
            continue
        dx = int(rng.integers(-shift, shift + 1)) if shift else 0
        dy = int(rng.integers(-vjit, vjit + 1)) if vjit else 0
        shifted = np.roll(band_pixels, dx, axis=1)
        target_y = max(0, min(image.height - (y2 - yy), yy + dy))
        arr[yy:y2] = 0
        arr[target_y:target_y + (y2 - yy)] = np.maximum(
            arr[target_y:target_y + (y2 - yy)], shifted
        )

    alpha_scale = max(0.0, min(1.0, float(opacity)))
    if alpha_scale < 1.0:
        arr[..., 3] = np.clip(arr[..., 3].astype(np.float32) * alpha_scale, 0, 255).astype(np.uint8)
    glitched = Image.fromarray(arr, "RGBA")
    return Image.alpha_composite(image.convert("RGBA"), glitched)


def _text_overlay(image: Image.Image, text: str, x: float, y: float, size: int, color: str, outline: int, shadow: int) -> Image.Image:
    img = image.convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    size = max(6, int(size))
    try:
        font = ImageFont.load_default(size=size)
    except TypeError:
        font = ImageFont.load_default()
    fill = hex_to_rgb(color)
    px = round(img.width * max(0.0, min(100.0, x)) / 100.0)
    py = round(img.height * max(0.0, min(100.0, y)) / 100.0)
    bbox = draw.multiline_textbbox((0, 0), str(text), font=font, align="center", stroke_width=max(0, int(outline)))
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = (px - tw // 2, py - th // 2)
    if shadow > 0:
        draw.multiline_text((pos[0] + shadow, pos[1] + shadow), str(text), font=font, fill=(0, 0, 0), align="center", stroke_width=max(0, int(outline)), stroke_fill=(0, 0, 0))
    draw.multiline_text(pos, str(text), font=font, fill=fill, align="center", stroke_width=max(0, int(outline)), stroke_fill=(0, 0, 0))
    return img


def effect_stack_output_size(size: tuple[int, int], stack: list[dict[str, Any]]) -> tuple[int, int]:
    """Return image dimensions after size-changing processing layers."""
    width, height = max(1, int(size[0])), max(1, int(size[1]))
    for step in normalize_effect_stack(stack):
        if not step.get("enabled", True) or step.get("kind") != "Pixel Aspect Ratio":
            continue
        params = step.get("params", {})
        x = max(0.25, min(4.0, float(params.get("x", 1.0))))
        y = max(0.25, min(4.0, float(params.get("y", 1.0))))
        width = max(1, round(width * x / y))
    return width, height


def apply_effect_stack(
    image: Image.Image,
    stack: list[dict[str, Any]],
    palette: list[str],
    *,
    frame_time: float = 0.0,
    frame_index: int = 0,
) -> Image.Image:
    img = image if image.mode == "RGB" else image.convert("RGB")
    palette_np = palette_array(palette)

    for step in normalize_effect_stack(stack):
        if not step.get("enabled", True):
            continue
        kind = step["kind"]
        p = step["params"]
        alpha_before = img.getchannel("A") if "A" in img.getbands() else None
        if alpha_before is not None:
            img = img.convert("RGB")

        if kind == "Adjustments":
            brightness = int(p.get("brightness", 0)); contrast = int(p.get("contrast", 0)); saturation = int(p.get("saturation", 0)); gamma = float(p.get("gamma", 1.0))
            if brightness: img = ImageEnhance.Brightness(img).enhance(max(0.0, 1.0 + brightness / 100.0))
            if contrast: img = ImageEnhance.Contrast(img).enhance(max(0.0, 1.0 + contrast / 100.0))
            if saturation: img = ImageEnhance.Color(img).enhance(max(0.0, 1.0 + saturation / 100.0))
            if abs(gamma - 1.0) > 1e-6:
                inv_gamma = 1.0 / max(0.1, gamma)
                img = img.point([round(255 * ((i / 255) ** inv_gamma)) for i in range(256)] * 3)
        elif kind == "Levels": img = _levels(img, int(p["black_point"]), int(p["white_point"]), float(p["gamma"]))
        elif kind == "Local Contrast": img = _local_contrast(img, int(p["amount"]), float(p["radius"]), int(p["threshold"]))
        elif kind == "Hue Rotate": img = _hue_rotate(img, int(p["degrees"]))
        elif kind == "Grayscale": img = ImageOps.grayscale(img).convert("RGB")
        elif kind == "Invert": img = ImageOps.invert(img.convert("RGB"))
        elif kind == "Gaussian Blur":
            radius = float(p["radius"])
            if radius > 0: img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        elif kind == "Median Denoise": img = img.filter(ImageFilter.MedianFilter(size=max(1, int(p["radius"])) * 2 + 1))
        elif kind == "Sharpen": img = ImageEnhance.Sharpness(img).enhance(float(p["amount"]))
        elif kind == "Glow": img = _glow(img, float(p["radius"]), float(p["intensity"]))
        elif kind == "Bloom": img = _bloom(img, float(p["threshold"]), float(p["soft_knee"]), float(p["radius"]), float(p["intensity"]), str(p["blend"]))
        elif kind == "JPEG Compression": img = _jpeg_compression(img, int(p["quality"]))
        elif kind == "Chromatic Shift": img = _chromatic_shift(img, int(p["amount"]))
        elif kind == "RGB Split": img = _rgb_split(img, int(p["x"]), int(p["y"]))
        elif kind == "Posterize": img = _posterize(img, int(p["levels"]))
        elif kind == "Scanlines": img = _scanlines(img, int(p["spacing"]), float(p["strength"]))
        elif kind == "Interlace": img = _interlace(img, int(p["offset"]), float(p["darken"]))
        elif kind == "Noise": img = _noise(img, float(p["amount"]), _seed(p, frame_index))
        elif kind == "Temporal Flicker": img = _flicker(img, float(p["amount"]), float(p["speed"]), frame_time)
        elif kind == "Temporal Pattern": img = _temporal_pattern(img, str(p["pattern"]), float(p["amount"]), float(p["speed"]), float(p["scale"]), float(p["phase"]), frame_time, int(p["seed"]))
        elif kind == "Pixel Aspect Ratio": img = _pixel_aspect_ratio(img, float(p["x"]), float(p["y"]), str(p["resample"]))
        elif kind == "Pixelate": img = _pixelate(img, int(round(float(p["size"]))))
        elif kind == "Pixel Sort": img = _pixel_sort(img, float(p["threshold"]), str(p["direction"]), bool(p["reverse"]))
        elif kind == "Screen Melt": img = _screen_melt(img, int(p["amount"]), int(p["column_width"]), _seed(p, frame_index))
        elif kind == "Block Shuffle": img = _block_shuffle(img, int(p["block"]), float(p["amount"]), _seed(p, frame_index))
        elif kind == "Pixel Scatter": img = _pixel_scatter(img, int(p["distance"]), float(p["density"]), _seed(p, frame_index))
        elif kind == "Data Shift": img = _data_shift(img, int(p["amount"]), int(p["band_height"]), _seed(p, frame_index))
        elif kind == "Row Shift": img = _periodic_shift(img, int(p["amount"]), int(p["period"]), 0)
        elif kind == "Column Shift": img = _periodic_shift(img, int(p["amount"]), int(p["period"]), 1)
        elif kind == "Cellular Automata": img = _cellular_automata(img, float(p["threshold"]), int(p["steps"]), float(p["blend"]))
        elif kind == "Databend": img = _databend(img, int(p["quality"]), int(p["shift"]), _seed(p, frame_index))
        elif kind == "Channel Swap": img = _channel_swap(img, str(p["order"]))
        elif kind == "Pixel Material": img = _pixel_material(img, str(p["style"]), int(p["cell_size"]), int(p["gap"]), str(p["background"]), str(p["sprite_path"]))
        elif kind == "Text Overlay": img = _text_overlay(img, str(p["text"]), float(p["x"]), float(p["y"]), int(p["size"]), str(p["color"]), int(p["outline"]), int(p["shadow"]))
        elif kind == "ASCII / Glyph":
            img = _ascii_glyph(
                img,
                str(p["character_set"]),
                str(p["custom_chars"]),
                bool(p.get("auto_density", True)),
                int(p["cell_size"]),
                int(p.get("spacing_x", 0)),
                int(p.get("spacing_y", 0)),
                int(p["depth"]),
                int(p["offset"]),
                bool(p["invert"]),
                str(p["color_mode"]),
                str(p["foreground"]),
                str(p.get("background_mode", "Solid Colour")),
                str(p["background"]),
                str(p["font"]),
                float(p["font_scale"]),
                palette_np,
                inject_chars=str(p.get("inject_chars", "")),
                mapping=str(p.get("mapping", "Density")),
                structure=float(p.get("structure", 75.0)),
                density_influence=float(p.get("density_influence", 25.0)),
                local_detail=float(p.get("local_detail", 35.0)),
                auto_cell_aspect=bool(p.get("auto_cell_aspect", True)),
                supersampling=str(p.get("supersampling", "4×")),
                color_sampling=str(p.get("color_sampling", "Glyph Weighted")),
            )
        elif kind == "Pixel Text": img = _pixel_text(img, str(p["text"]), float(p["x"]), float(p["y"]), int(p["size"]), str(p["color"]), str(p["font"]), str(p["alignment"]), float(p["wrap_width"]), int(p["letter_spacing"]), int(p["line_spacing"]), float(p["rotation"]), int(p["outline"]), int(p["shadow"]))
        elif kind == "Text Pattern": img = _text_pattern(img, str(p["text"]), int(p["size"]), str(p["color"]), str(p["font"]), int(p["spacing_x"]), int(p["spacing_y"]), int(p["offset_x"]), float(p["rotation"]), float(p["opacity"]))
        elif kind == "Text Mask":
            img = _text_mask(
                img, str(p["text"]), float(p["x"]), float(p["y"]), int(p["size"]), str(p["font"]), str(p["mode"]),
                str(p.get("background_mode", "Solid Colour")), str(p["background"]), float(p.get("threshold", 0.0)),
                float(p.get("feather", 0.0)), bool(p.get("invert", False)), float(p["rotation"]),
            )
        elif kind == "Wave / Jitter Text": img = _wave_jitter_text(img, str(p["text"]), float(p["x"]), float(p["y"]), int(p["size"]), str(p["color"]), str(p["font"]), float(p["amplitude"]), float(p["wavelength"]), float(p["jitter"]), float(p["speed"]), int(p["seed"]), frame_time)
        elif kind == "Typewriter Text":
            img = _typewriter_text(
                img, str(p["text"]), float(p["x"]), float(p["y"]), int(p["size"]), str(p["color"]), str(p["font"]),
                float(p["progress"]), str(p.get("reveal_mode", "Characters")), bool(p["cursor"]), str(p["cursor_char"]),
                bool(p.get("cursor_blink", True)), float(p.get("cursor_blink_speed", 2.0)), frame_time,
            )
        elif kind == "Text Glitch":
            img = _text_glitch(
                img, str(p["text"]), float(p["x"]), float(p["y"]), int(p["size"]), str(p["color"]), str(p["font"]),
                int(p["rgb_offset"]), int(p["slice_shift"]), int(p["slice_height"]), int(p.get("vertical_jitter", 0)),
                float(p.get("dropout", 0.0)), float(p.get("opacity", 1.0)), bool(p.get("temporal", False)), int(p["seed"]), frame_index,
            )
        elif kind == "Dither Glow":
            img = _dither_glow(
                img,
                float(p.get("threshold", 0.72)),
                float(p.get("softness", 0.18)),
                float(p.get("radius", 5.0)),
                int(p.get("spread", 1)),
                float(p.get("intensity", 1.25)),
                str(p.get("blend", "Screen")),
                str(p.get("glow_color_mode", "Source")),
                str(p.get("glow_color", "#FFFFFF")),
                bool(p.get("preserve_core", True)),
            )
        elif kind == "Dither":
            mix = max(0.0, min(1.0, float(p.get("mix", 1.0))))
            if mix <= 0.0:
                continue
            before = img.convert("RGB")
            arr = np.asarray(before, dtype=np.float32)
            result = apply_dither(
                arr,
                palette_np,
                str(p["algorithm"]),
                strength=float(p["strength"]),
                serpentine=bool(p["serpentine"]),
                threshold=float(p["threshold"]),
                color_mix_pattern=str(p.get("color_mix_pattern", "Checker")),
                color_mix_distance=str(p.get("color_mix_distance", "OKLab")),
                color_mix_phase=int(p.get("color_mix_phase", 0)),
            )
            dithered = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), "RGB")
            img = dithered if mix >= 1.0 else Image.blend(before, dithered, mix)

        if alpha_before is not None:
            alpha = alpha_before
            if alpha.size != img.size:
                alpha = alpha.resize(img.size, Image.Resampling.NEAREST)
            if "A" in img.getbands():
                generated_alpha = img.getchannel("A")
                alpha = ImageChops.multiply(alpha, generated_alpha)
            rgba = img.convert("RGBA")
            rgba.putalpha(alpha)
            img = rgba
    return img
