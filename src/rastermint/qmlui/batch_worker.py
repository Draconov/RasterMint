# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QRunnable, Slot

from rastermint.core.batch import process_batch
from rastermint.core.settings import ProcessingSettings

from .workers import WorkerSignals


class BatchWorker(QRunnable):
    """Run a still-image batch export with per-export sizing options."""

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

    def _progress(self, current: int, total: int, target: Path) -> None:
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
            written = process_batch(
                self.paths,
                self.output_dir,
                self.settings,
                progress=self._progress,
                format_name=self.options.get("format", "PNG"),
                scale_percent=self.options.get("scalePercent", 100),
                overwrite=self.options.get("overwrite", "auto-rename"),
                resampling=self.options.get(
                    "resampling", "Nearest (pixel-perfect)"
                ),
                preserve_transparency=bool(
                    self.options.get("preserveTransparency", True)
                ),
            )
            self.signals.finished.emit(
                self.job_id,
                "batch",
                [str(path) for path in written],
                self.output_dir,
            )
        except Exception:
            self.signals.failed.emit(
                self.job_id,
                "batch",
                traceback.format_exc(),
                self.output_dir,
            )
