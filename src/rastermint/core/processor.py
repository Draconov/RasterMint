# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import math
from typing import Callable

import numpy as np
from PIL import Image, ImageOps

from .effect_stack import apply_normalized_effect_stack, effect_stack_output_size, normalize_effect_stack
from .effect_schema import scale_normalized_stack_for_preview
from .hardware import render_display_view
from .palette import hex_to_rgb
from .settings import ProcessingSettings
from .temporal import TemporalEffectState

PREVIEW_MAX_SIDE = 640
FAST_PREVIEW_MAX_SIDE = 320


def runtime_effect_stack(settings: ProcessingSettings) -> list[dict[str, object]]:
    """Return the normalized stack with UI group/solo visibility applied.

    Group enable and Solo are non-destructive layer-workflow controls. They must
    affect previews and exports without overwriting each layer's own enabled
    flag, so runtime visibility is derived on a shallow copy only when needed.
    """
    stack = normalize_effect_stack(settings.effect_stack, settings)
    groups = {
        str(group.get("id", "")): bool(group.get("enabled", True))
        for group in getattr(settings, "layer_groups", [])
        if isinstance(group, dict) and str(group.get("id", ""))
    }
    solo_id = str(getattr(settings, "solo_layer_id", "") or "")
    if not groups and not solo_id:
        return stack

    runtime: list[dict[str, object]] = []
    for step in stack:
        visible = bool(step.get("enabled", True))
        group_id = str(step.get("group_id", "") or "")
        if group_id and not groups.get(group_id, True):
            visible = False
        if solo_id and str(step.get("id", "")) != solo_id:
            visible = False
        if visible == bool(step.get("enabled", True)):
            runtime.append(step)
        else:
            runtime.append({**step, "enabled": visible})
    return runtime


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
    ascii_mapping = ""
    for step in stack:
        if not step.get("enabled", True):
            continue
        if step.get("kind") == "Dither":
            algorithm = str(step.get("params", {}).get("algorithm", ""))
        if step.get("kind") == "Pixel Material":
            material = str(step.get("params", {}).get("style", ""))
        if step.get("kind") == "ASCII / Glyph":
            ascii_mapping = str(step.get("params", {}).get("mapping", "Density"))
    expensive = algorithm in {"Dot Diffusion", "Riemersma"}
    expensive_material = material in {"ASCII Tile", "Cross Stitch", "Brick", "Mosaic"}
    expensive_ascii = ascii_mapping == "Structure Match"
    large_palette_diffusion = len(settings.palette) > 64 and algorithm not in {
        "Nearest Palette", "Threshold", "Random", "Interleaved Gradient Noise",
        "Blue Noise", "Halftone",
    }
    if expensive or large_palette_diffusion or expensive_material or expensive_ascii:
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


def source_raster_size(source_size: tuple[int, int], settings: ProcessingSettings) -> tuple[int, int]:
    """Source raster dimensions after crop/rotation but before target fitting."""
    return _cropped_rotated_size(source_size, settings)


def linked_target_size(
    source_size: tuple[int, int],
    settings: ProcessingSettings,
    *,
    width: int | None = None,
    height: int | None = None,
    maximum: int = 16384,
) -> tuple[int, int]:
    """Return a target size linked to the transformed source aspect ratio.

    Exactly one of ``width``/``height`` should be supplied. The supplied axis
    is treated as authoritative unless the derived opposite axis would exceed
    the supported target-raster maximum, in which case both are scaled down
    together while preserving the ratio.
    """
    sw, sh = source_raster_size(source_size, settings)
    ratio = max(1e-9, float(sw) / max(1.0, float(sh)))
    limit = max(1, int(maximum))

    if width is not None:
        w = max(1, min(limit, int(round(width))))
        h = max(1, int(round(w / ratio)))
        if h > limit:
            h = limit
            w = max(1, min(limit, int(round(h * ratio))))
        return w, h

    if height is not None:
        h = max(1, min(limit, int(round(height))))
        w = max(1, int(round(h * ratio)))
        if w > limit:
            w = limit
            h = max(1, min(limit, int(round(w / ratio))))
        return w, h

    return source_raster_size(source_size, settings)


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


def processed_raster_size(source_size: tuple[int, int], settings: ProcessingSettings) -> tuple[int, int]:
    base = target_raster_size(source_size, settings)
    return effect_stack_output_size(base, runtime_effect_stack(settings))


def display_output_size(source_size: tuple[int, int], settings: ProcessingSettings) -> tuple[int, int]:
    width, height = processed_raster_size(source_size, settings)
    if settings.display_mode in {"corrected", "display"}:
        width = max(1, round(width * settings.pixel_aspect_x / max(0.05, settings.pixel_aspect_y)))
    return width, height


def image_has_transparency(image: Image.Image) -> bool:
    """Return True only when the image contains at least one non-opaque pixel."""
    try:
        if "A" in image.getbands() or "transparency" in image.info:
            alpha = image.convert("RGBA").getchannel("A")
            minimum, _maximum = alpha.getextrema()
            return int(minimum) < 255
    except Exception:
        return False
    return False


def _apply_alpha_source_transform(alpha: Image.Image, settings: ProcessingSettings) -> Image.Image:
    mask = alpha.convert("L")
    w, h = mask.size
    left = max(0, min(w - 1, round(w * settings.crop_left)))
    top = max(0, min(h - 1, round(h * settings.crop_top)))
    right = max(left + 1, min(w, round(w * (1.0 - settings.crop_right))))
    bottom = max(top + 1, min(h, round(h * (1.0 - settings.crop_bottom))))
    if (left, top, right, bottom) != (0, 0, w, h):
        mask = mask.crop((left, top, right, bottom))
    if settings.flip_horizontal:
        mask = ImageOps.mirror(mask)
    if settings.flip_vertical:
        mask = ImageOps.flip(mask)
    rotation = settings.rotation % 360
    if rotation == 90:
        mask = mask.transpose(Image.Transpose.ROTATE_270)
    elif rotation == 180:
        mask = mask.transpose(Image.Transpose.ROTATE_180)
    elif rotation == 270:
        mask = mask.transpose(Image.Transpose.ROTATE_90)
    return mask


def _apply_axis_mirror_alpha(alpha: Image.Image, settings: ProcessingSettings) -> Image.Image:
    if not settings.mirror_horizontal and not settings.mirror_vertical:
        return alpha.convert("L")

    arr = np.asarray(alpha.convert("L"), dtype=np.uint8).copy()
    height, width = arr.shape
    if settings.mirror_horizontal and width > 1:
        axis = max(0.0, min(1.0, settings.mirror_horizontal_axis)) * (width - 1)
        for x in range(max(0, math.floor(axis) + 1), width):
            source_x = int(round(2.0 * axis - x))
            if 0 <= source_x < width:
                arr[:, x] = arr[:, source_x]
    if settings.mirror_vertical and height > 1:
        axis = max(0.0, min(1.0, settings.mirror_vertical_axis)) * (height - 1)
        for y in range(max(0, math.floor(axis) + 1), height):
            source_y = int(round(2.0 * axis - y))
            if 0 <= source_y < height:
                arr[y, :] = arr[source_y, :]
    return Image.fromarray(arr, "L")


def _fit_alpha_to_target(
    alpha: Image.Image,
    target: tuple[int, int],
    *,
    fit_mode: str,
    position_x: float,
    position_y: float,
) -> Image.Image:
    tw, th = max(1, int(target[0])), max(1, int(target[1]))
    mask = alpha.convert("L")
    if mask.size == (tw, th):
        return mask
    mode = str(fit_mode or "fit").lower()
    if mode == "stretch":
        return mask.resize((tw, th), Image.Resampling.LANCZOS)

    iw, ih = mask.size
    if mode == "fill":
        scale = max(tw / max(1, iw), th / max(1, ih))
        rw, rh = max(1, round(iw * scale)), max(1, round(ih * scale))
        resized = mask.resize((rw, rh), Image.Resampling.LANCZOS)
        extra_x = max(0, rw - tw)
        extra_y = max(0, rh - th)
        fx = (max(-1.0, min(1.0, position_x)) + 1.0) * 0.5
        fy = (max(-1.0, min(1.0, position_y)) + 1.0) * 0.5
        left = round(extra_x * fx)
        top = round(extra_y * fy)
        return resized.crop((left, top, left + tw, top + th))

    scale = min(tw / max(1, iw), th / max(1, ih))
    rw, rh = max(1, round(iw * scale)), max(1, round(ih * scale))
    resized = mask.resize((rw, rh), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (tw, th), 0)
    fx = (max(-1.0, min(1.0, position_x)) + 1.0) * 0.5
    fy = (max(-1.0, min(1.0, position_y)) + 1.0) * 0.5
    left = round(max(0, tw - rw) * fx)
    top = round(max(0, th - rh) * fy)
    canvas.paste(resized, (left, top))
    return canvas


def prepare_transparency_mask(
    image: Image.Image,
    settings: ProcessingSettings,
    *,
    target_override: tuple[int, int] | None = None,
    output_size: tuple[int, int] | None = None,
) -> Image.Image | None:
    """Transform source alpha through RasterMint geometry without altering it creatively.

    The mask follows crop, flips, rotation, target fitting and mirror axes. Effects
    keep the original transparency silhouette; if an effect/display stage changes
    framebuffer dimensions the mask is expanded to that result using nearest
    neighbour so transparent source regions stay transparent.
    """
    if not image_has_transparency(image):
        return None
    alpha = image.convert("RGBA").getchannel("A")
    transformed = _apply_alpha_source_transform(alpha, settings)
    target = target_override or target_raster_size(image.size, settings)
    mask = _fit_alpha_to_target(
        transformed,
        target,
        fit_mode=settings.fit_mode,
        position_x=settings.position_x,
        position_y=settings.position_y,
    )
    mask = _apply_axis_mirror_alpha(mask, settings)
    if output_size is not None and mask.size != output_size:
        mask = mask.resize(output_size, Image.Resampling.NEAREST)
    return mask


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



def _apply_axis_mirror(image: Image.Image, settings: ProcessingSettings) -> Image.Image:
    """Reflect one side of the framebuffer around movable mirror axes.

    Horizontal mirroring keeps the left side and reflects it into the right
    side around a vertical axis. Vertical mirroring keeps the top side and
    reflects it into the bottom side around a horizontal axis. The canvas size
    stays unchanged while the axis is dragged.
    """
    if not settings.mirror_horizontal and not settings.mirror_vertical:
        return image

    arr = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    height, width = arr.shape[:2]

    if settings.mirror_horizontal and width > 1:
        axis = max(0.0, min(1.0, settings.mirror_horizontal_axis)) * (width - 1)
        for x in range(max(0, math.floor(axis) + 1), width):
            source_x = int(round(2.0 * axis - x))
            if 0 <= source_x < width:
                arr[:, x, :] = arr[:, source_x, :]

    if settings.mirror_vertical and height > 1:
        axis = max(0.0, min(1.0, settings.mirror_vertical_axis)) * (height - 1)
        for y in range(max(0, math.floor(axis) + 1), height):
            source_y = int(round(2.0 * axis - y))
            if 0 <= source_y < height:
                arr[y, :, :] = arr[source_y, :, :]

    return Image.fromarray(arr, "RGB")

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
    raster = _fit_to_target(
        transformed,
        target,
        fit_mode=settings.fit_mode,
        position_x=settings.position_x,
        position_y=settings.position_y,
        background=background,
    )
    return _apply_axis_mirror(raster, settings)


_TILE_SAFE_EFFECTS = frozenset({
    "Adjustments", "Levels", "Hue Rotate", "Grayscale", "Invert", "Posterize",
    "Channel Swap", "Hardware Display",
})


def _stack_supports_exact_tiling(stack: list[dict[str, object]]) -> bool:
    """Return whether independently processed tiles are pixel-identical.

    Only point-wise effects are admitted here. Neighborhood filters, geometry,
    temporal/random effects, hardware tile constraints and ordered diffusion
    deliberately fall back to the normal full-frame path.
    """
    for step in stack:
        if not bool(step.get("enabled", True)):
            continue
        mask = step.get("mask") if isinstance(step.get("mask"), dict) else {}
        if str(mask.get("type", "None") or "None") in {"Linear Horizontal", "Linear Vertical", "Radial"}:
            return False
        kind = str(step.get("kind", ""))
        if kind == "Dither":
            params = step.get("params") if isinstance(step.get("params"), dict) else {}
            if str(params.get("algorithm", "")) not in {"Nearest Palette", "Threshold"}:
                return False
            continue
        if kind not in _TILE_SAFE_EFFECTS:
            return False
    return True


def _apply_stack_tiled(
    source: Image.Image,
    stack: list[dict[str, object]],
    palette: list[str],
    *,
    tile_size: int,
    frame_time: float,
    frame_index: int,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> Image.Image:
    tile_size = max(256, min(4096, int(tile_size)))
    output = Image.new(source.mode, source.size)
    tiles_x = max(1, math.ceil(source.width / tile_size))
    tiles_y = max(1, math.ceil(source.height / tile_size))
    total_tiles = tiles_x * tiles_y
    completed = 0
    for top in range(0, source.height, tile_size):
        bottom = min(source.height, top + tile_size)
        for left in range(0, source.width, tile_size):
            right = min(source.width, left + tile_size)
            tile = source.crop((left, top, right, bottom))
            rendered = apply_normalized_effect_stack(
                tile,
                stack,  # type: ignore[arg-type]
                palette,
                frame_time=frame_time,
                frame_index=frame_index,
            )
            # Tile-safe effects are size preserving by definition. Keep a
            # defensive fallback contract if a future schema change violates it.
            if rendered.size != tile.size:
                raise RuntimeError("A tile-safe effect unexpectedly changed raster size")
            if output.mode != rendered.mode:
                output = output.convert(rendered.mode)
            output.paste(rendered, (left, top))
            completed += 1
            if progress_callback is not None:
                progress_callback(completed, total_tiles, "Processing tiles")
    return output


def process_image(
    image: Image.Image,
    settings: ProcessingSettings,
    *,
    frame_time: float = 0.0,
    frame_index: int = 0,
    display_mode: str = "raw",
    include_grid: bool = False,
    temporal_state: TemporalEffectState | None = None,
    render_cache: object | None = None,
    cache_context: str = "",
    tiled_processing: bool = True,
    tile_size: int = 1024,
    tile_threshold_pixels: int = 12_000_000,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> Image.Image:
    stack = runtime_effect_stack(settings)
    overall_total = max(2, len(stack) + 2)
    if progress_callback is not None:
        progress_callback(0, overall_total, "Preparing source")

    source = prepare_raster_source(image, settings)
    if progress_callback is not None:
        progress_callback(1, overall_total, "Preparing source")

    display_stage_present = any(step.get("kind") == "Hardware Display" for step in stack)
    display_profiles = [
        dict(step.get("params") or {})
        for step in stack
        if step.get("kind") == "Hardware Display" and step.get("enabled", True)
    ]
    use_tiles = (
        bool(tiled_processing)
        and source.width * source.height >= max(1, int(tile_threshold_pixels))
        and temporal_state is None
        and _stack_supports_exact_tiling(stack)
    )
    if use_tiles:
        def tiled_progress(current: int, total: int, label: str) -> None:
            if progress_callback is None:
                return
            span = max(1, overall_total - 2)
            fraction = max(0.0, min(1.0, current / max(1, total)))
            mapped = 1 + round(fraction * span)
            progress_callback(mapped, overall_total, label)

        result = _apply_stack_tiled(
            source, stack, settings.palette,
            tile_size=tile_size,
            frame_time=frame_time,
            frame_index=frame_index,
            progress_callback=tiled_progress if progress_callback is not None else None,
        )
    else:
        cache = render_cache
        resolved_context = str(cache_context or "")
        if cache is not None:
            # Stateful/animated frames must never borrow static intermediate
            # results. Cache use is intentionally restricted to frame zero.
            if temporal_state is not None or abs(float(frame_time)) > 1e-12 or int(frame_index) != 0:
                cache = None
            elif not resolved_context:
                try:
                    resolved_context = str(cache.source_signature(source))
                except Exception:
                    cache = None

        def layer_progress(current: int, total: int, label: str) -> None:
            del total
            if progress_callback is not None:
                progress_callback(1 + current, overall_total, label)

        result = apply_normalized_effect_stack(
            source,
            stack,
            settings.palette,
            frame_time=frame_time,
            frame_index=frame_index,
            temporal_state=temporal_state,
            render_cache=cache,
            cache_context=resolved_context,
            progress_callback=layer_progress if progress_callback is not None else None,
        )

    if progress_callback is not None:
        progress_callback(overall_total - 1, overall_total, "Finalizing display")

    if display_mode != "raw" or include_grid:
        alpha = result.getchannel("A") if "A" in result.getbands() else None
        result = render_display_view(
            result.convert("RGB"),
            settings,
            mode=display_mode,
            include_grid=include_grid,
            display_profiles=display_profiles if display_stage_present else None,
        )
        if alpha is not None:
            if alpha.size != result.size:
                alpha = alpha.resize(result.size, Image.Resampling.NEAREST)
            result = result.convert("RGBA")
            result.putalpha(alpha)

    if progress_callback is not None:
        progress_callback(overall_total, overall_total, "Complete")
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
    preview = settings.clone()
    preview.output_divisor = 1
    preview.target_enabled = False
    preview.target_width = 0
    preview.target_height = 0
    preview.crop_left = preview.crop_top = preview.crop_right = preview.crop_bottom = 0.0
    preview.rotation = 0
    preview.flip_horizontal = False
    preview.flip_vertical = False
    preview.mirror_horizontal = False
    preview.mirror_vertical = False
    preview.mirror_horizontal_axis = 0.5
    preview.mirror_vertical_axis = 0.5
    preview.fit_mode = "stretch"
    preview.position_x = preview.position_y = 0.0
    preview.effect_stack = normalize_effect_stack(preview.effect_stack, preview)

    final_w, final_h = final_size
    preview_w, preview_h = preview_size
    if final_w <= 0 or final_h <= 0:
        return preview

    scale = min(preview_w / final_w, preview_h / final_h, 1.0)
    preview.effect_stack = scale_normalized_stack_for_preview(preview.effect_stack, scale)

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
