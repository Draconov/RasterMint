# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PIL import Image

from .effect_stack import apply_effect_stack, normalize_effect_stack, scale_stack_for_preview
from .settings import ProcessingSettings

PREVIEW_MAX_SIDE = 640
FAST_PREVIEW_MAX_SIDE = 320


def adaptive_preview_max_side(settings: ProcessingSettings, requested: int) -> int:
    """Lower interactive budgets for algorithms/palettes with heavy per-pixel work.

    Full preview requests (> PREVIEW_MAX_SIDE) are never reduced. The function
    only affects the draft/refined interactive proxy, not exported output.
    """
    requested = max(64, int(requested))
    if requested > PREVIEW_MAX_SIDE:
        return requested
    stack = normalize_effect_stack(settings.effect_stack, settings)
    algorithm = ""
    for step in stack:
        if step.get("enabled", True) and step.get("kind") == "Dither":
            algorithm = str(step.get("params", {}).get("algorithm", ""))
    expensive = algorithm in {"Dot Diffusion", "Riemersma"}
    large_palette_diffusion = len(settings.palette) > 64 and algorithm not in {
        "Nearest Palette", "Threshold", "Random", "Interleaved Gradient Noise",
        "Blue Noise", "Halftone",
    }
    if expensive or large_palette_diffusion:
        return min(requested, 180 if requested <= FAST_PREVIEW_MAX_SIDE else 360)
    return requested


def scaled_output_size(size: tuple[int, int], divisor: int) -> tuple[int, int]:
    divisor = max(1, int(divisor))
    width, height = size
    return max(1, width // divisor), max(1, height // divisor)


def _apply_output_scale(image: Image.Image, divisor: int) -> Image.Image:
    target = scaled_output_size(image.size, divisor)
    if target == image.size:
        return image
    return image.resize(target, Image.Resampling.LANCZOS)


def process_image(
    image: Image.Image,
    settings: ProcessingSettings,
    *,
    frame_time: float = 0.0,
    frame_index: int = 0,
) -> Image.Image:
    source = image if image.mode == "RGB" else image.convert("RGB")
    source = _apply_output_scale(source, settings.output_divisor)
    stack = normalize_effect_stack(settings.effect_stack, settings)
    return apply_effect_stack(
        source,
        stack,
        settings.palette,
        frame_time=frame_time,
        frame_index=frame_index,
    )


def make_preview_settings(
    settings: ProcessingSettings,
    final_size: tuple[int, int],
    preview_size: tuple[int, int],
) -> ProcessingSettings:
    """Clone settings and scale pixel-based effect parameters for previews."""
    preview = ProcessingSettings.from_dict(settings.to_dict())
    preview.output_divisor = 1
    preview.effect_stack = normalize_effect_stack(preview.effect_stack, preview)

    final_w, final_h = final_size
    preview_w, preview_h = preview_size
    if final_w <= 0 or final_h <= 0:
        return preview

    scale = min(preview_w / final_w, preview_h / final_h, 1.0)
    preview.effect_stack = scale_stack_for_preview(preview.effect_stack, scale)

    # Keep old presets visually consistent if they are rendered without a new
    # effect stack for any reason.
    if scale < 1.0:
        preview.blur_radius *= scale
        if preview.pixel_size > 1:
            preview.pixel_size = max(1, round(preview.pixel_size * scale))
    return preview


def make_preview_source(
    image: Image.Image,
    max_side: int = PREVIEW_MAX_SIDE,
    output_divisor: int = 1,
) -> Image.Image:
    max_side = max(64, int(max_side))
    target = scaled_output_size(image.size, output_divisor)
    largest = max(target)
    if largest > max_side:
        scale = max_side / largest
        target = (max(1, round(target[0] * scale)), max(1, round(target[1] * scale)))

    source = image if image.mode == "RGB" else image.convert("RGB")
    if source.size == target:
        return source
    return source.resize(target, Image.Resampling.LANCZOS)
