# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class AboutDialog(QDialog):
    def __init__(self, version: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About RasterMint")
        self.setModal(True)
        self.setMinimumWidth(360)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        title = QLabel(f"<b>RasterMint {version}</b>")
        title.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(title)

        text = QLabel(
            'Developed by Draconov · 2026<br>'
            'Official repository: '
            '<a href="https://github.com/Draconov/RasterMint">github.com/Draconov/RasterMint</a>'
        )
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        text.setOpenExternalLinks(True)
        text.setWordWrap(True)
        root.addWidget(text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
