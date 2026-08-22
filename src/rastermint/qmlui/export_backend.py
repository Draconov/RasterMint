# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image
from PySide6.QtCore import QUrl, Slot

from rastermint.core.animation import settings_at_time
from rastermint.core.processor import (
    PREVIEW_MAX_SIDE,
    adaptive_preview_max_side,
    display_output_size,
    make_preview_settings,
    make_preview_source,
    processed_raster_size,
    target_raster_size,
)
from rastermint.core.svg_export import save_svg

from .backend import _local_path
from .preferences_backend import RasterMintBackend as PreferencesBackend
from .workers import BatchWorker, ProcessingWorker


_FORMAT_SUFFIXES = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WEBP": ".webp",
    "TIFF": ".tif",
    "SVG": ".svg",
}

_BATCH_FORMAT_SUFFIXES = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WEBP": ".webp",
    "TIFF": ".tif",
    "BMP": ".bmp",
}

_RESAMPLING = {
    "NEAREST": Image.Resampling.NEAREST,
    "NEAREST (PIXEL-PERFECT)": Image.Resampling.NEAREST,
    "BILINEAR": Image.Resampling.BILINEAR,
    "BICUBIC": Image.Resampling.BICUBIC,
    "LANCZOS": Image.Resampling.LANCZOS,
}


def _clamp_scale_percent(value: object) -> int:
    try:
        scale = int(value)
    except (TypeError, ValueError):
        scale = 100
    return max(10, min(800, scale))


class RasterMintBackend(PreferencesBackend):
    """Add export workflows to the normal QML backend."""

    # ---------- immediate preview-mode switching ----------
    def _preview_superseded_jobs(self) -> set[int]:
        jobs = getattr(self, "_mode_switch_superseded_preview_jobs", None)
        if jobs is None:
            jobs = set()
            self._mode_switch_superseded_preview_jobs = jobs
        return jobs

    def _start_mode_switch_preview(self, label: str) -> None:
        source = self._active_source()
        if source is None:
            return

        settings = settings_at_time(self.settings, self._current_time)
        if label == "Quick":
            max_side = self._quick_side()
        elif label == "Stable":
            max_side = adaptive_preview_max_side(self.settings, PREVIEW_MAX_SIDE)
        else:
            max_side = self._safe_full_side()

        final_size = target_raster_size(source.size, settings)
        preview_source = make_preview_source(source, max_side=int(max_side), settings=settings)
        preview_settings = make_preview_settings(settings, final_size, preview_source.size)
        job = self._next_job()
        context = {
            "source_revision": self._source_revision,
            "settings_revision": self._settings_revision,
            "time": self._current_time,
            "preview_mode": label,
        }
        worker = ProcessingWorker(
            job,
            "preview-mode-switch",
            preview_source,
            preview_settings,
            context,
            frame_time=self._current_time,
            frame_index=max(
                0,
                round(
                    self._current_time
                    * (self._video_info.fps if self._video_info else settings.animation_fps)
                ),
            ),
            display_mode=settings.display_mode,
            include_grid=False,
        )
        self._connect_worker(worker)
        self.thread_pool.start(worker)

    @Slot(str)
    def setPreviewMode(self, mode: str) -> None:
        label = str(mode).title()
        if label not in {"Quick", "Stable", "Full"} or label == self._preview_mode:
            return

        if self._preview_running and self._latest_preview_job:
            self._preview_superseded_jobs().add(int(self._latest_preview_job))

        self._quick_timer.stop()
        self._stable_timer.stop()
        self._pending_preview_side = 0
        self._preview_mode = label
        self.app_settings.setValue("previewModeQml", label)
        self.settingsChanged.emit()

        if self.hasSource:
            self._start_mode_switch_preview(label)
            if label == "Quick":
                self._stable_timer.start(330)

        self._set_status(f"Preview render: {label}")

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

    @Slot(str, result=str)
    def suggestedExportFile(self, format_name: str = "PNG") -> str:
        if self._current_file is None:
            return ""

        fmt = str(format_name or "PNG").strip().upper()
        suffix = _FORMAT_SUFFIXES.get(fmt, ".png")
        path = self._current_file.with_name(self._current_file.stem + suffix)
        return QUrl.fromLocalFile(str(path)).toString()

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

    @Slot("QVariantList", "QVariant", "QVariantMap")
    def batchExportWithOptions(
        self,
        paths: list[object] | None,
        output_dir: object,
        options: dict[str, Any] | None = None,
    ) -> None:
        source_paths = []
        for raw in list(paths or []):
            path = Path(_local_path(raw))
            if str(path):
                source_paths.append(str(path))
        if not source_paths:
            return

        destination = str(Path(_local_path(output_dir)))
        if not destination:
            return

        opts = dict(options or {})
        format_name = str(opts.get("format", "PNG") or "PNG").strip().upper()
        if format_name not in _BATCH_FORMAT_SUFFIXES:
            format_name = "PNG"

        overwrite = str(opts.get("overwrite", "auto-rename") or "auto-rename").strip().lower()
        if overwrite not in {"auto-rename", "replace", "skip"}:
            overwrite = "auto-rename"

        size_mode = str(opts.get("sizeMode", "relative") or "relative").strip().lower()
        if size_mode not in {"relative", "fixed-current"}:
            size_mode = "relative"

        fixed_output_size: list[int] | None = None
        if size_mode == "fixed-current" and self.hasSource:
            info = self.exportImageInfo()
            fixed_output_size = [int(info.get("width", 1)), int(info.get("height", 1))]
        elif size_mode == "fixed-current":
            size_mode = "relative"

        worker_options = {
            "format": format_name,
            "scalePercent": _clamp_scale_percent(opts.get("scalePercent", 100)),
            "overwrite": overwrite,
            "sizeMode": size_mode,
            "fixedOutputSize": fixed_output_size,
        }

        job = self._next_job()
        worker = BatchWorker(job, source_paths, destination, self.settings, worker_options)
        self._connect_worker(worker)
        self.thread_pool.start(worker)
        self._set_status(f"Batch exporting {len(source_paths)} image(s)…")

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
        if purpose == "preview-mode-switch":
            context_map = context if isinstance(context, dict) else {}
            valid = (
                context_map.get("source_revision") == self._source_revision
                and context_map.get("settings_revision") == self._settings_revision
                and context_map.get("preview_mode") == self._preview_mode
            )
            if valid and isinstance(result, Image.Image):
                self._publish_preview(result)
            return

        if purpose == "preview" and int(job_id) in self._preview_superseded_jobs():
            self._preview_superseded_jobs().discard(int(job_id))
            self._preview_running = False
            pending = self._pending_preview_side
            self._pending_preview_side = 0
            if pending:
                self._request_preview(pending)
            return

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
