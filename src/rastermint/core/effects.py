# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from .settings import ProcessingSettings


def apply_adjustments(image: Image.Image, settings: ProcessingSettings) -> Image.Image:
    """Apply non-destructive tonal adjustments before dithering."""
    img = image if image.mode == "RGB" else image.convert("RGB")

    if settings.brightness:
        img = ImageEnhance.Brightness(img).enhance(
            max(0.0, 1.0 + settings.brightness / 100.0)
        )
    if settings.contrast:
        img = ImageEnhance.Contrast(img).enhance(
            max(0.0, 1.0 + settings.contrast / 100.0)
        )
    if settings.saturation:
        img = ImageEnhance.Color(img).enhance(
            max(0.0, 1.0 + settings.saturation / 100.0)
        )
    if abs(settings.gamma - 1.0) > 1e-6:
        inv_gamma = 1.0 / settings.gamma
        lut = [round(255 * ((i / 255) ** inv_gamma)) for i in range(256)]
        img = img.point(lut * 3)

    return img


def apply_filters(image: Image.Image, settings: ProcessingSettings) -> Image.Image:
    """Apply RasterMint's pre-dither image filters in a stable order.

    Filter order is intentionally explicit because reordering operations changes
    the final dither. A future effect-stack system can replace this fixed order
    without changing the processing core's public entry point.
    """
    img = image if image.mode == "RGB" else image.convert("RGB")

    if settings.grayscale:
        img = ImageOps.grayscale(img).convert("RGB")

    if settings.invert:
        img = ImageOps.invert(img)

    if settings.blur_radius > 0.0:
        img = img.filter(ImageFilter.GaussianBlur(radius=settings.blur_radius))

    if abs(settings.sharpen - 1.0) > 1e-6:
        img = ImageEnhance.Sharpness(img).enhance(settings.sharpen)

    return img
