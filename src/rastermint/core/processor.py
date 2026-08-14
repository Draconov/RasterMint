# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PIL import Image, ImageOps

from .effect_stack import apply_effect_stack, normalize_effect_stack, scale_stack_for_preview
from .hardware import apply_hardware_constraints, render_display_view
from .palette import hex_to_rgb
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
    material = ""
    for step in stack:
        if not step.get("enabled", True):
            continue
        if step.get("kind") == "Dither":
            algorithm = str(step.get("params", {}).get("algorithm", ""))
        if step.get("kind") == "Pixel Material":
            material = str(step.get("params", {}).get("style", ""))
    expensive = algorithm in {"Dot Diffusion", "Riemersma"}
    expensive_material = material in {"ASCII Tile", "Cross Stitch", "Brick", "Mosaic"}
    large_palette_diffusion = len(settings.palette) > 64 and algorithm not in {
        "Nearest Palette", "Threshold", "Random", "Interleaved Gradient Noise",
        "Blue Noise", "Halftone",
    }
    if expensive or large_palette_diffusion or expensive_material:
        return min(requested, 180 if requested <= FAST_PREVIEW_MAX_SIDE else 360)
    return requested


def scaled_output_size(size: tuple[int, int], divisor: int) -> tuple[int, int]:
    """Legacy divisor-based output size retained for old presets and CLI."""
    divisor = max(1, int(divisor))
    width, height = size
    return max(1, width // divisor), max(1, height // divisor)


def _cropped_rotated_size(size: tuple[int, int], settings: ProcessingSettings) -> tuple[int, int]:
    width, height = size
    width = max(1, round(width * max(0.02, 1.0 - settings.crop_left - settings.crop_right)))
    height = max(1, round(height * max(0.02, 1.0 - settings.crop_top - settings.crop_bottom)))
    if settings.rotation % 180:
        width, height = height, width
    return width, height


def target_raster_size(source_size: tuple[int, int], settings: ProcessingSettings) -> tuple[int, int]:
    transformed = _cropped_rotated_size(source_size, settings)
    if settings.target_enabled:
        width = int(settings.target_width)
        height = int(settings.target_height)
        if width > 0 and height > 0:
            return width, height
        if width > 0:
            return width, max(1, round(width * transformed[1] / max(1, transformed[0])))
        if height > 0:
            return max(1, round(height * transformed[0] / max(1, transformed[1]))), height
    return scaled_output_size(transformed, settings.output_divisor)


def display_output_size(source_size: tuple[int, int], settings: ProcessingSettings) -> tuple[int, int]:
    width, height = target_raster_size(source_size, settings)
    if settings.display_mode in {"corrected", "display"}:
        width = max(1, round(width * settings.pixel_aspect_x / max(0.05, settings.pixel_aspect_y)))
    return width, height


def _apply_source_transform(image: Image.Image, settings: ProcessingSettings) -> Image.Image:
    img = image if image.mode == "RGB" else image.convert("RGB")
    w, h = img.size
    left = max(0, min(w - 1, round(w * settings.crop_left)))
    top = max(0, min(h - 1, round(h * settings.crop_top)))
    right = max(left + 1, min(w, round(w * (1.0 - settings.crop_right))))
    bottom = max(top + 1, min(h, round(h * (1.0 - settings.crop_bottom))))
    if (left, top, right, bottom) != (0, 0, w, h):
        img = img.crop((left, top, right, bottom))

    if settings.flip_horizontal:
        img = ImageOps.mirror(img)
    if settings.flip_vertical:
        img = ImageOps.flip(img)
    rotation = settings.rotation % 360
    if rotation == 90:
        img = img.transpose(Image.Transpose.ROTATE_270)  # clockwise
    elif rotation == 180:
        img = img.transpose(Image.Transpose.ROTATE_180)
    elif rotation == 270:
        img = img.transpose(Image.Transpose.ROTATE_90)
    return img


def _fit_to_target(
    image: Image.Image,
    target: tuple[int, int],
    *,
    fit_mode: str,
    position_x: float,
    position_y: float,
    background: tuple[int, int, int],
) -> Image.Image:
    tw, th = max(1, int(target[0])), max(1, int(target[1]))
    if image.size == (tw, th):
        return image.convert("RGB")
    mode = str(fit_mode or "fit").lower()
    if mode == "stretch":
        return image.resize((tw, th), Image.Resampling.LANCZOS)

    iw, ih = image.size
    if mode == "fill":
        scale = max(tw / max(1, iw), th / max(1, ih))
        rw, rh = max(1, round(iw * scale)), max(1, round(ih * scale))
        resized = image.resize((rw, rh), Image.Resampling.LANCZOS)
        extra_x = max(0, rw - tw)
        extra_y = max(0, rh - th)
        # -1 = left/top, +1 = right/bottom.
        fx = (max(-1.0, min(1.0, position_x)) + 1.0) * 0.5
        fy = (max(-1.0, min(1.0, position_y)) + 1.0) * 0.5
        left = round(extra_x * fx)
        top = round(extra_y * fy)
        return resized.crop((left, top, left + tw, top + th)).convert("RGB")

    # Fit: preserve all source content and letterbox the remainder.
    scale = min(tw / max(1, iw), th / max(1, ih))
    rw, rh = max(1, round(iw * scale)), max(1, round(ih * scale))
    resized = image.resize((rw, rh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (tw, th), background)
    fx = (max(-1.0, min(1.0, position_x)) + 1.0) * 0.5
    fy = (max(-1.0, min(1.0, position_y)) + 1.0) * 0.5
    left = round(max(0, tw - rw) * fx)
    top = round(max(0, th - rh) * fy)
    canvas.paste(resized, (left, top))
    return canvas


def prepare_raster_source(
    image: Image.Image,
    settings: ProcessingSettings,
    *,
    target_override: tuple[int, int] | None = None,
) -> Image.Image:
    transformed = _apply_source_transform(image, settings)
    target = target_override or target_raster_size(image.size, settings)
    background = hex_to_rgb(settings.palette[0]) if settings.palette else (0, 0, 0)
    return _fit_to_target(
        transformed,
        target,
        fit_mode=settings.fit_mode,
        position_x=settings.position_x,
        position_y=settings.position_y,
        background=background,
    )


def process_image(
    image: Image.Image,
    settings: ProcessingSettings,
    *,
    frame_time: float = 0.0,
    frame_index: int = 0,
    display_mode: str = "raw",
    include_grid: bool = False,
) -> Image.Image:
    source = prepare_raster_source(image, settings)
    stack = normalize_effect_stack(settings.effect_stack, settings)
    result = apply_effect_stack(
        source,
        stack,
        settings.palette,
        frame_time=frame_time,
        frame_index=frame_index,
    )
    if settings.hardware_constraints_enabled and settings.hardware_constraints:
        result = apply_hardware_constraints(result, settings.hardware_constraints)
    if display_mode != "raw" or include_grid:
        result = render_display_view(result, settings, mode=display_mode, include_grid=include_grid)
    return result


def make_preview_settings(
    settings: ProcessingSettings,
    final_size: tuple[int, int],
    preview_size: tuple[int, int],
) -> ProcessingSettings:
    """Clone settings and scale pixel-based effect parameters for previews.

    The preview source is already transformed/resized into a proxy framebuffer,
    so source-transform and target-raster fields are disabled on the clone to
    avoid applying them twice.
    """
    preview = ProcessingSettings.from_dict(settings.to_dict())
    preview.output_divisor = 1
    preview.target_enabled = False
    preview.target_width = 0
    preview.target_height = 0
    preview.crop_left = preview.crop_top = preview.crop_right = preview.crop_bottom = 0.0
    preview.rotation = 0
    preview.flip_horizontal = False
    preview.flip_vertical = False
    preview.fit_mode = "stretch"
    preview.position_x = preview.position_y = 0.0
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
        preview.grid_spacing = max(1, round(preview.grid_spacing * scale))
        if preview.grid_major_spacing > 0:
            preview.grid_major_spacing = max(1, round(preview.grid_major_spacing * scale))
    return preview


def make_preview_source(
    image: Image.Image,
    max_side: int = PREVIEW_MAX_SIDE,
    output_divisor: int = 1,
    settings: ProcessingSettings | None = None,
) -> Image.Image:
    """Create the proxy framebuffer used by interactive preview.

    `output_divisor` remains for API compatibility with older tests/callers.
    New code should pass `settings`, allowing exact target raster, crop, fit and
    hardware profile geometry to be previewed accurately.
    """
    max_side = max(64, int(max_side))
    if settings is None:
        target = scaled_output_size(image.size, output_divisor)
        largest = max(target)
        if largest > max_side:
            scale = max_side / largest
            target = (max(1, round(target[0] * scale)), max(1, round(target[1] * scale)))
        source = image if image.mode == "RGB" else image.convert("RGB")
        if source.size == target:
            return source
        return source.resize(target, Image.Resampling.LANCZOS)

    final_target = target_raster_size(image.size, settings)
    target = final_target
    largest = max(target)
    if largest > max_side:
        scale = max_side / largest
        target = (max(1, round(target[0] * scale)), max(1, round(target[1] * scale)))
    return prepare_raster_source(image, settings, target_override=target)
