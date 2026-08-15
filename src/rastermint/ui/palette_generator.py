# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from rastermint.core.palette_library import interpolate_palette
from rastermint.ui.palette_browser import palette_strip_icon


class PaletteGeneratorDialog(QDialog):
    palette_generated = Signal(list, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Palette Interpolation")
        self.resize(470, 280)
        self.start_color = "#163B2A"
        self.end_color = "#F1E66B"

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.start_button = QPushButton(self.start_color)
        self.end_button = QPushButton(self.end_color)
        self.start_button.clicked.connect(lambda: self._choose_color(True))
        self.end_button.clicked.connect(lambda: self._choose_color(False))
        self.count = QSpinBox(); self.count.setRange(2, 256); self.count.setValue(8)
        self.space = QComboBox(); self.space.addItems(["OKLab", "RGB", "Linear RGB", "HSV", "HSL"])
        form.addRow("Start", self.start_button)
        form.addRow("End", self.end_button)
        form.addRow("Colors", self.count)
        form.addRow("Interpolation", self.space)
        root.addLayout(form)

        self.preview = QLabel()
        self.preview.setMinimumHeight(44)
        root.addWidget(self.preview)
        hint = QLabel("OKLab usually gives the most even-looking perceptual ramp. RGB/HSV/HSL are available for stylized transitions.")
        hint.setWordWrap(True)
        root.addWidget(hint)

        buttons = QHBoxLayout(); buttons.addStretch(1)
        use = QPushButton("Use palette"); use.clicked.connect(self._use)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        buttons.addWidget(use); buttons.addWidget(cancel); root.addLayout(buttons)

        self.count.valueChanged.connect(self._refresh)
        self.space.currentTextChanged.connect(self._refresh)
        self._refresh()

    def _choose_color(self, start: bool) -> None:
        current = self.start_color if start else self.end_color
        chosen = QColorDialog.getColor(QColor(current), self, "Choose color")
        if not chosen.isValid():
            return
        value = chosen.name(QColor.NameFormat.HexRgb).upper()
        if start:
            self.start_color = value; self.start_button.setText(value)
        else:
            self.end_color = value; self.end_button.setText(value)
        self._refresh()

    def colors(self) -> list[str]:
        return interpolate_palette(self.start_color, self.end_color, self.count.value(), self.space.currentText())

    def _refresh(self, *_args) -> None:
        colors = self.colors()
        self.preview.setPixmap(palette_strip_icon(colors, 420, 38).pixmap(420, 38))

    def _use(self) -> None:
        colors = self.colors()
        name = f"{self.space.currentText()} {len(colors)}-color ramp"
        self.palette_generated.emit(colors, name)
        self.accept()
