# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image
from PySide6.QtCore import Slot

from rastermint.core.animation import settings_at_time
from rastermint.core.processor import display_output_size, processed_raster_size
from rastermint.core.svg_export import save_svg

from .backend import _local_path
from .preferences_backend import RasterMintBackend as PreferencesBackend
from .workers import ProcessingWorker


_FORMAT_SUFFIXES = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WEBP": ".webp",
    "TIFF": ".tif",
    "SVG": ".svg",
}

_RESAMPLING = {
    "NEAREST": Image.Resampling.NEAREST,
    "NEAREST (PIXEL-PERFECT)": Image.Resampling.NEAREST,
    "BILINEAR": Image.Resampling.BILINEAR,
    "BICUBIC": Image.Resampling.BICUBIC,
    "LANCZOS": Image.Resampling.LANCZOS,
}


class RasterMintBackend(PreferencesBackend):
    """Add the still-image export workflow to the normal QML backend."""

    @Slot(result="QVariantMap")
    def exportImageInfo(self) -> dict[str, Any]:
        source = self._active_source()
        if source is None:
            return {"sourceWidth": 1, "sourceHeight": 1, "width": 1, "height": 1}

        animated = settings_at_time(self.settings, self._current_time)
        if animated.display_export:
            width, height = display_output_size(source.size, animated)
        else:
            width, height = processed_raster_size(source.size, animated)

        return {
            "sourceWidth": int(source.width),
            "sourceHeight": int(source.height),
            "width": max(1, int(width)),
            "height": max(1, int(height)),
        }

    @staticmethod
    def _advanced_export_path(value: str, format_name: str) -> Path:
        path = Path(_local_path(value))
        fmt = str(format_name or "PNG").strip().upper()
        suffix = _FORMAT_SUFFIXES.get(fmt, ".png")
        accepted = {
            "PNG": {".png"},
            "JPEG": {".jpg", ".jpeg"},
            "WEBP": {".webp"},
            "TIFF": {".tif", ".tiff"},
            "SVG": {".svg"},
        }.get(fmt, {suffix})
        if path.suffix.lower() not in accepted:
            path = path.with_suffix(suffix)
        return path

    @Slot(str, "QVariantMap")
    def exportImageWithOptions(self, value: str, options: dict[str, Any] | None = None) -> None:
        source = self._active_source()
        if source is None:
            return

        opts = dict(options or {})
        format_name = str(opts.get("format", "PNG") or "PNG").strip().upper()
        if format_name not in _FORMAT_SUFFIXES:
            format_name = "PNG"

        path = self._advanced_export_path(value, format_name)
        width = max(1, min(32768, int(opts.get("width", source.width) or source.width)))
        height = max(1, min(32768, int(opts.get("height", source.height) or source.height)))
        quality = max(1, min(100, int(opts.get("quality", 90) or 90)))
        resampling = str(opts.get("resampling", "Nearest (pixel-perfect)") or "Nearest (pixel-perfect)")

        animated = settings_at_time(self.settings, self._current_time)
        context = {
            "path": str(path),
            "advanced_export": True,
            "width": width,
            "height": height,
            "format": format_name,
            "quality": quality,
            "resampling": resampling,
        }

        job = self._next_job()
        self._export_jobs.add(job)
        worker = ProcessingWorker(
            job,
            "export-image",
            source.copy(),
            animated,
            context,
            frame_time=self._current_time,
            frame_index=max(
                0,
                round(
                    self._current_time
                    * (self._video_info.fps if self._video_info else animated.animation_fps)
                ),
            ),
            display_mode=animated.display_mode if animated.display_export else "raw",
            include_grid=False,
        )
        self._connect_worker(worker)
        self.thread_pool.start(worker)
        self._set_status(f"Exporting {path.name} at {width} × {height}…")

    @staticmethod
    def _save_advanced_image(result: Image.Image, context: dict[str, Any]) -> Path:
        path = Path(str(context.get("path", "output.png")))
        width = max(1, min(32768, int(context.get("width", result.width) or result.width)))
        height = max(1, min(32768, int(context.get("height", result.height) or result.height)))
        format_name = str(context.get("format", "PNG") or "PNG").strip().upper()
        quality = max(1, min(100, int(context.get("quality", 90) or 90)))
        resampling_name = str(
            context.get("resampling", "Nearest (pixel-perfect)") or "Nearest (pixel-perfect)"
        ).strip().upper()
        resampling = _RESAMPLING.get(resampling_name, Image.Resampling.NEAREST)

        output = result
        if output.size != (width, height):
            output = output.resize((width, height), resampling)

        if format_name == "SVG":
            save_svg(output, path)
            return path

        if format_name == "JPEG":
            output.convert("RGB").save(
                path,
                format="JPEG",
                quality=quality,
                optimize=True,
                subsampling=0,
            )
        elif format_name == "WEBP":
            output.save(path, format="WEBP", quality=quality, method=6)
        elif format_name == "TIFF":
            output.save(path, format="TIFF", compression="tiff_deflate")
        else:
            output.save(path, format="PNG", optimize=True)

        return path

    @Slot(int, str, object, object)
    def _worker_finished(self, job_id: int, purpose: str, result: object, context: object) -> None:
        if (
            purpose == "export-image"
            and isinstance(result, Image.Image)
            and isinstance(context, dict)
            and bool(context.get("advanced_export"))
        ):
            self._export_jobs.discard(job_id)
            try:
                path = self._save_advanced_image(result, context)
                self._set_status(f"Exported {path.name}")
            except Exception as exc:
                self.errorOccurred.emit("Could not export image", str(exc))
            return

        super()._worker_finished(job_id, purpose, result, context)
