# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget

from rastermint.core.builtin_presets import BUILTIN_PRESETS


class PresetGallery(QWidget):
    preset_selected = Signal(str)
    refresh_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(4)
        nav = QHBoxLayout(); nav.setContentsMargins(0, 0, 0, 0)
        self.prev_button = QPushButton("‹"); self.prev_button.setFixedWidth(30); self.prev_button.setToolTip("Previous presets")
        self.refresh_button = QPushButton("↻"); self.refresh_button.setFixedWidth(30); self.refresh_button.setToolTip("Regenerate thumbnails from the current source image")
        self.next_button = QPushButton("›"); self.next_button.setFixedWidth(30); self.next_button.setToolTip("Next presets")
        nav.addWidget(self.prev_button); nav.addWidget(self.refresh_button); nav.addStretch(1); nav.addWidget(self.next_button)
        root.addLayout(nav)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget(); self.row = QHBoxLayout(host); self.row.setContentsMargins(0, 0, 0, 0); self.row.setSpacing(8); self.row.addStretch(1)
        self.scroll.setWidget(host)
        root.addWidget(self.scroll)

        self.buttons: dict[str, QToolButton] = {}
        for index, preset in enumerate(BUILTIN_PRESETS):
            button = QToolButton()
            button.setText(preset.name)
            button.setToolTip(preset.description)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIconSize(QPixmap(116, 78).size())
            button.setFixedSize(126, 112)
            button.clicked.connect(lambda _=False, pid=preset.id: self.preset_selected.emit(pid))
            self.row.insertWidget(index, button)
            self.buttons[preset.id] = button

        self.prev_button.clicked.connect(lambda: self._scroll(-240))
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.next_button.clicked.connect(lambda: self._scroll(240))

    def _scroll(self, delta: int) -> None:
        bar = self.scroll.horizontalScrollBar()
        bar.setValue(max(bar.minimum(), min(bar.maximum(), bar.value() + delta)))

    def set_thumbnail(self, preset_id: str, pixmap: QPixmap) -> None:
        button = self.buttons.get(preset_id)
        if button is not None:
            button.setIcon(QIcon(pixmap))
