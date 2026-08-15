# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout


class SettingsDialog(QDialog):
    """Small placeholder for future application-wide preferences."""

    reset_requested = Signal()

    def __init__(self, parent=None) -> None:
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
        root.addStretch(1)

        reset = QPushButton("Reset Settings")
        reset.setObjectName("resetSettingsButton")
        reset.setToolTip("Restore RasterMint processing settings to their defaults")
        reset.clicked.connect(self._reset)
        root.addWidget(reset)

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
