from __future__ import annotations

import traceback

from PIL import Image
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from rastermint.core.processor import process_image
from rastermint.core.settings import ProcessingSettings


class WorkerSignals(QObject):
    finished = Signal(int, str, object, object)
    failed = Signal(int, str, str, object)


class ProcessingWorker(QRunnable):
    def __init__(
        self,
        job_id: int,
        purpose: str,
        image: Image.Image,
        settings: ProcessingSettings,
        context: object = None,
    ) -> None:
        super().__init__()
        self.job_id = job_id
        self.purpose = purpose
        self.image = image.copy()
        self.settings = ProcessingSettings.from_dict(settings.to_dict())
        self.context = context
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = process_image(self.image, self.settings)
            self.signals.finished.emit(self.job_id, self.purpose, result, self.context)
        except Exception:
            self.signals.failed.emit(
                self.job_id,
                self.purpose,
                traceback.format_exc(),
                self.context,
            )
