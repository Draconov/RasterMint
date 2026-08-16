# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import traceback
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from rastermint.core.batch import process_batch
from rastermint.core.media import (
    export_image_animation,
    export_image_sequence,
    export_processed_video,
    export_processed_video_sequence,
    read_video_frame,
    probe_video,
    render_image_preview_frames,
    render_video_preview_frames,
)
from rastermint.core.animation import settings_at_time
from rastermint.core.processor import process_image
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
        image: Image.Image,
        settings: ProcessingSettings,
        context: object = None,
        *,
        frame_time: float = 0.0,
        frame_index: int = 0,
        display_mode: str = "raw",
        include_grid: bool = False,
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
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = process_image(
                self.image,
                self.settings,
                frame_time=self.frame_time,
                frame_index=self.frame_index,
                display_mode=self.display_mode,
                include_grid=self.include_grid,
            )
            self.signals.finished.emit(self.job_id, self.purpose, result, self.context)
        except Exception:
            self.signals.failed.emit(self.job_id, self.purpose, traceback.format_exc(), self.context)


class VideoCurrentFrameWorker(QRunnable):
    """Decode and fully process one source-video frame for still export."""

    def __init__(self, job_id: int, path: str, time_seconds: float, settings: ProcessingSettings, context: object = None) -> None:
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
            source = read_video_frame(self.path, self.time_seconds)
            animated = settings_at_time(self.settings, self.time_seconds)
            info = probe_video(self.path)
            frame_index = max(0, round(self.time_seconds * max(1.0, info.fps)))
            result = process_image(
                source,
                animated,
                frame_time=self.time_seconds,
                frame_index=frame_index,
                display_mode=animated.display_mode if animated.display_export else "raw",
                include_grid=animated.grid_enabled and animated.grid_export,
            )
            self.signals.finished.emit(self.job_id, "export-video-frame", result, self.context)
        except Exception:
            self.signals.failed.emit(self.job_id, "export-video-frame", traceback.format_exc(), self.context)


class VideoFrameWorker(QRunnable):
    def __init__(self, job_id: int, path: str, time_seconds: float) -> None:
        super().__init__()
        self.job_id = job_id
        self.path = path
        self.time_seconds = float(time_seconds)
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            frame = read_video_frame(self.path, self.time_seconds)
            self.signals.finished.emit(self.job_id, "video-frame", frame, self.time_seconds)
        except Exception:
            self.signals.failed.emit(self.job_id, "video-frame", traceback.format_exc(), self.time_seconds)


class MediaExportWorker(QRunnable):
    def __init__(
        self,
        job_id: int,
        settings: ProcessingSettings,
        output: str,
        *,
        image: Image.Image | None = None,
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
        self.signals.progress.emit(self.job_id, "media-export", current, total, Path(self.output).name)

    @Slot()
    def run(self) -> None:
        try:
            if self.video_path:
                result = export_processed_video(
                    self.video_path,
                    self.settings,
                    self.output,
                    include_audio=self.include_audio,
                    progress=self._progress,
                )
            elif self.image is not None:
                result = export_image_animation(
                    self.image,
                    self.settings,
                    self.output,
                    progress=self._progress,
                )
            else:
                raise ValueError("No image or video source for media export")
            self.signals.finished.emit(self.job_id, "media-export", str(result), self.output)
        except Exception:
            self.signals.failed.emit(self.job_id, "media-export", traceback.format_exc(), self.output)


class RenderedPreviewWorker(QRunnable):
    def __init__(
        self,
        job_id: int,
        settings: ProcessingSettings,
        *,
        image: Image.Image | None = None,
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
        self.signals.progress.emit(self.job_id, "rendered-preview", current, total, "frames")

    @Slot()
    def run(self) -> None:
        try:
            if self.video_path:
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
                frames, times, fps = render_image_preview_frames(
                    self.image,
                    self.settings,
                    max_side=self.max_side,
                    progress=self._progress,
                )
                source = "image"
            else:
                raise ValueError("No source for rendered preview")
            result = {"frames": frames, "times": times, "fps": fps, "source": source}
            self.signals.finished.emit(self.job_id, "rendered-preview", result, self.context)
        except Exception:
            self.signals.failed.emit(self.job_id, "rendered-preview", traceback.format_exc(), self.context)


class SequenceExportWorker(QRunnable):
    def __init__(
        self,
        job_id: int,
        settings: ProcessingSettings,
        output_dir: str,
        *,
        image: Image.Image | None = None,
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
        self.signals.progress.emit(self.job_id, "png-sequence", current, total, Path(self.output_dir).name)

    @Slot()
    def run(self) -> None:
        try:
            if self.video_path:
                written = export_processed_video_sequence(
                    self.video_path, self.settings, self.output_dir, prefix=self.prefix, progress=self._progress
                )
            elif self.image is not None:
                written = export_image_sequence(
                    self.image, self.settings, self.output_dir, prefix=self.prefix, progress=self._progress
                )
            else:
                raise ValueError("No source for PNG sequence export")
            self.signals.finished.emit(self.job_id, "png-sequence", [str(p) for p in written], self.output_dir)
        except Exception:
            self.signals.failed.emit(self.job_id, "png-sequence", traceback.format_exc(), self.output_dir)


class BatchWorker(QRunnable):
    def __init__(self, job_id: int, paths: list[str], output_dir: str, settings: ProcessingSettings) -> None:
        super().__init__()
        self.job_id = job_id
        self.paths = paths
        self.output_dir = output_dir
        self.settings = ProcessingSettings.from_dict(settings.to_dict())
        self.signals = WorkerSignals()

    def _progress(self, current: int, total: int, target: Path) -> None:
        self.signals.progress.emit(self.job_id, "batch", current, total, target.name)

    @Slot()
    def run(self) -> None:
        try:
            written = process_batch(self.paths, self.output_dir, self.settings, progress=self._progress)
            self.signals.finished.emit(self.job_id, "batch", [str(p) for p in written], self.output_dir)
        except Exception:
            self.signals.failed.emit(self.job_id, "batch", traceback.format_exc(), self.output_dir)
