# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from functools import lru_cache
import math
import os
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from .color_utils import hex_to_rgb
from .dither import apply_dither, beehive_dither, polygon_dither, pop_tone_dither
from .hardware import apply_hardware_limits_layer
from .print_lab import render_print_lab
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
from .layer_groups import canonicalize_layer_groups
from .pixel_cleanup import cleanup_pixel_art
from .temporal import TemporalEffectState


class ProcessingCancelled(RuntimeError):
    """Raised when an interactive render is superseded by newer work."""


def _layer_composite_is_passthrough(step: dict[str, Any]) -> bool:
    """Return whether layer compositing can return the effect image directly."""
    opacity = max(0.0, min(1.0, float(step.get("opacity", 1.0) or 0.0)))
    mode = str(step.get("blend_mode", "Normal") or "Normal")
    mask = step.get("mask") if isinstance(step.get("mask"), dict) else {"type": "None"}
    default_mask = (
        str(mask.get("type", "None") or "None") == "None"
        and not bool(mask.get("invert", False))
        and float(mask.get("strength", 1.0) or 0.0) >= 0.999999
    )
    return opacity >= 0.999999 and mode == "Normal" and default_mask

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


def _nearest_palette_labels(image: np.ndarray, palette: np.ndarray, chunk_pixels: int = 32768) -> np.ndarray:
    """Return nearest-palette indices using bounded-memory RGB distance chunks."""
    source = np.asarray(image, dtype=np.float32)
    pal = np.asarray(palette, dtype=np.float32)
    if source.ndim != 3 or source.shape[2] != 3:
        raise ValueError("image must have shape (H, W, 3)")
    if pal.ndim != 2 or pal.shape[1] != 3 or len(pal) == 0:
        raise ValueError("palette must have shape (N, 3) with N >= 1")
    pixels = source.reshape(-1, 3)
    pal_sq = np.sum(pal * pal, axis=1)
    labels = np.empty(len(pixels), dtype=np.intp)
    step = max(1024, int(chunk_pixels))
    for start in range(0, len(pixels), step):
        end = min(len(pixels), start + step)
        chunk = pixels[start:end]
        distances = (
            np.sum(chunk * chunk, axis=1, keepdims=True)
            + pal_sq[None, :]
            - 2.0 * (chunk @ pal.T)
        )
        labels[start:end] = np.argmin(distances, axis=1)
    return labels.reshape(source.shape[:2])


def _apply_dither_edge_treatment(
    result: np.ndarray,
    palette: np.ndarray,
    *,
    bleed: float = 0.0,
    rounding: float = 0.0,
) -> np.ndarray:
    """Apply palette-safe morphology to a completed dither result.

    Positive bleed grows darker/ink-like palette entries into neighbouring
    lighter pixels; negative bleed contracts dark regions by growing lighter
    neighbours. Rounding is majority morphology on palette indices, so no
    intermediate colours are introduced.
    """
    pal = np.asarray(palette, dtype=np.float32)
    labels = _nearest_palette_labels(result, pal)
    if len(pal) > 256:
        # RasterMint palettes are currently capped at 256 colours, but keep a
        # defensive no-overflow path if that limit changes in the future.
        return pal[labels]

    bleed_px = int(round(float(bleed)))
    if bleed_px:
        luminance = pal @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        rank_to_label = np.argsort(luminance, kind="stable")
        label_to_rank = np.empty(len(rank_to_label), dtype=np.uint8)
        label_to_rank[rank_to_label] = np.arange(len(rank_to_label), dtype=np.uint8)
        ranked = label_to_rank[labels]
        ranked_image = Image.fromarray(ranked, "L")
        size = max(3, abs(bleed_px) * 2 + 1)
        filtered = ranked_image.filter(
            ImageFilter.MinFilter(size=size) if bleed_px > 0 else ImageFilter.MaxFilter(size=size)
        )
        ranks = np.asarray(filtered, dtype=np.uint8)
        labels = rank_to_label[ranks]

    rounding_amount = max(0.0, min(100.0, float(rounding)))
    if rounding_amount > 0.0 and len(pal) > 1:
        mode_image = Image.fromarray(labels.astype(np.uint8), "L")
        passes = max(1, min(4, int(math.ceil(rounding_amount / 25.0))))
        kernel = 5 if rounding_amount >= 75.0 else 3
        for _ in range(passes):
            mode_image = mode_image.filter(ImageFilter.ModeFilter(size=kernel))
        labels = np.asarray(mode_image, dtype=np.uint8).astype(np.intp)

    return pal[labels]


def _tonal_map(
    image: Image.Image,
    mode: str,
    shadow_color: str,
    midtone_color: str,
    highlight_color: str,
    background_color: str,
    shadow_point: float,
    midpoint: float,
    highlight_point: float,
    blend_softness: float,
) -> Image.Image:
    """Map source luminance through configurable tonal colour anchors."""
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    luminance = (
        arr[..., 0] * 0.2126
        + arr[..., 1] * 0.7152
        + arr[..., 2] * 0.0722
    ) / 255.0 * 100.0

    shadow = np.asarray(hex_to_rgb(shadow_color), dtype=np.float32)
    midtone = np.asarray(hex_to_rgb(midtone_color), dtype=np.float32)
    highlight = np.asarray(hex_to_rgb(highlight_color), dtype=np.float32)
    background = np.asarray(hex_to_rgb(background_color), dtype=np.float32)

    sp = max(0.0, min(100.0, float(shadow_point)))
    mp = max(sp, min(100.0, float(midpoint)))
    hp = max(mp, min(100.0, float(highlight_point)))
    mode_name = str(mode or "Tritone")

    if mode_name == "Mono":
        points = [0.0, hp]
        colors = [background, highlight]
    elif mode_name == "Duotone":
        points = [sp, hp]
        colors = [shadow, highlight]
    elif mode_name == "Gradient":
        points = [0.0, sp, mp, hp]
        colors = [background, shadow, midtone, highlight]
    else:  # Tritone
        points = [sp, mp, hp]
        colors = [shadow, midtone, highlight]

    softness = max(0.0, min(1.0, float(blend_softness) / 100.0))
    out = np.empty_like(arr, dtype=np.float32)
    out[...] = colors[0]
    out[luminance >= points[-1]] = colors[-1]

    for idx in range(len(points) - 1):
        lo = float(points[idx])
        hi = float(points[idx + 1])
        left = colors[idx]
        right = colors[idx + 1]
        if hi <= lo + 1e-9:
            mask = luminance >= hi
            out[mask] = right
            continue
        if idx == len(points) - 2:
            mask = (luminance >= lo) & (luminance <= hi)
        else:
            mask = (luminance >= lo) & (luminance < hi)
        if not np.any(mask):
            continue
        t = np.clip((luminance[mask] - lo) / (hi - lo), 0.0, 1.0)
        smooth_t = t * t * (3.0 - 2.0 * t)
        hard_t = (t >= 0.5).astype(np.float32)
        blend_t = hard_t * (1.0 - softness) + smooth_t * softness
        out[mask] = left[None, :] * (1.0 - blend_t[:, None]) + right[None, :] * blend_t[:, None]

    return Image.fromarray(np.rint(np.clip(out, 0, 255)).astype(np.uint8), "RGB")


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


def _animated_rng(seed: int, frame_index: int, frame_time: float, salt: int = 0) -> np.random.Generator:
    time_key = int(round(max(0.0, float(frame_time)) * 1000.0))
    mixed = (
        (int(seed) * 1000003)
        ^ (int(frame_index) * 0x9E3779B1)
        ^ (time_key * 0x85EBCA6B)
        ^ int(salt)
    ) & 0xFFFFFFFF
    return np.random.default_rng(mixed)


def _shift_with_edge(arr: np.ndarray, x: int = 0, y: int = 0) -> np.ndarray:
    x = int(x)
    y = int(y)
    out = np.array(arr, copy=True)
    h, w = out.shape[:2]
    if w <= 0 or h <= 0:
        return out

    if x != 0:
        shifted = np.empty_like(out)
        if x > 0:
            dx = min(x, w)
            shifted[:, :dx] = out[:, :1]
            shifted[:, dx:] = out[:, : w - dx]
        else:
            dx = min(-x, w)
            shifted[:, w - dx :] = out[:, -1:]
            shifted[:, : w - dx] = out[:, dx:]
        out = shifted

    if y != 0:
        shifted = np.empty_like(out)
        if y > 0:
            dy = min(y, h)
            shifted[:dy, :] = out[:1, :]
            shifted[dy:, :] = out[: h - dy, :]
        else:
            dy = min(-y, h)
            shifted[h - dy :, :] = out[-1:, :]
            shifted[: h - dy, :] = out[dy:, :]
        out = shifted

    return out


def _horizontal_blur_channel(channel: np.ndarray, radius: float) -> np.ndarray:
    radius = max(0.0, float(radius))
    if radius <= 1e-9:
        return np.asarray(channel, dtype=np.float32)

    whole = int(math.floor(radius))
    frac = float(radius - whole)
    offsets = range(-whole, whole + 1)
    weights = [float(whole + 1 - abs(offset)) for offset in offsets]
    if frac > 1e-6:
        offsets = list(offsets) + [whole + 1, -(whole + 1)]
        edge_weight = max(0.0, float(weights[-1]) * frac)
        weights += [edge_weight, edge_weight]
    total = max(1e-9, float(sum(weights)))

    padded = np.pad(np.asarray(channel, dtype=np.float32), ((0, 0), (whole + 1, whole + 1)), mode="edge")
    width = channel.shape[1]
    out = np.zeros_like(channel, dtype=np.float32)
    center = whole + 1
    for offset, weight in zip(offsets, weights, strict=False):
        start = center + int(offset)
        out += padded[:, start : start + width] * float(weight)
    return out / total


def _chroma_bleed(image: Image.Image, bleed: float, delay: int, strength: float) -> Image.Image:
    bleed = max(0.0, float(bleed))
    delay = int(delay)
    strength = max(0.0, min(1.0, float(strength)))
    if bleed <= 1e-9 and delay == 0 or strength <= 1e-9:
        return image

    arr = np.asarray(image.convert("YCbCr"), dtype=np.float32)
    cb = arr[..., 1]
    cr = arr[..., 2]

    cb_shifted = _shift_with_edge(_horizontal_blur_channel(cb, bleed), delay, 0)
    cr_shifted = _shift_with_edge(_horizontal_blur_channel(cr, bleed * 1.2), delay + (1 if delay >= 0 else -1), 0)
    arr[..., 1] = cb * (1.0 - strength) + cb_shifted * strength
    arr[..., 2] = cr * (1.0 - strength) + cr_shifted * strength

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "YCbCr").convert("RGB")


def _tracking_error(
    image: Image.Image,
    amount: int,
    band_height: int,
    instability: float,
    speed: float,
    seed: int,
    frame_time: float,
    frame_index: int,
) -> Image.Image:
    amount = max(0, int(amount))
    band_height = max(1, int(band_height))
    instability = max(0.0, min(1.0, float(instability)))
    speed = max(0.0, float(speed))
    if amount <= 0:
        return image

    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    phase = 2.0 * np.pi * speed * max(0.0, float(frame_time))
    rng = _animated_rng(seed, frame_index, frame_time, salt=101)

    for band_index, y in enumerate(range(0, arr.shape[0], band_height)):
        local_h = min(band_height, arr.shape[0] - y)
        smooth = math.sin(phase + band_index * 0.83 + seed * 0.11)
        noise = (float(rng.random()) * 2.0 - 1.0) * instability
        spike = 0.0
        if rng.random() < 0.05 + 0.25 * instability:
            spike = (float(rng.random()) * 2.0 - 1.0) * (0.25 + 0.75 * instability)
        shift = int(round(amount * max(-1.0, min(1.0, 0.65 * smooth + 0.35 * noise + spike))))
        if shift:
            out[y : y + local_h] = _shift_with_edge(arr[y : y + local_h], shift, 0)

    return Image.fromarray(out, "RGB")


def _tape_dropout(
    image: Image.Image,
    amount: float,
    length: int,
    thickness: int,
    strength: float,
    seed: int,
    frame_time: float,
    frame_index: int,
) -> Image.Image:
    amount = max(0.0, min(1.0, float(amount)))
    length = max(2, int(length))
    thickness = max(1, int(thickness))
    strength = max(0.0, min(1.0, float(strength)))
    if amount <= 1e-9 or strength <= 1e-9:
        return image

    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    out = arr.copy()
    h, w = out.shape[:2]
    rng = _animated_rng(seed, frame_index, frame_time, salt=211)
    count = max(1, int(round(amount * max(1.0, h / max(1, thickness)) * 0.6)))
    min_length = max(2, int(round(length * 0.2)))

    for _ in range(count):
        streak_h = int(rng.integers(1, thickness + 1))
        span = int(rng.integers(min_length, length + 1))
        if span >= w:
            x0 = 0
            span = w
        else:
            x0 = int(rng.integers(0, w - span + 1))
        y0 = int(rng.integers(0, max(1, h - streak_h + 1)))
        opacity = strength * (0.35 + 0.65 * float(rng.random()))
        region = out[y0 : y0 + streak_h, x0 : x0 + span]

        if rng.random() < 0.3:
            region[...] = region * (1.0 - opacity * 0.25) + 255.0 * (opacity * 0.9)
        else:
            luminance = (
                0.2126 * region[..., 0]
                + 0.7152 * region[..., 1]
                + 0.0722 * region[..., 2]
            )[..., None]
            region[...] = np.clip(
                (region * (1.0 - opacity) + luminance * (opacity * 0.55)) * (1.0 - opacity * 0.6),
                0.0,
                255.0,
            )

        if span > 6 and rng.random() < 0.45:
            speckle_count = max(1, span // 12)
            xs = rng.integers(x0, x0 + span, size=speckle_count)
            ys = rng.integers(y0, y0 + streak_h, size=speckle_count)
            out[ys, xs] = 255.0

    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _temporal_jitter(
    image: Image.Image,
    x: float,
    y: float,
    speed: float,
    seed: int,
    frame_time: float,
    frame_index: int,
) -> Image.Image:
    x = max(0.0, float(x))
    y = max(0.0, float(y))
    speed = max(0.0, float(speed))
    if x <= 1e-9 and y <= 1e-9:
        return image

    theta = 2.0 * np.pi * speed * max(0.0, float(frame_time))
    rng = _animated_rng(seed, frame_index, frame_time, salt=307)
    dx = x * (0.75 * math.sin(theta + seed * 0.17) + 0.25 * (float(rng.random()) * 2.0 - 1.0))
    dy = y * (0.75 * math.sin(theta * 0.87 + seed * 0.31) + 0.25 * (float(rng.random()) * 2.0 - 1.0))
    shifted = _shift_with_edge(np.asarray(image.convert("RGB"), dtype=np.uint8), int(round(dx)), int(round(dy)))
    return Image.fromarray(shifted, "RGB")


def _head_switching_noise(
    image: Image.Image,
    height: int,
    shift: int,
    noise: float,
    strength: float,
    seed: int,
    frame_time: float,
    frame_index: int,
) -> Image.Image:
    height = max(1, int(height))
    shift = max(0, int(shift))
    noise = max(0.0, min(1.0, float(noise)))
    strength = max(0.0, min(1.0, float(strength)))
    if shift <= 0 and noise <= 1e-9:
        return image

    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    out = arr.copy()
    h, w = out.shape[:2]
    band = min(h, height)
    start = h - band
    phase = 2.0 * np.pi * 6.0 * max(0.0, float(frame_time))
    rng = _animated_rng(seed, frame_index, frame_time, salt=401)

    for local_y in range(band):
        y_index = start + local_y
        weight = (local_y + 1) / max(1, band)
        wave = math.sin(phase + local_y * 0.55 + seed * 0.07)
        jitter = (float(rng.random()) * 2.0 - 1.0) * noise
        row_shift = int(round(shift * weight * max(-1.0, min(1.0, 0.7 * wave + 0.3 * jitter))))
        if row_shift:
            out[y_index : y_index + 1] = _shift_with_edge(arr[y_index : y_index + 1], row_shift, 0)

    if noise > 1e-9:
        band_arr = out[start:].copy()
        vertical_weight = np.linspace(0.45, 1.0, band, dtype=np.float32)[:, None, None]
        grain = rng.normal(0.0, 255.0 * 0.18 * noise, size=band_arr.shape).astype(np.float32)
        spark_mask = (rng.random((band, w, 1)) < (0.003 + 0.02 * noise)).astype(np.float32)
        spark = spark_mask * rng.integers(160, 256, size=(band, w, 1), dtype=np.int16).astype(np.float32)
        band_arr = band_arr * (1.0 - 0.12 * strength * vertical_weight) + grain * vertical_weight * (0.35 + 0.65 * strength)
        band_arr = np.maximum(band_arr, spark * vertical_weight)
        out[start:] = np.clip(band_arr, 0.0, 255.0)

    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _rgb_convergence(
    image: Image.Image,
    red_x: float,
    red_y: float,
    blue_x: float,
    blue_y: float,
    strength: float,
) -> Image.Image:
    strength = max(0.0, min(1.0, float(strength)))
    if strength <= 1e-9:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    out = arr.copy()
    red = _shift_with_edge(arr[..., 0], int(round(red_x)), int(round(red_y)))
    blue = _shift_with_edge(arr[..., 2], int(round(blue_x)), int(round(blue_y)))
    out[..., 0] = arr[..., 0] * (1.0 - strength) + red * strength
    out[..., 2] = arr[..., 2] * (1.0 - strength) + blue * strength
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _crt_mask(image: Image.Image, mask_type: str, scale: int, strength: float, brightness: float) -> Image.Image:
    scale = max(1, int(scale))
    strength = max(0.0, min(1.0, float(strength)))
    brightness = max(0.0, min(1.0, float(brightness)))
    if strength <= 1e-9:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cell_x = (xx // scale).astype(np.int32)
    cell_y = (yy // scale).astype(np.int32)
    mask = np.ones((h, w, 3), dtype=np.float32)

    kind = str(mask_type)
    if kind == "Shadow Mask":
        # Triad dots on alternating rows approximate a delta-gun shadow mask.
        phase = (cell_x + (cell_y & 1)) % 3
        for channel in range(3):
            active = phase == channel
            mask[..., channel] = np.where(active, 1.0, 0.42)
        row_gate = np.where((yy % max(2, scale * 2)) < scale, 1.0, 0.82).astype(np.float32)
        mask *= row_gate[..., None]
    elif kind == "Slot Mask":
        # Vertical RGB slots staggered every other row pair.
        phase = (cell_x + ((cell_y // 2) & 1)) % 3
        for channel in range(3):
            active = phase == channel
            mask[..., channel] = np.where(active, 1.0, 0.36)
        gap = (yy % max(2, scale * 3)) >= max(1, scale * 2)
        mask[gap] *= 0.68
    else:  # Aperture Grille
        phase = cell_x % 3
        for channel in range(3):
            active = phase == channel
            mask[..., channel] = np.where(active, 1.0, 0.46)
        # Sparse horizontal damper wires keep the effect CRT-like at larger scales.
        wire_period = max(12, scale * 12)
        wire = (yy % wire_period) == 0
        mask[wire] *= 0.70

    compensated = np.clip(mask + brightness, 0.0, 1.4)
    factor = 1.0 - strength + compensated * strength
    out = np.clip(arr * factor, 0.0, 1.0)
    return Image.fromarray(np.rint(out * 255.0).astype(np.uint8), "RGB")


def _phosphor_glow(image: Image.Image, threshold: float, radius: float, intensity: float) -> Image.Image:
    threshold = max(0.0, min(1.0, float(threshold)))
    radius = max(0.0, float(radius))
    intensity = max(0.0, float(intensity))
    if radius <= 1e-9 or intensity <= 1e-9:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    lum = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    denom = max(1e-6, 1.0 - threshold)
    gate = np.clip((lum - threshold) / denom, 0.0, 1.0)[..., None]
    bright = np.clip(arr * gate, 0.0, 1.0)
    glow_img = Image.fromarray(np.rint(bright * 255.0).astype(np.uint8), "RGB").filter(
        ImageFilter.GaussianBlur(radius=radius)
    )
    glow = np.asarray(glow_img, dtype=np.float32) / 255.0
    out = 1.0 - (1.0 - arr) * (1.0 - np.clip(glow * intensity, 0.0, 1.0))
    return Image.fromarray(np.rint(np.clip(out, 0.0, 1.0) * 255.0).astype(np.uint8), "RGB")


def _beam_width(image: Image.Image, spacing: int, width: float, strength: float) -> Image.Image:
    spacing = max(2, int(spacing))
    width = max(0.1, min(1.5, float(width)))
    strength = max(0.0, min(1.0, float(strength)))
    if strength <= 1e-9:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    h = arr.shape[0]
    phase = (np.arange(h, dtype=np.float32) % spacing) / max(1.0, float(spacing - 1))
    distance = np.abs(phase - 0.5) * 2.0
    sigma = max(0.08, width * 0.55)
    beam = np.exp(-(distance * distance) / (2.0 * sigma * sigma))
    beam /= max(1e-6, float(beam.max()))
    factor = 1.0 - strength * (1.0 - beam)
    out = arr * factor[:, None, None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _horizontal_bloom(image: Image.Image, threshold: float, radius: float, intensity: float) -> Image.Image:
    threshold = max(0.0, min(1.0, float(threshold)))
    radius = max(0.0, float(radius))
    intensity = max(0.0, float(intensity))
    if radius <= 1e-9 or intensity <= 1e-9:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    lum = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    gate = np.clip((lum - threshold) / max(1e-6, 1.0 - threshold), 0.0, 1.0)
    bright = arr * gate[..., None]
    blurred = np.empty_like(bright)
    for channel in range(3):
        blurred[..., channel] = _horizontal_blur_channel(bright[..., channel], radius)
    bloom = np.clip(blurred * intensity, 0.0, 1.0)
    out = 1.0 - (1.0 - arr) * (1.0 - bloom)
    return Image.fromarray(np.rint(np.clip(out, 0.0, 1.0) * 255.0).astype(np.uint8), "RGB")


def _scanline_variation(
    image: Image.Image,
    spacing: int,
    strength: float,
    variation: float,
    speed: float,
    seed: int,
    frame_time: float,
) -> Image.Image:
    spacing = max(2, int(spacing))
    strength = max(0.0, min(1.0, float(strength)))
    variation = max(0.0, min(1.0, float(variation)))
    speed = max(0.0, float(speed))
    if strength <= 1e-9:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32).copy()
    h = arr.shape[0]
    rows = np.arange(h, dtype=np.float32)
    phase = 2.0 * np.pi * speed * max(0.0, float(frame_time)) + float(seed) * 0.173
    wave = 0.5 + 0.5 * np.sin(rows * 0.77 + phase)
    darken = strength * (1.0 - variation + variation * wave)
    active = (np.arange(h) % spacing) == 0
    factors = np.ones(h, dtype=np.float32)
    factors[active] = 1.0 - darken[active]
    arr *= factors[:, None, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _crt_auto_border_fill(image: Image.Image) -> tuple[int, int, int, int]:
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    if rgba.size == 0:
        return (0, 0, 0, 255)
    top = rgba[0, :, :]
    bottom = rgba[-1, :, :]
    left = rgba[:, 0, :]
    right = rgba[:, -1, :]
    edges = np.concatenate((top, bottom, left, right), axis=0)
    opaque = edges[edges[:, 3] > 0]
    sample = opaque if opaque.size else edges
    if sample.size == 0:
        return (0, 0, 0, 255)
    rgb = np.median(sample[:, :3], axis=0)
    alpha = 255 if opaque.size else int(np.median(sample[:, 3]))
    return tuple(int(round(v)) for v in (*rgb, alpha))


def _crt_fill_colour(image: Image.Image, border_fill: str, border_color: str) -> tuple[int, int, int, int]:
    mode = str(border_fill or "Solid Color")
    if mode == "Transparent":
        return (0, 0, 0, 0)
    if mode == "Solid Color":
        return (*hex_to_rgb(border_color), 255)
    if mode == "Auto":
        return _crt_auto_border_fill(image)
    return (0, 0, 0, 255)


def _crt_curvature(
    image: Image.Image,
    curvature: float,
    zoom: float,
    edge_fade: float,
    border_fill: str = "Solid Color",
    border_color: str = "#000000",
) -> Image.Image:
    curvature = max(0.0, min(0.5, float(curvature)))
    zoom = max(1.0, min(1.3, float(zoom)))
    edge_fade = max(0.0, min(1.0, float(edge_fade)))
    if curvature <= 1e-9 and abs(zoom - 1.0) <= 1e-9 and edge_fade <= 1e-9:
        return image

    src = image.convert("RGBA")
    w, h = src.size
    # PIL MESH keeps memory bounded while approximating a barrel-distorted CRT face.
    divisions = max(8, min(32, round(max(w, h) / 64)))
    mesh = []

    def source_point(x: float, y: float) -> tuple[float, float]:
        nx = (x / max(1.0, w - 1.0)) * 2.0 - 1.0
        ny = (y / max(1.0, h - 1.0)) * 2.0 - 1.0
        r2 = nx * nx + ny * ny
        factor = (1.0 + curvature * r2) / zoom
        sx = ((nx * factor) + 1.0) * 0.5 * (w - 1.0)
        sy = ((ny * factor) + 1.0) * 0.5 * (h - 1.0)
        return sx, sy

    for gy in range(divisions):
        y0 = round(gy * h / divisions)
        y1 = round((gy + 1) * h / divisions)
        if y1 <= y0:
            continue
        for gx in range(divisions):
            x0 = round(gx * w / divisions)
            x1 = round((gx + 1) * w / divisions)
            if x1 <= x0:
                continue
            p00 = source_point(x0, y0)
            p10 = source_point(x1, y0)
            p11 = source_point(x1, y1)
            p01 = source_point(x0, y1)
            mesh.append(((x0, y0, x1, y1), (*p00, *p01, *p11, *p10)))

    curved = src.transform(
        src.size,
        Image.Transform.MESH,
        mesh,
        resample=Image.Resampling.BILINEAR,
        fillcolor=_crt_fill_colour(image, border_fill, border_color),
    )
    if edge_fade > 1e-9:
        arr = np.asarray(curved, dtype=np.float32)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        nx = np.abs((xx / max(1.0, w - 1.0)) * 2.0 - 1.0)
        ny = np.abs((yy / max(1.0, h - 1.0)) * 2.0 - 1.0)
        edge = np.maximum(nx, ny)
        fade = np.clip((edge - 0.82) / 0.18, 0.0, 1.0) * edge_fade
        arr[..., :3] *= (1.0 - fade[..., None])
        curved = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    if str(border_fill or "Solid Color") != "Transparent" and "A" not in image.getbands():
        return curved.convert("RGB")
    return curved


def _edge_distortion(image: Image.Image, amount: float, frequency: float, falloff: float) -> Image.Image:
    amount = max(0.0, float(amount))
    frequency = max(0.1, float(frequency))
    falloff = max(0.05, min(1.0, float(falloff)))
    if amount <= 1e-9:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    h, w = arr.shape[:2]
    center = (h - 1) * 0.5
    half = max(1.0, center)
    for y in range(h):
        ny = abs((y - center) / half)
        edge_weight = np.clip((ny - (1.0 - falloff)) / falloff, 0.0, 1.0)
        if edge_weight <= 0.0:
            continue
        shift = int(round(math.sin((y / max(1.0, h)) * frequency * 2.0 * math.pi) * amount * edge_weight))
        if shift:
            out[y : y + 1] = _shift_with_edge(arr[y : y + 1], shift, 0)
    return Image.fromarray(out, "RGB")


def _vertical_sync_roll(image: Image.Image, amount: int, speed: float, softness: float, frame_time: float) -> Image.Image:
    amount = max(0, int(amount))
    speed = float(speed)
    softness = max(0.0, min(1.0, float(softness)))
    if amount <= 0 or abs(speed) <= 1e-9:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    h = arr.shape[0]
    center = ((max(0.0, float(frame_time)) * speed) % 1.0) * h
    yy = np.arange(h, dtype=np.float32)
    circular = np.minimum(np.abs(yy - center), h - np.abs(yy - center))
    width = max(1.0, h * (0.05 + softness * 0.2))
    weight = np.exp(-0.5 * (circular / width) ** 2)
    out = arr.copy()
    for y in range(h):
        shift = int(round(amount * float(weight[y])))
        if shift:
            src_y = int((y - shift) % h)
            out[y] = arr[src_y]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _field_flicker(image: Image.Image, amount: float, field_rate: str, interlaced: bool, frame_time: float, frame_index: int) -> Image.Image:
    amount = max(0.0, min(0.5, float(amount)))
    if amount <= 1e-9:
        return image
    hz = 50.0 if str(field_rate).startswith("50") else 60.0
    phase = math.sin(2.0 * math.pi * hz * max(0.0, float(frame_time)))
    arr = np.asarray(image.convert("RGB"), dtype=np.float32).copy()
    if interlaced:
        parity = int(frame_index) & 1
        arr[parity::2] *= max(0.0, 1.0 - amount * (0.55 + 0.45 * abs(phase)))
        arr[1 - parity :: 2] *= min(1.5, 1.0 + amount * 0.22 * phase)
    else:
        arr *= max(0.0, 1.0 + amount * phase)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _lcd_inversion(image: Image.Image, pattern: str, amount: float, scale: int, phase: int) -> Image.Image:
    amount = max(0.0, min(0.5, float(amount)))
    scale = max(1, int(scale))
    phase = int(phase) & 1
    if amount <= 1e-9:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    if pattern == "Rows":
        polarity = ((yy // scale) + phase) & 1
    elif pattern == "Checker":
        polarity = ((xx // scale) + (yy // scale) + phase) & 1
    else:
        polarity = ((xx // scale) + phase) & 1
    signed = np.where(polarity == 0, -1.0, 1.0).astype(np.float32)
    lum = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    # Voltage inversion is most visible in mid-tones and should remain subtle.
    mid_weight = 1.0 - np.abs(lum / 127.5 - 1.0)
    factor = 1.0 + signed * amount * 0.18 * np.clip(mid_weight, 0.0, 1.0)
    out = arr * factor[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _dot_crawl(image: Image.Image, amount: float, scale: float, speed: float, frame_time: float) -> Image.Image:
    amount = max(0.0, min(1.0, float(amount)))
    scale = max(1.0, float(scale))
    speed = max(0.0, float(speed))
    if amount <= 1e-9:
        return image
    ycc = np.asarray(image.convert("YCbCr"), dtype=np.float32)
    chroma = np.sqrt((ycc[..., 1] - 128.0) ** 2 + (ycc[..., 2] - 128.0) ** 2) / 181.0
    # Crawl is strongest at chroma transitions.
    edge = np.abs(chroma - np.roll(chroma, 1, axis=1))
    h, w = chroma.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    phase = 2.0 * np.pi * speed * max(0.0, float(frame_time))
    carrier = np.sin((xx + yy * 0.5) * (2.0 * np.pi / scale) + phase)
    delta = carrier * edge * (32.0 * amount)
    ycc[..., 1] = np.clip(ycc[..., 1] + delta, 0.0, 255.0)
    ycc[..., 2] = np.clip(ycc[..., 2] - delta, 0.0, 255.0)
    return Image.fromarray(ycc.astype(np.uint8), "YCbCr").convert("RGB")


def _composite_noise(image: Image.Image, luma: float, chroma: float, seed: int, frame_time: float, frame_index: int) -> Image.Image:
    luma = max(0.0, min(1.0, float(luma)))
    chroma = max(0.0, min(1.0, float(chroma)))
    if luma <= 1e-9 and chroma <= 1e-9:
        return image
    arr = np.asarray(image.convert("YCbCr"), dtype=np.float32)
    h, w = arr.shape[:2]
    rng = _animated_rng(seed, frame_index, frame_time, salt=503)
    if luma > 0.0:
        grain = rng.normal(0.0, 22.0 * luma, size=(h, w)).astype(np.float32)
        # Slight horizontal correlation feels closer to analog composite noise.
        grain = (grain + np.roll(grain, 1, axis=1) * 0.35) / 1.35
        arr[..., 0] += grain
    if chroma > 0.0:
        # Ceiling division guarantees that the repeated low-resolution chroma
        # noise always covers widths that are not divisible by three.
        low_w = max(1, (w + 2) // 3)
        cnoise_small = rng.normal(0.0, 30.0 * chroma, size=(h, low_w, 2)).astype(np.float32)
        cnoise = np.repeat(cnoise_small, 3, axis=1)[:, :w]
        arr[..., 1:] += cnoise
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "YCbCr").convert("RGB")


def _rf_interference(image: Image.Image, amount: float, bands: int, speed: float, seed: int, frame_time: float, frame_index: int) -> Image.Image:
    amount = max(0.0, min(1.0, float(amount)))
    bands = max(1, min(16, int(bands)))
    speed = max(0.0, float(speed))
    if amount <= 1e-9:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = _animated_rng(seed, frame_index, frame_time, salt=607)
    phase = 2.0 * np.pi * speed * max(0.0, float(frame_time))
    interference = np.zeros((h, w), dtype=np.float32)
    for index in range(bands):
        freq = 0.5 + (index + 1) * 0.37
        angle = phase * (0.4 + index * 0.11) + float(rng.random()) * 2.0 * np.pi
        interference += np.sin((yy / max(1.0, h)) * 2.0 * np.pi * freq + (xx / max(1.0, w)) * 0.65 + angle)
    interference /= max(1, bands)
    snow = rng.normal(0.0, 1.0, size=(h, w)).astype(np.float32)
    delta = (interference * 22.0 + snow * 10.0) * amount
    out = arr + delta[..., None]
    # RF also makes rows wobble very slightly.
    wobble = np.rint(np.sin(np.arange(h) * 0.31 + phase) * amount * 3.0).astype(np.int32)
    shifted = np.empty_like(out)
    for y in range(h):
        shifted[y : y + 1] = _shift_with_edge(out[y : y + 1], int(wobble[y]), 0)
    return Image.fromarray(np.clip(shifted, 0, 255).astype(np.uint8), "RGB")


def _horizontal_tear(
    image: Image.Image,
    amount: int,
    bands: int,
    height: int,
    speed: float,
    seed: int,
    frame_time: float,
    frame_index: int,
) -> Image.Image:
    amount = max(0, int(amount))
    bands = max(1, min(16, int(bands)))
    height = max(1, int(height))
    speed = max(0.0, float(speed))
    if amount <= 0:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    h = arr.shape[0]
    rng = _animated_rng(seed, frame_index, frame_time, salt=709)
    phase = max(0.0, float(frame_time)) * speed
    for index in range(bands):
        base = ((index / bands) + phase * (0.17 + index * 0.03) + float(rng.random()) * 0.25) % 1.0
        y0 = min(h - 1, max(0, int(round(base * max(0, h - 1)))))
        local_h = min(height, h - y0)
        shift = int(round((float(rng.random()) * 2.0 - 1.0) * amount))
        if shift:
            out[y0 : y0 + local_h] = _shift_with_edge(arr[y0 : y0 + local_h], shift, 0)
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


def _vignette(
    image: Image.Image,
    strength: float,
    size: float,
    softness: float,
    roundness: float,
    center_x: float,
    center_y: float,
    color: str,
) -> Image.Image:
    strength = max(0.0, min(1.0, float(strength)))
    if strength <= 0.0:
        return image
    size = max(0.05, min(1.5, float(size)))
    softness = max(0.01, min(1.0, float(softness)))
    roundness = max(0.0, min(1.0, float(roundness)))
    center_x = max(-1.0, min(1.0, float(center_x)))
    center_y = max(-1.0, min(1.0, float(center_y)))

    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    height, width = arr.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    half_w = max(1.0, (width - 1) * 0.5)
    half_h = max(1.0, (height - 1) * 0.5)
    cx = (width - 1) * (0.5 + 0.5 * center_x)
    cy = (height - 1) * (0.5 + 0.5 * center_y)
    nx = np.abs((xx - cx) / half_w)
    ny = np.abs((yy - cy) / half_h)

    # 1.0 is round/elliptical; lower values become progressively squarer.
    exponent = 8.0 - 6.0 * roundness
    distance = np.power(np.power(nx, exponent) + np.power(ny, exponent), 1.0 / exponent)
    transition = np.clip((distance - size) / softness, 0.0, 1.0)
    transition = transition * transition * (3.0 - 2.0 * transition)
    mask = (transition * strength)[:, :, None]

    tint = np.asarray(hex_to_rgb(str(color)), dtype=np.float32).reshape((1, 1, 3))
    out = arr * (1.0 - mask) + tint * mask
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _noise(image: Image.Image, amount: float, seed: int, chroma: bool = False) -> Image.Image:
    amount = max(0.0, float(amount))
    if amount <= 0.0:
        return image
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    shape = arr.shape if bool(chroma) else (*arr.shape[:2], 1)
    noise = rng.normal(0.0, amount, size=shape)
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


def _ascii_stable_random_unit(*values: int) -> float:
    value = 0x811C9DC5
    for item in values:
        value ^= int(item) & 0xFFFFFFFF
        value = (value * 0x01000193) & 0xFFFFFFFF
    value ^= value >> 13
    value = (value * 0x85EBCA6B) & 0xFFFFFFFF
    value ^= value >> 16
    return float(value) / float(0xFFFFFFFF)


def _ascii_randomized_index(chars: str, index: int, amount: float, x: int, y: int) -> int:
    if amount <= 1e-9 or index < 0 or index >= len(chars):
        return index
    if chars[index] in _INTENTIONAL_BLANK_GLYPHS:
        return index
    visible = [i for i, ch in enumerate(chars) if ch not in _INTENTIONAL_BLANK_GLYPHS]
    if len(visible) <= 1:
        return index
    chance = max(0.0, min(1.0, float(amount) / 100.0))
    if _ascii_stable_random_unit(x, y, index, len(chars)) >= chance:
        return index
    radius = max(1, int(round(chance * max(1, len(visible) - 1))))
    candidates = [i for i in visible if i != index and abs(i - index) <= radius]
    if not candidates:
        candidates = [i for i in visible if i != index]
    if not candidates:
        return index
    weights = np.asarray([1.0 / (1.0 + abs(i - index)) for i in candidates], dtype=np.float64)
    if chance < 0.999:
        weights = weights ** max(0.35, 1.35 - chance)
    cumulative = np.cumsum(weights)
    pick = _ascii_stable_random_unit(x, y, index, radius, 17) * float(cumulative[-1])
    return int(candidates[int(np.searchsorted(cumulative, pick, side="right"))])


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
    symbol_randomization: float = 0.0,
    cell_mode: str = "Normal",
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
    mode_1_to_1 = str(cell_mode) == "1:1 Pixel Symbols"
    high_detail = str(mapping) == "Structure Match" and not mode_1_to_1
    ss = _ascii_supersampling_factor(supersampling) if high_detail else 1
    if mode_1_to_1:
        cell_width = cell_height = pitch_x = pitch_y = 1
    else:
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
                    index = _ascii_randomized_index(chars, index, float(symbol_randomization), int(x), int(y))
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
            chosen_index = _ascii_randomized_index(
                chars,
                int(index),
                float(symbol_randomization),
                int(record.get("x", 0)),
                int(record.get("y", 0)),
            )
            record["char"] = chars[int(chosen_index)]

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
        line_value = "".join(line_chars)
        lines.append(line_value if mode_1_to_1 else line_value.rstrip())
        colors.append(line_colors)

    if not mode_1_to_1:
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
        "cell_mode": "1:1 Pixel Symbols" if mode_1_to_1 else "Normal",
        "proxy_cell": max(1, int(cell_size)),
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
    symbol_randomization: float = 0.0,
    cell_mode: str = "Normal",
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
        symbol_randomization=symbol_randomization,
        cell_mode=cell_mode,
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
        symbol_randomization=float(p.get("symbol_randomization", 0.0)),
        cell_mode=str(p.get("cell_mode", "Normal")),
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
    symbol_randomization: float = 0.0,
    cell_mode: str = "Normal",
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
        symbol_randomization=symbol_randomization,
        cell_mode=cell_mode,
    )

    mode = str(background_mode)
    cell_mode_value = str(layout.get("cell_mode", "Normal"))
    if cell_mode_value == "1:1 Pixel Symbols":
        max_side = max(1, max(image.size))
        desired_proxy_cell = max(1, int(layout.get("proxy_cell", max(1, int(cell_size)))))
        proxy_cell = max(1, min(desired_proxy_cell, max(1, 4096 // max_side)))
        proxy_size = (max(1, image.width * proxy_cell), max(1, image.height * proxy_cell))
        if mode == "Transparent":
            canvas = Image.new("RGBA", proxy_size, (0, 0, 0, 0))
        elif mode == "Source Image":
            canvas = image.convert("RGBA").resize(proxy_size, Image.Resampling.NEAREST)
        else:
            canvas = Image.new("RGBA", proxy_size, (*hex_to_rgb(background), 255))
        draw = ImageDraw.Draw(canvas)
        cell_width = cell_height = pitch_x = pitch_y = proxy_cell
        font_size = max(2, round(proxy_cell * max(0.75, min(1.5, float(font_scale)))))
        ss = max(1, int(layout["supersampling"]))
        high_detail = True
    else:
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
    if cell_mode_value == "1:1 Pixel Symbols" and canvas.size != image.size:
        return canvas.resize(image.size, Image.Resampling.BOX)
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


def _blend_rgb(base: np.ndarray, effect: np.ndarray, mode: str) -> np.ndarray:
    mode = str(mode or "Normal")
    if mode == "Multiply":
        return base * effect
    if mode == "Screen":
        return 1.0 - (1.0 - base) * (1.0 - effect)
    if mode == "Overlay":
        return np.where(base <= 0.5, 2.0 * base * effect, 1.0 - 2.0 * (1.0 - base) * (1.0 - effect))
    if mode == "Soft Light":
        # W3C-style soft-light approximation.
        d = np.where(base <= 0.25, ((16.0 * base - 12.0) * base + 4.0) * base, np.sqrt(np.clip(base, 0.0, 1.0)))
        return np.where(effect <= 0.5, base - (1.0 - 2.0 * effect) * base * (1.0 - base), base + (2.0 * effect - 1.0) * (d - base))
    if mode == "Hard Light":
        return np.where(effect <= 0.5, 2.0 * base * effect, 1.0 - 2.0 * (1.0 - base) * (1.0 - effect))
    if mode == "Add":
        return np.clip(base + effect, 0.0, 1.0)
    if mode == "Difference":
        return np.abs(base - effect)
    if mode == "Darken":
        return np.minimum(base, effect)
    if mode == "Lighten":
        return np.maximum(base, effect)
    return effect


def _layer_mask_array(base_image: Image.Image, mask: dict[str, Any], target_size: tuple[int, int]) -> np.ndarray:
    w, h = target_size
    kind = str(mask.get("type", "None") or "None")
    strength = max(0.0, min(1.0, float(mask.get("strength", 1.0) or 0.0)))
    invert = bool(mask.get("invert", False))
    feather = max(0.0, min(1.0, float(mask.get("feather", 0.0) or 0.0)))

    if kind == "None":
        arr = np.ones((h, w), dtype=np.float32)
    elif kind == "Alpha":
        if "A" in base_image.getbands():
            alpha = base_image.getchannel("A")
            if alpha.size != target_size:
                alpha = alpha.resize(target_size, Image.Resampling.BILINEAR)
            arr = np.asarray(alpha, dtype=np.float32) / 255.0
        else:
            arr = np.ones((h, w), dtype=np.float32)
    elif kind in {"Luminance", "Shadows", "Highlights"}:
        rgb = base_image.convert("RGB")
        if rgb.size != target_size:
            rgb = rgb.resize(target_size, Image.Resampling.BILINEAR)
        pixels = np.asarray(rgb, dtype=np.float32) / 255.0
        lum = 0.2126 * pixels[..., 0] + 0.7152 * pixels[..., 1] + 0.0722 * pixels[..., 2]
        if kind == "Shadows":
            arr = np.clip(1.0 - lum, 0.0, 1.0)
        elif kind == "Highlights":
            arr = np.clip(lum, 0.0, 1.0)
        else:
            arr = np.clip(lum, 0.0, 1.0)
    else:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        nx = xx / max(1.0, w - 1.0)
        ny = yy / max(1.0, h - 1.0)
        if kind == "Linear Horizontal":
            arr = nx
        elif kind == "Linear Vertical":
            arr = ny
        else:  # Radial
            dx = (nx - 0.5) * 2.0
            dy = (ny - 0.5) * 2.0
            arr = np.clip(1.0 - np.sqrt(dx * dx + dy * dy), 0.0, 1.0)

    if feather > 1e-9:
        radius = max(0.1, feather * max(1.0, min(w, h)) * 0.08)
        mask_img = Image.fromarray(np.rint(np.clip(arr, 0.0, 1.0) * 255.0).astype(np.uint8), "L")
        mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=radius))
        arr = np.asarray(mask_img, dtype=np.float32) / 255.0
    if invert:
        arr = 1.0 - arr
    return np.clip(arr * strength, 0.0, 1.0)


def _apply_group_composite(base_image: Image.Image, group_image: Image.Image, group: dict[str, Any]) -> Image.Image:
    pseudo_step = {
        "opacity": float(group.get("opacity", 1.0) or 0.0),
        "blend_mode": str(group.get("blend_mode", "Normal") or "Normal"),
        "mask": {"type": "None", "invert": False, "strength": 1.0},
    }
    return _apply_layer_composite(base_image, group_image, pseudo_step)


def _apply_layer_composite(base_image: Image.Image, effect_image: Image.Image, step: dict[str, Any]) -> Image.Image:
    opacity = max(0.0, min(1.0, float(step.get("opacity", 1.0) or 0.0)))
    mode = str(step.get("blend_mode", "Normal") or "Normal")
    mask = step.get("mask") if isinstance(step.get("mask"), dict) else {"type": "None"}

    if _layer_composite_is_passthrough(step):
        return effect_image
    if opacity <= 1e-9:
        if base_image.size == effect_image.size:
            return base_image
        return base_image.resize(effect_image.size, Image.Resampling.BILINEAR)

    target_size = effect_image.size
    base = base_image.convert("RGB")
    if base.size != target_size:
        base = base.resize(target_size, Image.Resampling.BILINEAR)
    effect = effect_image.convert("RGB")
    base_arr = np.asarray(base, dtype=np.float32) / 255.0
    effect_arr = np.asarray(effect, dtype=np.float32) / 255.0
    blended = np.clip(_blend_rgb(base_arr, effect_arr, mode), 0.0, 1.0)
    mask_arr = _layer_mask_array(base_image, mask, target_size)
    mix = np.clip(mask_arr * opacity, 0.0, 1.0)[..., None]
    out = base_arr * (1.0 - mix) + blended * mix
    result = Image.fromarray(np.rint(np.clip(out, 0.0, 1.0) * 255.0).astype(np.uint8), "RGB")

    # Preserve the effect-stage alpha contract. Existing RasterMint effects keep
    # source transparency, so blend/mask controls should not unexpectedly make
    # transparent source pixels opaque.
    alpha = None
    if "A" in effect_image.getbands():
        alpha = effect_image.getchannel("A")
    elif "A" in base_image.getbands():
        alpha = base_image.getchannel("A")
    if alpha is not None:
        if alpha.size != target_size:
            alpha = alpha.resize(target_size, Image.Resampling.BILINEAR)
        result = result.convert("RGBA")
        result.putalpha(alpha)
    return result


def apply_normalized_effect_stack(
    image: Image.Image,
    stack: list[dict[str, Any]],
    palette: list[str],
    *,
    frame_time: float = 0.0,
    frame_index: int = 0,
    temporal_state: TemporalEffectState | None = None,
    render_cache: Any | None = None,
    cache_context: str = "",
    progress_callback: Callable[[int, int, str], None] | None = None,
    cancel_callback: Callable[[], bool] | None = None,
) -> Image.Image:
    """Apply a stack that has already been normalized by effect_schema.

    Internal processor paths use this to avoid normalizing the same stack a
    second time on every preview/video frame. Public ``apply_effect_stack``
    remains the safe entry point for arbitrary caller-provided stacks.
    """
    img = image if image.mode == "RGB" else image.convert("RGB")
    palette_np = palette_array(palette)

    total_steps = max(1, len(stack))

    def report_progress(completed: int, label: str) -> None:
        if progress_callback is not None:
            progress_callback(max(0, min(total_steps, int(completed))), total_steps, str(label or ""))

    cache_signatures: list[str] | None = None
    active_groups: list[dict[str, Any]] = []

    def _shared_prefix_length(left: list[str], right: list[str]) -> int:
        shared = 0
        while shared < len(left) and shared < len(right) and str(left[shared]) == str(right[shared]):
            shared += 1
        return shared

    def _open_runtime_groups(current_image: Image.Image, step: dict[str, Any]) -> Image.Image:
        current_path = [str(value) for value in (step.get("_group_path") or []) if str(value)]
        current_settings = canonicalize_layer_groups(list(step.get("_group_settings") or []))
        active_path = [str(entry.get("id", "")) for entry in active_groups]
        shared = _shared_prefix_length(active_path, current_path)
        image_out = current_image
        while len(active_groups) > shared:
            state = active_groups.pop()
            image_out = _apply_group_composite(state["base"], image_out, state["group"])
        by_id = {str(group.get("id", "")): dict(group) for group in current_settings}
        for gid in current_path[shared:]:
            group = by_id.get(gid)
            if group is not None:
                active_groups.append({"id": gid, "base": image_out.copy(), "group": group})
        return image_out

    def _close_runtime_groups(current_image: Image.Image, current_path: list[str], next_path: list[str]) -> Image.Image:
        shared = _shared_prefix_length(current_path, next_path)
        image_out = current_image
        while len(active_groups) > shared:
            state = active_groups.pop()
            image_out = _apply_group_composite(state["base"], image_out, state["group"])
        return image_out
    start_index = 0
    if render_cache is not None and cache_context:
        try:
            cache_signatures = render_cache.prefix_signatures(stack, palette)
            start_index, cached = render_cache.longest_prefix(str(cache_context), cache_signatures)
            if cached is not None:
                img = cached
        except Exception:
            # Caching is an optimization only. A stale/broken cache must never
            # affect the correctness of the processing pipeline.
            cache_signatures = None
            start_index = 0

    if start_index > 0:
        report_progress(start_index, "Using cached layers")

    for step_index, step in enumerate(stack):
        if step_index < start_index:
            continue
        if cancel_callback is not None and cancel_callback():
            raise ProcessingCancelled("Processing superseded by a newer preview")
        img = _open_runtime_groups(img, step)
        current_path = [str(value) for value in (step.get("_group_path") or []) if str(value)]
        next_step = stack[step_index + 1] if step_index + 1 < len(stack) else None
        next_path = [str(value) for value in ((next_step.get("_group_path") if isinstance(next_step, dict) else []) or []) if str(value)]
        if not step.get("enabled", True):
            img = _close_runtime_groups(img, current_path, next_path)
            if cache_signatures is not None and render_cache is not None:
                try:
                    render_cache.store(str(cache_context), cache_signatures[step_index], img)
                except Exception:
                    pass
            report_progress(step_index + 1, str(step.get("kind", "Layer")))
            continue
        kind = step["kind"]
        p = step["params"]
        layer_input = img if _layer_composite_is_passthrough(step) else img.copy()
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
        elif kind == "Tonal Map":
            img = _tonal_map(
                img,
                str(p.get("mode", "Tritone")),
                str(p.get("shadow_color", "#000000")),
                str(p.get("midtone_color", "#808080")),
                str(p.get("highlight_color", "#FFFFFF")),
                str(p.get("background_color", "#000000")),
                float(p.get("shadow_point", 0.0)),
                float(p.get("midpoint", 50.0)),
                float(p.get("highlight_point", 100.0)),
                float(p.get("blend_softness", 100.0)),
            )
        elif kind == "Grayscale": img = ImageOps.grayscale(img).convert("RGB")
        elif kind == "Invert": img = ImageOps.invert(img.convert("RGB"))
        elif kind == "Gaussian Blur":
            radius = float(p["radius"])
            if radius > 0: img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        elif kind == "Median Denoise": img = img.filter(ImageFilter.MedianFilter(size=max(1, int(p["radius"])) * 2 + 1))
        elif kind == "Sharpen": img = ImageEnhance.Sharpness(img).enhance(float(p["amount"]))
        elif kind == "Glow": img = _glow(img, float(p["radius"]), float(p["intensity"]))
        elif kind == "Bloom": img = _bloom(img, float(p["threshold"]), float(p["soft_knee"]), float(p["radius"]), float(p["intensity"]), str(p["blend"]))
        elif kind == "Vignette": img = _vignette(img, float(p["strength"]), float(p["size"]), float(p["softness"]), float(p["roundness"]), float(p["center_x"]), float(p["center_y"]), str(p["color"]))
        elif kind == "JPEG Compression": img = _jpeg_compression(img, int(p["quality"]))
        elif kind == "Chromatic Shift": img = _chromatic_shift(img, int(p["amount"]))
        elif kind == "RGB Split": img = _rgb_split(img, int(p["x"]), int(p["y"]))
        elif kind == "Posterize": img = _posterize(img, int(p["levels"]))
        elif kind == "Scanlines": img = _scanlines(img, int(p["spacing"]), float(p["strength"]))
        elif kind == "Interlace": img = _interlace(img, int(p["offset"]), float(p["darken"]))
        elif kind == "Display Persistence":
            if temporal_state is not None:
                img = temporal_state.apply_display_persistence(
                    str(step.get("id", "display-persistence")),
                    img,
                    p,
                    frame_time=frame_time,
                    frame_index=frame_index,
                )
        elif kind == "Chroma Bleed": img = _chroma_bleed(img, float(p["bleed"]), int(p["delay"]), float(p["strength"]))
        elif kind == "Tracking Error": img = _tracking_error(img, int(p["amount"]), int(p["band_height"]), float(p["instability"]), float(p["speed"]), int(p["seed"]), frame_time, frame_index)
        elif kind == "Tape Dropout": img = _tape_dropout(img, float(p["amount"]), int(p["length"]), int(p["thickness"]), float(p["strength"]), int(p["seed"]), frame_time, frame_index)
        elif kind == "Temporal Jitter": img = _temporal_jitter(img, float(p["x"]), float(p["y"]), float(p["speed"]), int(p["seed"]), frame_time, frame_index)
        elif kind == "Head Switching Noise": img = _head_switching_noise(img, int(p["height"]), int(p["shift"]), float(p["noise"]), float(p["strength"]), int(p["seed"]), frame_time, frame_index)
        elif kind == "RGB Convergence": img = _rgb_convergence(img, float(p["red_x"]), float(p["red_y"]), float(p["blue_x"]), float(p["blue_y"]), float(p["strength"]))
        elif kind == "CRT Mask": img = _crt_mask(img, str(p["mask_type"]), int(p["scale"]), float(p["strength"]), float(p["brightness"]))
        elif kind == "Phosphor Glow": img = _phosphor_glow(img, float(p["threshold"]), float(p["radius"]), float(p["intensity"]))
        elif kind == "Beam Width": img = _beam_width(img, int(p["spacing"]), float(p["width"]), float(p["strength"]))
        elif kind == "Horizontal Bloom": img = _horizontal_bloom(img, float(p["threshold"]), float(p["radius"]), float(p["intensity"]))
        elif kind == "Scanline Variation": img = _scanline_variation(img, int(p["spacing"]), float(p["strength"]), float(p["variation"]), float(p["speed"]), int(p["seed"]), frame_time)
        elif kind == "CRT Curvature": img = _crt_curvature(img, float(p["curvature"]), float(p["zoom"]), float(p["edge_fade"]), str(p.get("border_fill", "Solid Color")), str(p.get("border_color", "#000000")))
        elif kind == "Edge Distortion": img = _edge_distortion(img, float(p["amount"]), float(p["frequency"]), float(p["falloff"]))
        elif kind == "Vertical Sync Roll": img = _vertical_sync_roll(img, int(p["amount"]), float(p["speed"]), float(p["softness"]), frame_time)
        elif kind == "Field Flicker": img = _field_flicker(img, float(p["amount"]), str(p["field_rate"]), bool(p["interlaced"]), frame_time, frame_index)
        elif kind == "LCD Inversion": img = _lcd_inversion(img, str(p["pattern"]), float(p["amount"]), int(p["scale"]), int(p["phase"]))
        elif kind == "Dot Crawl": img = _dot_crawl(img, float(p["amount"]), float(p["scale"]), float(p["speed"]), frame_time)
        elif kind == "Composite Noise": img = _composite_noise(img, float(p["luma"]), float(p["chroma"]), int(p["seed"]), frame_time, frame_index)
        elif kind == "RF Interference": img = _rf_interference(img, float(p["amount"]), int(p["bands"]), float(p["speed"]), int(p["seed"]), frame_time, frame_index)
        elif kind == "Horizontal Tear": img = _horizontal_tear(img, int(p["amount"]), int(p["bands"]), int(p["height"]), float(p["speed"]), int(p["seed"]), frame_time, frame_index)
        elif kind == "Noise": img = _noise(img, float(p["amount"]), _seed(p, frame_index), bool(p.get("chroma", False)))
        elif kind == "Temporal Flicker": img = _flicker(img, float(p["amount"]), float(p["speed"]), frame_time)
        elif kind == "Temporal Pattern": img = _temporal_pattern(img, str(p["pattern"]), float(p["amount"]), float(p["speed"]), float(p["scale"]), float(p["phase"]), frame_time, int(p["seed"]))
        elif kind == "Pixel Aspect Ratio": img = _pixel_aspect_ratio(img, float(p["x"]), float(p["y"]), str(p["resample"]))
        elif kind == "Pixelate": img = _pixelate(img, int(round(float(p["size"]))))
        elif kind == "Pixel Art Cleanup":
            img = cleanup_pixel_art(
                img,
                orphan_removal=float(p.get("orphan_removal", 75)),
                cluster_cleanup=float(p.get("cluster_cleanup", 35)),
                line_cleanup=float(p.get("line_cleanup", 50)),
                staircase_correction=float(p.get("staircase_correction", 45)),
                tiny_island_size=int(p.get("tiny_island_size", 4)),
                edge_preservation=float(p.get("edge_preservation", 80)),
                passes=int(p.get("passes", 2)),
                connectivity=str(p.get("connectivity", "8-neighbour")),
                analysis_view=str(p.get("analysis_view", "Clean Result")),
            )
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
                symbol_randomization=float(p.get("symbol_randomization", 0.0)),
                cell_mode=str(p.get("cell_mode", "Normal")),
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
        elif kind == "Pop Tone":
            arr = np.asarray(img.convert("RGB"), dtype=np.float32)
            result = pop_tone_dither(arr, palette_np, int(p.get("scale", 8)), float(p.get("density", 0.72)), float(p.get("variation", 0.25)))
            img = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), "RGB")
        elif kind == "Polygon Dither":
            arr = np.asarray(img.convert("RGB"), dtype=np.float32)
            result = polygon_dither(arr, palette_np, str(p.get("variant", "Hexa-Poly")), int(p.get("cell_size", 12)))
            img = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), "RGB")
        elif kind == "Beehive":
            arr = np.asarray(img.convert("RGB"), dtype=np.float32)
            result = beehive_dither(arr, palette_np, int(p.get("scale", 10)), float(p.get("luminance_threshold", 0.5)), int(p.get("cell_size", 10)))
            img = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), "RGB")
        elif kind == "Print Lab":
            img = render_print_lab(img, p)
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
        elif kind == "Hardware Limits":
            img = apply_hardware_limits_layer(img, p, list(palette))
        elif kind == "Hardware Display":
            # Display-stage processing is intentionally applied after pixel
            # aspect correction by processor.process_image. Keeping this node
            # in the layer stack makes the stage visible/editable without
            # changing raw-frame export semantics.
            pass
        elif kind == "Dither":
            mix = max(0.0, min(1.0, float(p.get("mix", 1.0))))
            if mix <= 0.0:
                report_progress(step_index + 1, kind)
                continue
            before = img.convert("RGB")
            sampling = str(p.get("sampling", "Native"))
            working = (
                before.resize((before.width * 2, before.height * 2), Image.Resampling.BICUBIC)
                if sampling == "2× Supersampled"
                else before
            )
            arr = np.asarray(working, dtype=np.float32)
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
                custom_matrix=p.get("custom_matrix_json"),
                modulation_mode=str(p.get("modulation_mode", "Smooth Diffuse")),
                modulation_scale=float(p.get("modulation_scale", 12.0)),
                modulation_phase=float(p.get("modulation_phase", 0.0)),
                modulation_bias=float(p.get("modulation_bias", 0.0)),
                modulation_detail=float(p.get("modulation_detail", 0.55)),
                modulation_seed=int(p.get("modulation_seed", 1)),
            )
            bleed = float(p.get("bleed", 0.0))
            rounding = float(p.get("rounding", 0.0))
            if sampling == "2× Supersampled":
                high = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), "RGB")
                reduced = high.resize(before.size, Image.Resampling.BOX)
                result = np.asarray(reduced, dtype=np.float32)
                # Area downsampling creates intermediate RGB values; remap
                # before morphology so the final result remains palette-pure.
                result = _apply_dither_edge_treatment(result, palette_np, bleed=bleed, rounding=rounding)
            elif abs(bleed) > 1e-9 or rounding > 1e-9:
                result = _apply_dither_edge_treatment(result, palette_np, bleed=bleed, rounding=rounding)
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

        img = _apply_layer_composite(layer_input, img, step)
        img = _close_runtime_groups(img, current_path, next_path)
        if cache_signatures is not None and render_cache is not None:
            try:
                render_cache.store(str(cache_context), cache_signatures[step_index], img)
            except Exception:
                pass
        report_progress(step_index + 1, kind)
    while active_groups:
        state = active_groups.pop()
        img = _apply_group_composite(state["base"], img, state["group"])
    return img

def apply_effect_stack(
    image: Image.Image,
    stack: list[dict[str, Any]],
    palette: list[str],
    *,
    frame_time: float = 0.0,
    frame_index: int = 0,
    temporal_state: TemporalEffectState | None = None,
) -> Image.Image:
    return apply_normalized_effect_stack(
        image,
        normalize_effect_stack(stack),
        palette,
        frame_time=frame_time,
        frame_index=frame_index,
        temporal_state=temporal_state,
    )

