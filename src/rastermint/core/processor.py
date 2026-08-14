# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import numpy as np
from PIL import Image, ImageEnhance

from .dither import apply_dither
from .palette import palette_array
from .settings import ProcessingSettings

PREVIEW_MAX_SIDE = 640


def scaled_output_size(size: tuple[int, int], divisor: int) -> tuple[int, int]:
    divisor = max(1, int(divisor))
    width, height = size
    return max(1, width // divisor), max(1, height // divisor)


def _apply_output_scale(image: Image.Image, divisor: int) -> Image.Image:
    divisor = max(1, int(divisor))
    target = scaled_output_size(image.size, divisor)
    if target == image.size:
        return image
    return image.resize(target, Image.Resampling.LANCZOS)


def _apply_adjustments(image: Image.Image, s: ProcessingSettings) -> Image.Image:
    img = image if image.mode == "RGB" else image.convert("RGB")
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
    output_size = image.size
    if pixel_size <= 1:
        return image, output_size
    width, height = output_size
    small = image.resize(
        (max(1, width // pixel_size), max(1, height // pixel_size)),
        Image.Resampling.BOX,
    )
    return small, output_size


def process_image(image: Image.Image, settings: ProcessingSettings) -> Image.Image:
    source = image if image.mode == "RGB" else image.convert("RGB")
    source = _apply_output_scale(source, settings.output_divisor)
    adjusted = _apply_adjustments(source, settings)
    working, output_size = _pixelate_for_processing(adjusted, settings.pixel_size)
    palette = palette_array(settings.palette)
    arr = np.asarray(working, dtype=np.float32)
    result = apply_dither(
        arr,
        palette,
        settings.algorithm,
        strength=settings.dither_strength,
        serpentine=settings.serpentine,
    ).astype(np.uint8)
    out = Image.fromarray(result, mode="RGB")

    if out.size != output_size:
        out = out.resize(output_size, Image.Resampling.NEAREST)
    return out


def make_preview_source(
    image: Image.Image,
    max_side: int = PREVIEW_MAX_SIDE,
    output_divisor: int = 1,
) -> Image.Image:
    """Create a bounded RGB preview of the *final output dimensions*.

    Output scaling is folded into the preview source itself.  The caller should
    therefore render this image with ``output_divisor=1``.  This avoids the
    accidental double-downscale that would otherwise turn, for example, a
    1920 px image at ÷4 into a 160 px preview instead of a 480 px preview.
    """
    max_side = max(64, int(max_side))
    target = scaled_output_size(image.size, output_divisor)
    largest = max(target)
    if largest > max_side:
        scale = max_side / largest
        target = (
            max(1, round(target[0] * scale)),
            max(1, round(target[1] * scale)),
        )

    source = image if image.mode == "RGB" else image.convert("RGB")
    if source.size == target:
        return source
    return source.resize(target, Image.Resampling.LANCZOS)
