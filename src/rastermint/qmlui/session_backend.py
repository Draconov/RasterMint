# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Crash-recovery autosaves and independent reference-image state."""

from __future__ import annotations

import hashlib
import json
import os
import traceback
from pathlib import Path

from PySide6.QtCore import Property, QRunnable, QStandardPaths, QTimer, Signal, Slot, Qt
from PySide6.QtGui import QImage

from rastermint.core.project import save_project_file
from .backend import _local_path, _pil_to_qimage
from .preferences_backend import RasterMintBackend as PreferencesBackend
from .workers import WorkerSignals


class ProjectAutosaveWorker(QRunnable):
    """Package autosave assets without blocking QML's event loop."""

    def __init__(self, temp_path: Path, payload: dict, digest: str):
        super().__init__()
        self.temp_path = Path(temp_path)
        self.payload = payload
        self.digest = digest
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            save_project_file(self.temp_path, self.payload, package_assets=True)
            self.signals.finished.emit(0, "autosave", str(self.temp_path), self.digest)
        except Exception:
            self.signals.failed.emit(0, "autosave", traceback.format_exc(), self.digest)


class RasterMintBackend(PreferencesBackend):
    referenceChanged = Signal()
    recoveryChanged = Signal()

    def __init__(self, image_provider):
        super().__init__(image_provider)
        location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self._session_dir = (Path(location) if location else Path.home() / ".rastermint") / "sessions"
        self._session_dir.mkdir(parents=True, exist_ok=True)
        self._project_asset_cache = self._session_dir / "extracted-assets"
        self._recovery_path = self._session_dir / "autosave.rastermint"
        self._recovery_pending = self._recovery_path.is_file()
        self._autosave_last_digest = ""
        self._autosave_error_reported = False
        self._autosave_running = False
        self._autosave_shutdown = False
        self._autosave_pending_path = self._session_dir / "autosave.pending.rastermint"
        self._autosave_pending_path.unlink(missing_ok=True)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(45000)
        self._autosave_timer.timeout.connect(self._autosave_checkpoint)
        self._autosave_timer.start()

        self._reference_visible = str(self.app_settings.value("referenceVisible", "false")).lower() in {"true", "1", "yes"}
        # A reference is now a live view of the imported source or the current
        # video frame, not an independently selected picture. Keep the legacy
        # path API for older project files, without loading a stale reference
        # from application preferences on a new session.
        self._reference_path = ""
        self._reference_revision = 0
        self._reference_width = 0
        self._reference_height = 0
        self._reference_source_object = None
        self.sourceChanged.connect(self._sync_current_source_reference)
        self._sync_current_source_reference()

    @Property(bool, notify=recoveryChanged)
    def recoveryAvailable(self) -> bool:
        return self._recovery_pending and self._recovery_path.is_file()

    @Slot()
    def discardAutosave(self) -> None:
        self._recovery_pending = False
        self._autosave_last_digest = ""
        self._recovery_path.unlink(missing_ok=True)
        self.recoveryChanged.emit()

    @Slot()
    def recoverAutosave(self) -> None:
        if not self.recoveryAvailable:
            return
        try:
            from rastermint.core.project import load_project_file
            recovered = load_project_file(self._recovery_path)
            previous = str((recovered.get("autosave_session") or {}).get("project_path", ""))
            # Preserve autosave until the data has been successfully loaded.
            self.loadProject(str(self._recovery_path))
            if self._project_path != self._recovery_path:
                raise RuntimeError("Autosaved project could not be loaded")
            if previous:
                self._project_path = Path(previous)
            else:
                self._project_path = None
            self.projectChanged.emit()
            # Keep the snapshot until a new periodic autosave replaces it.
            # Another crash immediately after recovery must still be recoverable.
            self._recovery_pending = False
            self._autosave_last_digest = ""
            self.recoveryChanged.emit()
        except Exception as exc:
            self.errorOccurred.emit("Could not recover project", str(exc))

    def _autosave_checkpoint(self) -> None:
        if self._autosave_shutdown or self._recovery_pending or self._autosave_running or not (self.hasSource or self._project_path is not None):
            return
        try:
            payload = self._project_payload()
            payload["autosave_session"] = {
                "project_path": str(self._project_path) if self._project_path else "",
                "automatic": True,
            }
            serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            if digest == self._autosave_last_digest:
                return
            self._autosave_running = True
            worker = ProjectAutosaveWorker(self._autosave_pending_path, payload, digest)
            worker.signals.finished.connect(self._autosave_finished)
            worker.signals.failed.connect(self._autosave_failed)
            self.thread_pool.start(worker, -1)
        except Exception as exc:
            self._autosave_running = False
            self._report_autosave_error(str(exc))

    @Slot(int, str, object, object)
    def _autosave_finished(self, job_id: int, purpose: str, result: object, digest: object) -> None:
        del job_id, purpose
        self._autosave_running = False
        try:
            if not self._autosave_shutdown and not self._recovery_pending:
                os.replace(str(result), self._recovery_path)
                self._autosave_last_digest = str(digest)
                self._autosave_error_reported = False
            else:
                Path(str(result)).unlink(missing_ok=True)
        except Exception as exc:
            self._report_autosave_error(str(exc))

    @Slot(int, str, str, object)
    def _autosave_failed(self, job_id: int, purpose: str, trace: str, digest: object) -> None:
        del job_id, purpose, digest
        self._autosave_running = False
        self._autosave_pending_path.unlink(missing_ok=True)
        self._report_autosave_error(trace.strip().splitlines()[-1] if trace.strip() else "Unknown error")

    def _report_autosave_error(self, reason: str) -> None:
        if not self._autosave_shutdown and not self._autosave_error_reported:
            self._autosave_error_reported = True
            self.errorOccurred.emit("Autosave failed", reason)

    @Property(bool, notify=referenceChanged)
    def referenceVisible(self) -> bool:
        return self._reference_visible

    @Property(str, notify=referenceChanged)
    def referenceImagePath(self) -> str:
        return self._reference_path

    @Property(int, notify=referenceChanged)
    def referenceRevision(self) -> int:
        return self._reference_revision

    @Property(int, notify=referenceChanged)
    def referenceWidth(self) -> int:
        return self._reference_width

    @Property(int, notify=referenceChanged)
    def referenceHeight(self) -> int:
        return self._reference_height

    @Property(str, notify=referenceChanged)
    def referenceSourceName(self) -> str:
        if self._active_source() is not None and self._current_file is not None:
            return self._current_file.name
        return ""

    @Slot(bool)
    def setReferenceVisible(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled != self._reference_visible:
            self._reference_visible = enabled
            self.app_settings.setValue("referenceVisible", enabled)
            if enabled:
                self._sync_current_source_reference()
            else:
                self._reference_source_object = None
            self.referenceChanged.emit()

    @Slot()
    def _sync_current_source_reference(self) -> None:
        """Show the real source image/frame, independent from effect rendering."""
        source = self._active_source()
        if source is None:
            # Clear immediately when switching to an empty document; otherwise
            # the previous image would remain displayed as the reference.
            if self._reference_width or self._reference_height or self._reference_source_object is not None:
                self.provider.clear("reference")
                self._reference_width = 0
                self._reference_height = 0
                self._reference_source_object = None
                self._reference_revision += 1
                self.referenceChanged.emit()
            return
        if not self._reference_visible:
            self._reference_source_object = None
            return
        if source is self._reference_source_object:
            return
        # Rendering a 4K frame to the reference every video frame is wasteful.
        # Bound the UI thumbnail, while retaining the original source aspect.
        preview = source
        if max(source.width, source.height) > 2048:
            from PIL import Image
            preview = source.copy()
            preview.thumbnail((2048, 2048), Image.Resampling.BILINEAR)
        self.provider.set_image("reference", _pil_to_qimage(preview))
        self._reference_source_object = source
        self._reference_width = int(source.width)
        self._reference_height = int(source.height)
        self._reference_revision += 1
        self.referenceChanged.emit()

    def _load_reference_image(self, path: Path, *, persist: bool = True) -> None:
        image = QImage(str(path))
        if image.isNull():
            raise ValueError("Selected file is not a readable image")
        if max(image.width(), image.height()) > 2048:
            image = image.scaled(2048, 2048, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.provider.set_image("reference", image)
        self._reference_path = str(path)
        self._reference_width = image.width()
        self._reference_height = image.height()
        self._reference_source_object = None
        self._reference_revision += 1
        if persist:
            self.app_settings.setValue("referenceImagePath", str(path))
            self._reference_visible = True
            self.app_settings.setValue("referenceVisible", True)
        self.referenceChanged.emit()
        # Old project files can still provide a separate reference asset, but
        # while editing a source the floating panel always follows that source.
        if self._active_source() is not None:
            self._sync_current_source_reference()

    @Slot(str)
    def openReferenceImage(self, value: str) -> None:
        try:
            path = Path(_local_path(value)).expanduser().resolve()
            self._load_reference_image(path)
        except Exception as exc:
            self.errorOccurred.emit("Could not open reference image", str(exc))

    @Slot()
    def clearReferenceImage(self) -> None:
        self.provider.clear("reference")
        self._reference_path = ""
        self._reference_width = 0
        self._reference_height = 0
        self._reference_source_object = None
        self._reference_revision += 1
        self.app_settings.remove("referenceImagePath")
        self.referenceChanged.emit()
        self._sync_current_source_reference()

    @Slot()
    def shutdown(self) -> None:
        if hasattr(self, "_autosave_timer"):
            self._autosave_shutdown = True
            self._autosave_timer.stop()
            if not self._recovery_pending:
                self._recovery_path.unlink(missing_ok=True)
        super().shutdown()
