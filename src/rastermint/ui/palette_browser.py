# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from rastermint.core.palette_library import PaletteRecord, palette_categories, search_palettes


def palette_strip_icon(colors: tuple[str, ...] | list[str], width: int = 180, height: int = 28) -> QIcon:
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    count = max(1, len(colors))
    for i, color in enumerate(colors):
        x0 = round(i * width / count)
        x1 = round((i + 1) * width / count)
        painter.fillRect(x0, 0, max(1, x1 - x0), height, QColor(color))
    painter.end()
    return QIcon(pixmap)


class PaletteBrowserDialog(QDialog):
    palette_selected = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Palette Library")
        self.resize(610, 560)
        root = QVBoxLayout(self)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search palettes, systems, descriptions…")
        self.category = QComboBox()
        self.category.addItem("All")
        self.category.addItems(palette_categories())
        filters.addWidget(self.search, 1)
        filters.addWidget(self.category)
        root.addLayout(filters)

        self.list = QListWidget()
        self.list.setIconSize(QPixmap(180, 28).size())
        self.list.itemDoubleClicked.connect(lambda *_: self._accept_selected())
        self.list.currentItemChanged.connect(lambda *_: self._update_details())
        root.addWidget(self.list, 1)

        self.details = QLabel("Select a palette")
        self.details.setWordWrap(True)
        self.details.setMinimumHeight(62)
        root.addWidget(self.details)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.use_button = QPushButton("Use palette")
        self.use_button.clicked.connect(self._accept_selected)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(self.use_button)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

        self.search.textChanged.connect(self._rebuild)
        self.category.currentTextChanged.connect(self._rebuild)
        self._rebuild()

    def _rebuild(self, *_args) -> None:
        selected_id = self.current_palette().id if self.current_palette() else None
        self.list.clear()
        records = search_palettes(self.search.text(), self.category.currentText())
        for record in records:
            item = QListWidgetItem(palette_strip_icon(record.colors), f"{record.name}  ·  {len(record.colors)} colors")
            item.setData(Qt.ItemDataRole.UserRole, record)
            tooltip = f"{record.category} · {len(record.colors)} colors"
            if record.description:
                tooltip += f"\n{record.description}"
            item.setToolTip(tooltip)
            self.list.addItem(item)
            if selected_id and record.id == selected_id:
                self.list.setCurrentItem(item)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)
        self._update_details()

    def current_palette(self) -> PaletteRecord | None:
        item = self.list.currentItem()
        value = item.data(Qt.ItemDataRole.UserRole) if item else None
        return value if isinstance(value, PaletteRecord) else None

    def _update_details(self) -> None:
        record = self.current_palette()
        self.use_button.setEnabled(record is not None)
        if record is None:
            self.details.setText("No matching palettes")
            return
        text = f"{record.category} · {record.name} · {len(record.colors)} colors"
        if record.description:
            text += f"\n{record.description}"
        self.details.setText(text)

    def _accept_selected(self) -> None:
        record = self.current_palette()
        if record is None:
            return
        self.palette_selected.emit(record)
        self.accept()
