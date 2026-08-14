# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import colorsys
import random

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QGridLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class PaletteEditor(QWidget):
    palette_changed = Signal(list)
    locks_changed = Signal(list)

    def __init__(self, colors: list[str] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._colors = list(colors or ["#0B1020", "#F3F7FF"])
        self._locks = [False] * len(self._colors)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(4)
        root.addLayout(self._grid)
        self._rebuild()

    def colors(self) -> list[str]:
        return self._colors.copy()

    def locks(self) -> list[bool]:
        return self._locks.copy()

    def set_colors(self, colors: list[str], locks: list[bool] | None = None, emit: bool = True) -> None:
        if not colors:
            return
        self._colors = list(colors[:256])
        if locks is None:
            self._locks = [False] * len(self._colors)
        else:
            self._locks = [bool(v) for v in locks[: len(self._colors)]]
            self._locks.extend([False] * (len(self._colors) - len(self._locks)))
        self._rebuild()
        if emit:
            self.palette_changed.emit(self.colors())
            self.locks_changed.emit(self.locks())

    def shuffle_unlocked(self) -> None:
        indexes = [i for i, locked in enumerate(self._locks) if not locked]
        values = [self._colors[i] for i in indexes]
        random.shuffle(values)
        for i, value in zip(indexes, values, strict=False):
            self._colors[i] = value
        self._rebuild()
        self.palette_changed.emit(self.colors())

    def randomize_unlocked(self) -> None:
        for i, locked in enumerate(self._locks):
            if locked:
                continue
            hue = random.random()
            saturation = random.uniform(0.45, 1.0)
            value = random.uniform(0.35, 1.0)
            r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
            self._colors[i] = f"#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"
        self._rebuild()
        self.palette_changed.emit(self.colors())

    def _rebuild(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        columns = 8
        for i, color in enumerate(self._colors):
            button = QPushButton("🔒" if self._locks[i] else "")
            button.setToolTip(
                f"{i + 1}: {color}\nClick: edit color\nRight-click: {'unlock' if self._locks[i] else 'lock'} color"
            )
            button.setFixedSize(30, 30)
            border = "2px solid #FFD166" if self._locks[i] else "1px solid #697180"
            button.setStyleSheet(
                f"QPushButton {{ background: {color}; border: {border}; border-radius: 4px; color: white; }}"
                "QPushButton:hover { border: 2px solid #FFFFFF; }"
            )
            button.clicked.connect(lambda _=False, idx=i: self._edit_color(idx))
            button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            button.customContextMenuRequested.connect(lambda _pos, idx=i: self._toggle_lock(idx))
            self._grid.addWidget(button, i // columns, i % columns)

        row = (len(self._colors) + columns - 1) // columns
        add = QPushButton("+")
        add.setToolTip("Add color")
        add.clicked.connect(self._add_color)
        add.setEnabled(len(self._colors) < 256)
        remove = QPushButton("−")
        remove.setToolTip("Remove last unlocked color")
        remove.clicked.connect(self._remove_color)
        remove.setEnabled(len(self._colors) > 1)
        self._grid.addWidget(add, row, 0)
        self._grid.addWidget(remove, row, 1)

    def _toggle_lock(self, index: int) -> None:
        self._locks[index] = not self._locks[index]
        self._rebuild()
        self.locks_changed.emit(self.locks())

    def _edit_color(self, index: int) -> None:
        initial = QColor(self._colors[index])
        chosen = QColorDialog.getColor(initial, self, "Choose palette color")
        if chosen.isValid():
            self._colors[index] = chosen.name(QColor.NameFormat.HexRgb).upper()
            self._rebuild()
            self.palette_changed.emit(self.colors())

    def _add_color(self) -> None:
        if len(self._colors) >= 256:
            return
        initial = QColor(self._colors[-1] if self._colors else "#FFFFFF")
        chosen = QColorDialog.getColor(initial, self, "Add palette color")
        if chosen.isValid():
            self._colors.append(chosen.name(QColor.NameFormat.HexRgb).upper())
            self._locks.append(False)
            self._rebuild()
            self.palette_changed.emit(self.colors())
            self.locks_changed.emit(self.locks())

    def _remove_color(self) -> None:
        if len(self._colors) <= 1:
            return
        index = next((i for i in range(len(self._colors) - 1, -1, -1) if not self._locks[i]), None)
        if index is None:
            return
        self._colors.pop(index)
        self._locks.pop(index)
        self._rebuild()
        self.palette_changed.emit(self.colors())
        self.locks_changed.emit(self.locks())
