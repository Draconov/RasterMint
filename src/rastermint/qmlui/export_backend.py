# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops
from PySide6.QtCore import QUrl, Slot
from rastermint.core.animation import settings_at_time
from rastermint.core.effect_stack import ascii_text_grid_for_stack, normalize_effect_stack
from rastermint.core.processor import (
    PREVIEW_MAX_SIDE,
    adaptive_preview_max_side,
    display_output_size,
    image_has_transparency,
    make_preview_settings,
    make_preview_source,
    prepare_raster_source,
    prepare_transparency_mask,
    processed_raster_size,
    target_raster_size,
)
from rastermint.core.settings import ProcessingSettings
from rastermint.core.svg_export import save_svg

from .backend import _local_path
from .batch_worker import BatchWorker
from .preferences_backend import RasterMintBackend as PreferencesBackend
from .workers import ProcessingWorker

_FORMAT_SUFFIXES = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WEBP": ".webp",
    "TIFF": ".tif",
    "SVG": ".svg",
    "TXT": ".txt",
}

_BATCH_FORMAT_SUFFIXES = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WEBP": ".webp",
    "TIFF": ".tif",
    "BMP": ".bmp",
}
_ALPHA_FORMATS = {"PNG", "WEBP", "TIFF", "SVG"}
_BATCH_ALPHA_FORMATS = {"PNG", "WEBP", "TIFF"}

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
    """Add export workflows and keep UI profile identity in sync with settings."""

    # These values describe library/UI metadata rather than the rendered result.
    # Changing only one of them should not turn a real hardware profile into
    # Custom. Any actual processing change does.
    _HARDWARE_IDENTITY_METADATA_KEYS = frozenset({
        "hardware_profile_id",
        "hardware_mode",
        "palette_name",
        "palette_author",
        "palette_source",
        "palette_locks",
        "random_locks",
    })

    @classmethod
    def _hardware_identity_signature(cls, settings: ProcessingSettings) -> dict[str, Any]:
        data = settings.to_dict()
        for key in cls._HARDWARE_IDENTITY_METADATA_KEYS:
            data.pop(key, None)
        return data

    @contextmanager
    def _preserve_hardware_identity(self):
        depth = int(getattr(self, "_hardware_identity_preserve_depth", 0))
        self._hardware_identity_preserve_depth = depth + 1
        try:
            yield
        finally:
            self._hardware_identity_preserve_depth = depth

    def _replace_settings(
        self,
        settings: ProcessingSettings,
        *,
        schedule: bool = True,
        action: str | None = None,
        selected_layer: int | None = None,
        record_history: bool = True,
    ) -> bool:
        incoming = ProcessingSettings.from_dict(settings.to_dict())
        preserving = bool(getattr(self, "_hardware_identity_preserve_depth", 0))
        current = getattr(self, "settings", None)

        if not preserving and isinstance(current, ProcessingSettings):
            if self._hardware_identity_signature(incoming) != self._hardware_identity_signature(current):
                # A manual edit means the current pipeline is no longer an exact
                # named hardware profile. Keep every actual setting untouched and
                # change only the identity shown by the Hardware page.
                data = incoming.to_dict()
                data["hardware_profile_id"] = "custom"
                incoming = ProcessingSettings.from_dict(data)

        return super()._replace_settings(
            incoming,
            schedule=schedule,
            action=action,
            selected_layer=selected_layer,
            record_history=record_history,
        )

    @Slot(str, str, "QVariantMap")
    def applyHardware(self, profile_id: str, mode: str, options: dict[str, Any] | None = None) -> None:
        # Applying a named profile is intentional, so keep the profile ID written
        # by apply_profile_to_settings instead of classifying the operation as a
        # manual/custom edit.
        with self._preserve_hardware_identity():
            super().applyHardware(profile_id, mode, options)

    @Slot(str)
    def applyBuiltinPreset(self, preset_id: str) -> None:
        with self._preserve_hardware_identity():
            super().applyBuiltinPreset(preset_id)

    @Slot(str)
    def applyPreset(self, preset_id: str) -> None:
        # PreferencesBackend applies both built-ins and user-library presets.
        # The guard also covers its direct super().applyBuiltinPreset(...) call.
        with self._preserve_hardware_identity():
            super().applyPreset(preset_id)

    @Slot(str)
    def loadPreset(self, value: str) -> None:
        with self._preserve_hardware_identity():
            super().loadPreset(value)

    def _restore_history_state(self, state: dict[str, Any]) -> None:
        # Undo/redo restores the exact profile identity recorded in history.
        with self._preserve_hardware_identity():
            super()._restore_history_state(state)

    def _transparency_source(self) -> Image.Image | None:
        """Reload the original still image when it contains real alpha.

        The normal preview pipeline keeps an RGB working copy for speed. Export
        reopens the source so alpha is not lost just because preview rendering is
        RGB-only.
        """
        path = getattr(self, "_current_file", None)
        if path is None or getattr(self, "_video_path", None) is not None:
            return None
        try:
            with Image.open(path) as opened:
                if not image_has_transparency(opened):
                    return None
                return opened.convert("RGBA").copy()
        except Exception:
            return None

    def _source_has_transparency(self) -> bool:
        return self._transparency_source() is not None

    @staticmethod
    def _format_from_path(path: Path) -> str:
        return {
            ".png": "PNG",
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".webp": "WEBP",
            ".tif": "TIFF",
            ".tiff": "TIFF",
            ".svg": "SVG",
            ".txt": "TXT",
        }.get(path.suffix.lower(), "PNG")

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
            return {
                "sourceWidth": 1,
                "sourceHeight": 1,
                "width": 1,
                "height": 1,
                "hasTransparency": False,
                "hasAsciiLayer": False,
            }

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
            "hasTransparency": self._source_has_transparency(),
            "hasAsciiLayer": any(
                step.get("enabled", True) and step.get("kind") == "ASCII / Glyph"
                for step in normalize_effect_stack(animated.effect_stack, animated)
            ),
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
            "TXT": {".txt"},
        }.get(fmt, {suffix})
        if path.suffix.lower() not in accepted:
            path = path.with_suffix(suffix)
        return path

    @Slot(str)
    def exportImage(self, value: str) -> None:
        """Quick export; alpha-capable formats preserve source transparency automatically."""
        source = self._active_source()
        if source is None:
            return
        path = Path(_local_path(value))
        if not path.suffix:
            path = path.with_suffix(".png")
        format_name = self._format_from_path(path)
        alpha_source = self._transparency_source() if format_name in _ALPHA_FORMATS else None
        if alpha_source is None:
            super().exportImage(str(path))
            return

        animated = settings_at_time(self.settings, self._current_time)
        alpha_mask = prepare_transparency_mask(alpha_source, animated)
        context = {
            "path": str(path),
            "quick_alpha_export": True,
            "format": format_name,
            "alpha_mask": alpha_mask,
        }
        job = self._next_job()
        self._export_jobs.add(job)
        worker = ProcessingWorker(
            job,
            "export-image",
            alpha_source.copy(),
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
        self._set_status(f"Exporting {path.name}…")

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
        if format_name == "TXT":
            raster_source = prepare_raster_source(source, animated)
            grid = ascii_text_grid_for_stack(
                raster_source,
                animated.effect_stack,
                animated.palette,
                frame_time=self._current_time,
                frame_index=max(
                    0,
                    round(
                        self._current_time
                        * (self._video_info.fps if self._video_info else animated.animation_fps)
                    ),
                ),
            )
            if grid is None:
                self.errorOccurred.emit("Could not export text", "Add and enable an ASCII / Glyph layer first.")
                return
            try:
                path.write_text(grid, encoding="utf-8")
                self._set_status(f"Exported {path.name}")
            except Exception as exc:
                self.errorOccurred.emit("Could not export text", str(exc))
            return

        preserve_requested = bool(opts.get("preserveTransparency", True))
        alpha_source = (
            self._transparency_source()
            if preserve_requested and format_name in _ALPHA_FORMATS
            else None
        )
        source_for_worker = alpha_source if alpha_source is not None else source.copy()
        alpha_mask = (
            prepare_transparency_mask(alpha_source, animated)
            if alpha_source is not None
            else None
        )
        context = {
            "path": str(path),
            "advanced_export": True,
            "width": width,
            "height": height,
            "format": format_name,
            "quality": quality,
            "resampling": resampling,
            "preserve_transparency": alpha_mask is not None,
            "alpha_mask": alpha_mask,
        }
        job = self._next_job()
        self._export_jobs.add(job)
        worker = ProcessingWorker(
            job,
            "export-image",
            source_for_worker.copy(),
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
        resampling = str(
            opts.get("resampling", "Nearest (pixel-perfect)") or "Nearest (pixel-perfect)"
        ).strip()
        if resampling.upper() not in _RESAMPLING:
            resampling = "Nearest (pixel-perfect)"

        worker_options = {
            "format": format_name,
            "scalePercent": _clamp_scale_percent(opts.get("scalePercent", 100)),
            "overwrite": overwrite,
            "resampling": resampling,
            "preserveTransparency": bool(
                opts.get("preserveTransparency", True)
                and format_name in _BATCH_ALPHA_FORMATS
            ),
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
        alpha_mask = context.get("alpha_mask")
        if (
            bool(context.get("preserve_transparency"))
            and format_name in _ALPHA_FORMATS
            and isinstance(alpha_mask, Image.Image)
        ):
            mask = alpha_mask.convert("L")
            if mask.size != output.size:
                mask = mask.resize(output.size, Image.Resampling.NEAREST)
            existing_alpha = output.getchannel("A") if "A" in output.getbands() else None
            output = output.convert("RGBA")
            if existing_alpha is not None:
                if existing_alpha.size != mask.size:
                    existing_alpha = existing_alpha.resize(mask.size, Image.Resampling.NEAREST)
                mask = ImageChops.multiply(existing_alpha, mask)
            output.putalpha(mask)
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
            and bool(context.get("quick_alpha_export"))
        ):
            self._export_jobs.discard(job_id)
            path = Path(str(context.get("path", "output.png")))
            try:
                output = result.convert("RGBA")
                alpha_mask = context.get("alpha_mask")
                if isinstance(alpha_mask, Image.Image):
                    mask = alpha_mask.convert("L")
                    if mask.size != output.size:
                        mask = mask.resize(output.size, Image.Resampling.NEAREST)
                    existing_alpha = output.getchannel("A")
                    mask = ImageChops.multiply(existing_alpha, mask)
                    output.putalpha(mask)
                if path.suffix.lower() == ".svg":
                    save_svg(output, path)
                else:
                    output.save(path)
                self._set_status(f"Exported {path.name}")
            except Exception as exc:
                self.errorOccurred.emit("Could not export image", str(exc))
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
