# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from PIL import Image

from rastermint.core.animation import settings_at_time
from rastermint.core.processor import process_image
from rastermint.core.settings import ProcessingSettings


_FORMAT_SUFFIXES = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WEBP": ".webp",
    "TIFF": ".tif",
    "BMP": ".bmp",
}


def _normalize_format(value: object) -> str:
    fmt = str(value or "PNG").strip().upper()
    return fmt if fmt in _FORMAT_SUFFIXES else "PNG"


def _normalize_scale(value: object) -> int:
    try:
        scale = int(value)
    except (TypeError, ValueError):
        scale = 100
    return max(10, min(800, scale))


def _normalize_overwrite(value: object) -> str:
    mode = str(value or "auto-rename").strip().lower()
    return mode if mode in {"auto-rename", "replace", "skip"} else "auto-rename"


_RESAMPLING = {
    "NEAREST": Image.Resampling.NEAREST,
    "NEAREST (PIXEL-PERFECT)": Image.Resampling.NEAREST,
    "BILINEAR": Image.Resampling.BILINEAR,
    "BICUBIC": Image.Resampling.BICUBIC,
    "LANCZOS": Image.Resampling.LANCZOS,
}


def _normalize_resampling(value: object) -> Image.Resampling:
    name = str(value or "Nearest (pixel-perfect)").strip().upper()
    return _RESAMPLING.get(name, Image.Resampling.NEAREST)



def _ensure_output_path(path: Path, overwrite: str) -> Path | None:
    if overwrite == "replace":
        return path
    if overwrite == "skip" and path.exists():
        return None
    if overwrite != "auto-rename" or not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 2
    while True:
        candidate = parent / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def _save_image(image: Image.Image, path: Path, format_name: str) -> None:
    if format_name == "JPEG":
        image.convert("RGB").save(
            path,
            format="JPEG",
            quality=95,
            optimize=True,
            subsampling=0,
        )
    elif format_name == "WEBP":
        image.save(path, format="WEBP", quality=95, method=6)
    elif format_name == "TIFF":
        image.save(path, format="TIFF", compression="tiff_deflate")
    elif format_name == "BMP":
        image.save(path, format="BMP")
    else:
        image.save(path, format="PNG", optimize=True)


def _resize(
    image: Image.Image,
    size: tuple[int, int],
    resampling: Image.Resampling,
) -> Image.Image:
    if image.size == size:
        return image
    return image.resize(size, resampling)


def _apply_scaling(
    image: Image.Image,
    scale_percent: int,
    resampling: Image.Resampling,
) -> Image.Image:
    if scale_percent == 100:
        return image
    width = max(1, round(image.width * scale_percent / 100.0))
    height = max(1, round(image.height * scale_percent / 100.0))
    return _resize(image, (width, height), resampling)


def process_batch(
    paths: Iterable[str | Path],
    output_dir: str | Path,
    settings: ProcessingSettings,
    progress: Callable[[int, int, Path], None] | None = None,
    *,
    format_name: str = "PNG",
    scale_percent: int = 100,
    overwrite: str = "auto-rename",
    resampling: str = "Nearest (pixel-perfect)",
) -> list[Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    source_paths = [Path(p) for p in paths]
    total = len(source_paths)
    written: list[Path] = []

    format_name = _normalize_format(format_name)
    scale_percent = _normalize_scale(scale_percent)
    overwrite = _normalize_overwrite(overwrite)
    resampling_filter = _normalize_resampling(resampling)
    animated = settings_at_time(settings, 0.0)
    display_mode = animated.display_mode if getattr(animated, "display_export", False) else "raw"
    include_grid = bool(getattr(animated, "grid_enabled", False) and getattr(animated, "grid_export", False))
    suffix = _FORMAT_SUFFIXES[format_name]

    for index, path in enumerate(source_paths, start=1):
        with Image.open(path) as opened:
            source = opened.copy()
        source_size = source.size
        result = process_image(
            source,
            animated,
            frame_time=0.0,
            frame_index=0,
            display_mode=display_mode,
            include_grid=include_grid,
        )

        # Batch exports always keep each source file's own pixel dimensions at
        # 100%. Effects can internally render at a different raster size, so
        # normalize the processed result back to that source before export scale.
        result = _resize(result, source_size, resampling_filter)
        result = _apply_scaling(result, scale_percent, resampling_filter)
        target = destination / f"{path.stem}-rastermint{suffix}"
        final_target = _ensure_output_path(target, overwrite)
        if final_target is not None:
            _save_image(result, final_target, format_name)
            written.append(final_target)
            report_target = final_target
        else:
            report_target = target

        if progress:
            progress(index, total, report_target)

    return written
