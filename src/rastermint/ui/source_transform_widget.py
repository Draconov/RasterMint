# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDoubleSpinBox, QGridLayout, QLabel, QWidget

from rastermint.core.settings import ProcessingSettings


class SourceTransformWidget(QWidget):
    """Detailed source framing controls.

    Rotation, flip and interactive mirroring now live directly in the Edit
    menu. This inspector intentionally keeps crop and fill-position controls so
    the same image-manipulation actions are not duplicated in two places.
    """

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._loading = False
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)

        self.crop: dict[str, QDoubleSpinBox] = {}
        for col, (key, label) in enumerate(
            [("left", "Left"), ("top", "Top"), ("right", "Right"), ("bottom", "Bottom")]
        ):
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 49.0)
            spin.setDecimals(1)
            spin.setSuffix("%")
            spin.setSingleStep(1.0)
            spin.valueChanged.connect(self._emit)
            self.crop[key] = spin
            grid.addWidget(QLabel(label), 0, col)
            grid.addWidget(spin, 1, col)

        self.pos_x = QDoubleSpinBox()
        self.pos_x.setRange(-100.0, 100.0)
        self.pos_x.setSuffix("%")
        self.pos_x.setValue(0)
        self.pos_x.valueChanged.connect(self._emit)
        self.pos_y = QDoubleSpinBox()
        self.pos_y.setRange(-100.0, 100.0)
        self.pos_y.setSuffix("%")
        self.pos_y.setValue(0)
        self.pos_y.valueChanged.connect(self._emit)
        grid.addWidget(QLabel("Fill position X"), 2, 0)
        grid.addWidget(self.pos_x, 2, 1)
        grid.addWidget(QLabel("Y"), 2, 2)
        grid.addWidget(self.pos_y, 2, 3)

    def _emit(self, *_args) -> None:
        if not self._loading:
            self.changed.emit()

    def apply_to_settings(self, settings: ProcessingSettings) -> None:
        settings.crop_left = self.crop["left"].value() / 100.0
        settings.crop_top = self.crop["top"].value() / 100.0
        settings.crop_right = self.crop["right"].value() / 100.0
        settings.crop_bottom = self.crop["bottom"].value() / 100.0
        settings.position_x = self.pos_x.value() / 100.0
        settings.position_y = self.pos_y.value() / 100.0

    def set_from_settings(self, settings: ProcessingSettings) -> None:
        self._loading = True
        try:
            self.crop["left"].setValue(settings.crop_left * 100)
            self.crop["top"].setValue(settings.crop_top * 100)
            self.crop["right"].setValue(settings.crop_right * 100)
            self.crop["bottom"].setValue(settings.crop_bottom * 100)
            self.pos_x.setValue(settings.position_x * 100)
            self.pos_y.setValue(settings.position_y * 100)
        finally:
            self._loading = False
