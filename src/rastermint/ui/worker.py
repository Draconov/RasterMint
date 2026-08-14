# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import traceback
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from rastermint.core.batch import process_batch
from rastermint.core.media import export_image_animation, export_processed_video, read_video_frame
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
    ) -> None:
        super().__init__()
        self.job_id = job_id
        self.purpose = purpose
        self.image = image
        self.settings = ProcessingSettings.from_dict(settings.to_dict())
        self.context = context
        self.frame_time = float(frame_time)
        self.frame_index = int(frame_index)
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = process_image(
                self.image,
                self.settings,
                frame_time=self.frame_time,
                frame_index=self.frame_index,
            )
            self.signals.finished.emit(self.job_id, self.purpose, result, self.context)
        except Exception:
            self.signals.failed.emit(self.job_id, self.purpose, traceback.format_exc(), self.context)


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
