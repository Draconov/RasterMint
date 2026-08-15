# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QStackedWidget, QWidget


class InspectorSidebar(QWidget):
    """Two-column inspector: category list on the left, detail page on the right."""

    page_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._keys: list[str] = []

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(1)

        self.nav = QListWidget()
        self.nav.setObjectName("inspectorNav")
        self.nav.setFixedWidth(142)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav.currentRowChanged.connect(self._row_changed)

        self.stack = QStackedWidget()
        self.stack.setObjectName("inspectorDetails")

        root.addWidget(self.nav)
        root.addWidget(self.stack, 1)

    def add_page(self, key: str, label: str, widget: QWidget) -> None:
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setToolTip(label)
        self.nav.addItem(item)
        self.stack.addWidget(widget)
        self._keys.append(key)
        if self.nav.count() == 1:
            self.nav.setCurrentRow(0)

    def set_current(self, key: str) -> None:
        for row, value in enumerate(self._keys):
            if value == key:
                self.nav.setCurrentRow(row)
                return

    def current_key(self) -> str:
        row = self.nav.currentRow()
        return self._keys[row] if 0 <= row < len(self._keys) else ""

    def _row_changed(self, row: int) -> None:
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)
            self.page_changed.emit(self._keys[row])
