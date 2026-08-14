# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from rastermint.core.palette import rgb_to_hex


class PaletteEditor(QWidget):
    palette_changed = Signal(list)

    def __init__(self, colors: list[str] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._colors = list(colors or ["#0B1020", "#F3F7FF"])
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(5)
        self._rebuild()

    def colors(self) -> list[str]:
        return self._colors.copy()

    def set_colors(self, colors: list[str], emit: bool = True) -> None:
        if not colors:
            return
        self._colors = list(colors[:32])
        self._rebuild()
        if emit:
            self.palette_changed.emit(self.colors())

    def _rebuild(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for i, color in enumerate(self._colors):
            button = QPushButton()
            button.setToolTip(f"{i + 1}: {color} — click to edit")
            button.setFixedSize(28, 28)
            button.setStyleSheet(
                f"QPushButton {{ background: {color}; border: 1px solid #697180; border-radius: 4px; }}"
                "QPushButton:hover { border: 2px solid #FFFFFF; }"
            )
            button.clicked.connect(lambda _=False, idx=i: self._edit_color(idx))
            self._layout.addWidget(button)

        add = QPushButton("+")
        add.setToolTip("Add color")
        add.setFixedSize(28, 28)
        add.clicked.connect(self._add_color)
        add.setEnabled(len(self._colors) < 32)
        self._layout.addWidget(add)

        remove = QPushButton("−")
        remove.setToolTip("Remove last color")
        remove.setFixedSize(28, 28)
        remove.clicked.connect(self._remove_color)
        remove.setEnabled(len(self._colors) > 1)
        self._layout.addWidget(remove)
        self._layout.addStretch(1)

    def _edit_color(self, index: int) -> None:
        initial = QColor(self._colors[index])
        chosen = QColorDialog.getColor(initial, self, "Choose palette color")
        if chosen.isValid():
            self._colors[index] = chosen.name(QColor.NameFormat.HexRgb).upper()
            self._rebuild()
            self.palette_changed.emit(self.colors())

    def _add_color(self) -> None:
        if len(self._colors) >= 32:
            return
        initial = QColor(self._colors[-1] if self._colors else "#FFFFFF")
        chosen = QColorDialog.getColor(initial, self, "Add palette color")
        if chosen.isValid():
            self._colors.append(chosen.name(QColor.NameFormat.HexRgb).upper())
            self._rebuild()
            self.palette_changed.emit(self.colors())

    def _remove_color(self) -> None:
        if len(self._colors) > 1:
            self._colors.pop()
            self._rebuild()
            self.palette_changed.emit(self.colors())
