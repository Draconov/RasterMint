# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QLabel, QWidget

from rastermint.core.settings import ProcessingSettings


class SourceTransformWidget(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._loading = False
        grid = QGridLayout(self); grid.setContentsMargins(0, 0, 0, 0)
        self.rotation = QComboBox()
        for label, value in [("0°", 0), ("90°", 90), ("180°", 180), ("270°", 270)]: self.rotation.addItem(label, value)
        self.rotation.currentIndexChanged.connect(self._emit)
        self.flip_h = QCheckBox("Flip H"); self.flip_v = QCheckBox("Flip V")
        self.flip_h.toggled.connect(self._emit); self.flip_v.toggled.connect(self._emit)
        grid.addWidget(QLabel("Rotate"), 0, 0); grid.addWidget(self.rotation, 0, 1); grid.addWidget(self.flip_h, 0, 2); grid.addWidget(self.flip_v, 0, 3)

        self.crop: dict[str, QDoubleSpinBox] = {}
        for col, (key, label) in enumerate([("left", "Left"), ("top", "Top"), ("right", "Right"), ("bottom", "Bottom")]):
            spin = QDoubleSpinBox(); spin.setRange(0.0, 49.0); spin.setDecimals(1); spin.setSuffix("%"); spin.setSingleStep(1.0); spin.valueChanged.connect(self._emit)
            self.crop[key] = spin
            grid.addWidget(QLabel(label), 1, col)
            grid.addWidget(spin, 2, col)

        self.pos_x = QDoubleSpinBox(); self.pos_x.setRange(-100.0, 100.0); self.pos_x.setSuffix("%"); self.pos_x.setValue(0); self.pos_x.valueChanged.connect(self._emit)
        self.pos_y = QDoubleSpinBox(); self.pos_y.setRange(-100.0, 100.0); self.pos_y.setSuffix("%"); self.pos_y.setValue(0); self.pos_y.valueChanged.connect(self._emit)
        grid.addWidget(QLabel("Fill position X"), 3, 0); grid.addWidget(self.pos_x, 3, 1); grid.addWidget(QLabel("Y"), 3, 2); grid.addWidget(self.pos_y, 3, 3)

    def _emit(self, *_args) -> None:
        if not self._loading: self.changed.emit()

    def apply_to_settings(self, settings: ProcessingSettings) -> None:
        settings.rotation = int(self.rotation.currentData() or 0)
        settings.flip_horizontal = self.flip_h.isChecked(); settings.flip_vertical = self.flip_v.isChecked()
        settings.crop_left = self.crop["left"].value() / 100.0; settings.crop_top = self.crop["top"].value() / 100.0
        settings.crop_right = self.crop["right"].value() / 100.0; settings.crop_bottom = self.crop["bottom"].value() / 100.0
        settings.position_x = self.pos_x.value() / 100.0; settings.position_y = self.pos_y.value() / 100.0

    def set_from_settings(self, settings: ProcessingSettings) -> None:
        self._loading = True
        try:
            idx = self.rotation.findData(settings.rotation); self.rotation.setCurrentIndex(max(0, idx))
            self.flip_h.setChecked(settings.flip_horizontal); self.flip_v.setChecked(settings.flip_vertical)
            self.crop["left"].setValue(settings.crop_left * 100); self.crop["top"].setValue(settings.crop_top * 100)
            self.crop["right"].setValue(settings.crop_right * 100); self.crop["bottom"].setValue(settings.crop_bottom * 100)
            self.pos_x.setValue(settings.position_x * 100); self.pos_y.setValue(settings.position_y * 100)
        finally: self._loading = False
