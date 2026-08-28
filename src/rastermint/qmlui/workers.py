# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from rastermint.core.settings import ProcessingSettings


class WorkerSignals(QObject):
    finished = Signal(int, str, object, object)
    failed = Signal(int, str, str, object)
    progress = Signal(int, str, int, int, str)


class ProcessingWorker(QRunnable):
    def __init__(
        self,
        job_id: int,
        purpose: str,
        image: Any,
        settings: ProcessingSettings,
        context: object = None,
        *,
        frame_time: float = 0.0,
        frame_index: int = 0,
        display_mode: str = "raw",
        include_grid: bool = False,
        temporal_state: Any | None = None,
        render_cache: Any | None = None,
        cache_context: str = "",
        tiled_processing: bool = True,
        tile_size: int = 1024,
    ) -> None:
        super().__init__()
        self.job_id = job_id
        self.purpose = purpose
        self.image = image
        self.settings = ProcessingSettings.from_dict(settings.to_dict())
        self.context = context
        self.frame_time = float(frame_time)
        self.frame_index = int(frame_index)
        self.display_mode = str(display_mode or "raw")
        self.include_grid = bool(include_grid)
        self.temporal_state = temporal_state
        self.render_cache = render_cache
        self.cache_context = str(cache_context or "")
        self.tiled_processing = bool(tiled_processing)
        self.tile_size = max(256, int(tile_size))
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            # NumPy/Pillow and the rendering pipeline are intentionally imported
            # only when a worker actually starts processing an image. Importing
            # the QML backend during application startup must stay lightweight.
            from rastermint.core.processor import process_image

            def progress(current: int, total: int, label: str) -> None:
                self.signals.progress.emit(
                    self.job_id,
                    self.purpose,
                    int(current),
                    int(total),
                    str(label or ""),
                )

            result = process_image(
                self.image,
                self.settings,
                frame_time=self.frame_time,
                frame_index=self.frame_index,
                display_mode=self.display_mode,
                include_grid=self.include_grid,
                temporal_state=self.temporal_state,
                render_cache=self.render_cache,
                cache_context=self.cache_context,
                tiled_processing=self.tiled_processing,
                tile_size=self.tile_size,
                progress_callback=progress,
            )
            self.signals.finished.emit(
                self.job_id, self.purpose, result, self.context
            )
        except Exception:
            self.signals.failed.emit(
                self.job_id, self.purpose, traceback.format_exc(), self.context
            )


class VideoCurrentFrameWorker(QRunnable):
    """Decode and fully process one source-video frame for still export."""

    def __init__(
        self,
        job_id: int,
        path: str,
        time_seconds: float,
        settings: ProcessingSettings,
        context: object = None,
    ) -> None:
        super().__init__()
        self.job_id = job_id
        self.path = path
        self.time_seconds = float(time_seconds)
        self.settings = ProcessingSettings.from_dict(settings.to_dict())
        self.context = context
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            from rastermint.core.media import render_processed_video_frame

            result = render_processed_video_frame(
                self.path,
                self.settings,
                self.time_seconds,
            )
            self.signals.finished.emit(
                self.job_id, "export-video-frame", result, self.context
            )
        except Exception:
            self.signals.failed.emit(
                self.job_id,
                "export-video-frame",
                traceback.format_exc(),
                self.context,
            )


class AudioEnvelopeWorker(QRunnable):
    def __init__(self, job_id: int, path: str, rate: float = 30.0) -> None:
        super().__init__()
        self.job_id = int(job_id)
        self.path = str(path)
        self.rate = float(rate)
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            from rastermint.core.audio import extract_audio_envelope
            envelope, rate = extract_audio_envelope(self.path, rate=self.rate)
            self.signals.finished.emit(self.job_id, "audio-envelope", {"envelope": envelope, "rate": rate}, self.path)
        except Exception:
            self.signals.failed.emit(self.job_id, "audio-envelope", traceback.format_exc(), self.path)


class BenchmarkWorker(QRunnable):
    def __init__(self, job_id: int, image: Any, settings: ProcessingSettings) -> None:
        super().__init__()
        self.job_id = int(job_id)
        self.image = image
        self.settings = ProcessingSettings.from_dict(settings.to_dict())
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            from rastermint.core.benchmark import benchmark_processing
            result = benchmark_processing(self.image, self.settings)
            self.signals.finished.emit(self.job_id, "benchmark", result, None)
        except Exception:
            self.signals.failed.emit(self.job_id, "benchmark", traceback.format_exc(), None)


class VideoFrameWorker(QRunnable):
    def __init__(
        self, job_id: int, path: str, time_seconds: float
    ) -> None:
        super().__init__()
        self.job_id = job_id
        self.path = path
        self.time_seconds = float(time_seconds)
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            from rastermint.core.media import read_video_frame

            frame = read_video_frame(self.path, self.time_seconds)
            self.signals.finished.emit(
                self.job_id, "video-frame", frame, self.time_seconds
            )
        except Exception:
            self.signals.failed.emit(
                self.job_id,
                "video-frame",
                traceback.format_exc(),
                self.time_seconds,
            )


class MediaExportWorker(QRunnable):
    def __init__(
        self,
        job_id: int,
        settings: ProcessingSettings,
        output: str,
        *,
        image: Any | None = None,
        video_path: str | None = None,
        include_audio: bool = True,
    ) -> None:
        super().__init__()
        self.job_id = job_id
        self.settings = ProcessingSettings.from_dict(settings.to_dict())
        self.output = output
        self.image = image
        self.video_path = video_path
        self.include_audio = include_audio
        self.signals = WorkerSignals()

    def _progress(self, current: int, total: int) -> None:
        self.signals.progress.emit(
            self.job_id,
            "media-export",
            current,
            total,
            Path(self.output).name,
        )

    @Slot()
    def run(self) -> None:
        try:
            if self.video_path:
                if Path(self.output).suffix.lower() == ".gif":
                    from rastermint.core.gif_export import export_processed_video_gif

                    result = export_processed_video_gif(
                        self.video_path,
                        self.settings,
                        self.output,
                        progress=self._progress,
                    )
                else:
                    from rastermint.core.media import export_processed_video

                    result = export_processed_video(
                        self.video_path,
                        self.settings,
                        self.output,
                        include_audio=self.include_audio,
                        progress=self._progress,
                    )
            elif self.image is not None:
                from rastermint.core.media import export_image_animation

                result = export_image_animation(
                    self.image,
                    self.settings,
                    self.output,
                    progress=self._progress,
                )
            else:
                raise ValueError(
                    "No image or video source for media export"
                )
            self.signals.finished.emit(
                self.job_id, "media-export", str(result), self.output
            )
        except Exception:
            self.signals.failed.emit(
                self.job_id,
                "media-export",
                traceback.format_exc(),
                self.output,
            )


class RenderedPreviewWorker(QRunnable):
    def __init__(
        self,
        job_id: int,
        settings: ProcessingSettings,
        *,
        image: Any | None = None,
        video_path: str | None = None,
        start_time: float = 0.0,
        duration: float = 5.0,
        max_side: int = 640,
        context: object = None,
    ) -> None:
        super().__init__()
        self.job_id = job_id
        self.settings = ProcessingSettings.from_dict(settings.to_dict())
        self.image = image
        self.video_path = video_path
        self.start_time = float(start_time)
        self.duration = float(duration)
        self.max_side = int(max_side)
        self.context = context
        self.signals = WorkerSignals()

    def _progress(self, current: int, total: int) -> None:
        self.signals.progress.emit(
            self.job_id,
            "rendered-preview",
            current,
            total,
            "frames",
        )

    @Slot()
    def run(self) -> None:
        try:
            if self.video_path:
                from rastermint.core.media import render_video_preview_frames

                frames, times, fps = render_video_preview_frames(
                    self.video_path,
                    self.settings,
                    start_time=self.start_time,
                    duration=self.duration,
                    max_side=self.max_side,
                    progress=self._progress,
                )
                source = "video"
            elif self.image is not None:
                from rastermint.core.media import render_image_preview_frames

                frames, times, fps = render_image_preview_frames(
                    self.image,
                    self.settings,
                    max_side=self.max_side,
                    progress=self._progress,
                )
                source = "image"
            else:
                raise ValueError("No source for rendered preview")
            result = {
                "frames": frames,
                "times": times,
                "fps": fps,
                "source": source,
            }
            self.signals.finished.emit(
                self.job_id,
                "rendered-preview",
                result,
                self.context,
            )
        except Exception:
            self.signals.failed.emit(
                self.job_id,
                "rendered-preview",
                traceback.format_exc(),
                self.context,
            )


class SequenceExportWorker(QRunnable):
    def __init__(
        self,
        job_id: int,
        settings: ProcessingSettings,
        output_dir: str,
        *,
        image: Any | None = None,
        video_path: str | None = None,
        prefix: str = "frame",
    ) -> None:
        super().__init__()
        self.job_id = job_id
        self.settings = ProcessingSettings.from_dict(settings.to_dict())
        self.output_dir = output_dir
        self.image = image
        self.video_path = video_path
        self.prefix = prefix
        self.signals = WorkerSignals()

    def _progress(self, current: int, total: int) -> None:
        self.signals.progress.emit(
            self.job_id,
            "png-sequence",
            current,
            total,
            Path(self.output_dir).name,
        )

    @Slot()
    def run(self) -> None:
        try:
            if self.video_path:
                from rastermint.core.media import export_processed_video_sequence

                written = export_processed_video_sequence(
                    self.video_path,
                    self.settings,
                    self.output_dir,
                    prefix=self.prefix,
                    progress=self._progress,
                )
            elif self.image is not None:
                from rastermint.core.media import export_image_sequence

                written = export_image_sequence(
                    self.image,
                    self.settings,
                    self.output_dir,
                    prefix=self.prefix,
                    progress=self._progress,
                )
            else:
                raise ValueError("No source for PNG sequence export")
            self.signals.finished.emit(
                self.job_id,
                "png-sequence",
                [str(p) for p in written],
                self.output_dir,
            )
        except Exception:
            self.signals.failed.emit(
                self.job_id,
                "png-sequence",
                traceback.format_exc(),
                self.output_dir,
            )


class BatchWorker(QRunnable):
    def __init__(
        self,
        job_id: int,
        paths: list[str],
        output_dir: str,
        settings: ProcessingSettings,
        options: dict[str, object] | None = None,
    ) -> None:
        super().__init__()
        self.job_id = job_id
        self.paths = paths
        self.output_dir = output_dir
        self.settings = ProcessingSettings.from_dict(settings.to_dict())
        self.options = dict(options or {})
        self.signals = WorkerSignals()

    def _progress(
        self, current: int, total: int, target: Path
    ) -> None:
        self.signals.progress.emit(
            self.job_id,
            "batch",
            current,
            total,
            target.name,
        )

    @Slot()
    def run(self) -> None:
        try:
            from rastermint.core.batch import process_batch

            written = process_batch(
                self.paths,
                self.output_dir,
                self.settings,
                progress=self._progress,
                format_name=self.options.get("format", "PNG"),
                scale_percent=self.options.get("scalePercent", 100),
                overwrite=self.options.get("overwrite", "auto-rename"),
                size_mode=self.options.get("sizeMode", "relative"),
                fixed_output_size=self.options.get("fixedOutputSize"),
            )
            self.signals.finished.emit(
                self.job_id,
                "batch",
                [str(p) for p in written],
                self.output_dir,
            )
        except Exception:
            self.signals.failed.emit(
                self.job_id,
                "batch",
                traceback.format_exc(),
                self.output_dir,
            )
