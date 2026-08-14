# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import numpy as np
from PIL import Image, ImageEnhance

from .dither import apply_dither
from .palette import palette_array
from .settings import ProcessingSettings


def _apply_adjustments(image: Image.Image, s: ProcessingSettings) -> Image.Image:
    img = image.convert("RGB")
    if s.brightness:
        img = ImageEnhance.Brightness(img).enhance(max(0.0, 1.0 + s.brightness / 100.0))
    if s.contrast:
        img = ImageEnhance.Contrast(img).enhance(max(0.0, 1.0 + s.contrast / 100.0))
    if s.saturation:
        img = ImageEnhance.Color(img).enhance(max(0.0, 1.0 + s.saturation / 100.0))
    if abs(s.gamma - 1.0) > 1e-6:
        inv_gamma = 1.0 / s.gamma
        lut = [round(255 * ((i / 255) ** inv_gamma)) for i in range(256)]
        img = img.point(lut * 3)
    return img


def _pixelate_for_processing(image: Image.Image, pixel_size: int) -> tuple[Image.Image, tuple[int, int]]:
    original_size = image.size
    if pixel_size <= 1:
        return image, original_size
    w, h = original_size
    small = image.resize((max(1, w // pixel_size), max(1, h // pixel_size)), Image.Resampling.BOX)
    return small, original_size


def process_image(image: Image.Image, settings: ProcessingSettings) -> Image.Image:
    adjusted = _apply_adjustments(image, settings)
    working, output_size = _pixelate_for_processing(adjusted, settings.pixel_size)
    arr = np.asarray(working, dtype=np.float32)
    pal = palette_array(settings.palette)
    result = apply_dither(
        arr,
        pal,
        settings.algorithm,
        strength=settings.dither_strength,
        serpentine=settings.serpentine,
    ).astype(np.uint8)
    out = Image.fromarray(result, mode="RGB")
    if out.size != output_size:
        out = out.resize(output_size, Image.Resampling.NEAREST)
    return out


def make_preview_source(image: Image.Image, max_side: int = 960) -> Image.Image:
    img = image.convert("RGB").copy()
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return img
