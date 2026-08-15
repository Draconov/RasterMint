# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    preview_mode_requested = Signal(str)
    reset_requested = Signal()

    def __init__(self, preview_mode: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("RasterMint Settings")
        self.setModal(True)
        self.setMinimumWidth(390)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Application settings")
        title.setObjectName("dialogTitle")
        root.addWidget(title)

        form = QFormLayout()
        self.preview_mode = QComboBox()
        self.preview_mode.addItem("Quick", "live")
        self.preview_mode.addItem("Stable", "still")
        self.preview_mode.addItem("Full", "full")
        index = self.preview_mode.findData(preview_mode)
        self.preview_mode.setCurrentIndex(max(0, index))
        self.preview_mode.currentIndexChanged.connect(self._preview_changed)
        form.addRow("Preview render", self.preview_mode)
        root.addLayout(form)

        note = QLabel("Quick, Stable and Full keep the same renderer behavior used by the main inspector.")
        note.setWordWrap(True)
        note.setObjectName("sectionHint")
        root.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        reset = QPushButton("Reset Settings")
        reset.setObjectName("resetSettingsButton")
        reset.setToolTip("Restore RasterMint processing settings to their defaults")
        reset.clicked.connect(self._reset)
        root.addWidget(reset)

    def _preview_changed(self) -> None:
        self.preview_mode_requested.emit(str(self.preview_mode.currentData() or "live"))

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset RasterMint processing settings to their defaults?",
            QMessageBox.StandardButton.Reset | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Reset:
            self.reset_requested.emit()
            index = self.preview_mode.findData("live")
            self.preview_mode.setCurrentIndex(max(0, index))
