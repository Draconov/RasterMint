# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from rastermint.core.settings import ProcessingSettings


RASTER_PRESETS = [
    ("Custom", None),
    ("Game Boy · 160 × 144", (160, 144)),
    ("GBA · 240 × 160", (240, 160)),
    ("SNES · 256 × 224", (256, 224)),
    ("NES · 256 × 240", (256, 240)),
    ("ZX Spectrum · 256 × 192", (256, 192)),
    ("320 × 200", (320, 200)),
    ("320 × 240", (320, 240)),
    ("640 × 480", (640, 480)),
]

PIXEL_ASPECT_PRESETS = [
    ("Square · 1:1", (1.0, 1.0)),
    ("CGA 320×200 display-fit · 5:6", (5.0, 6.0)),
    ("SNES display-fit · 7:6", (7.0, 6.0)),
    ("Mega Drive 320-wide · 14:15", (14.0, 15.0)),
    ("C64 multicolor display-fit · 5:3", (5.0, 3.0)),
    ("Custom", None),
]


class TargetRasterWidget(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._loading = False
        self._source_size: tuple[int, int] | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.enabled = QCheckBox("Use exact target raster")
        self.enabled.toggled.connect(self._emit_changed)
        root.addWidget(self.enabled)

        self.preset = QComboBox()
        for label, size in RASTER_PRESETS:
            self.preset.addItem(label, size)
        self.preset.currentIndexChanged.connect(self._preset_changed)
        root.addWidget(self.preset)

        size_grid = QGridLayout()
        self.width = QSpinBox(); self.width.setRange(1, 16384); self.width.setValue(320)
        self.height = QSpinBox(); self.height.setRange(1, 16384); self.height.setValue(200)
        self.keep_aspect = QCheckBox("Keep aspect ratio"); self.keep_aspect.setChecked(True)
        self.width.valueChanged.connect(self._width_changed)
        self.height.valueChanged.connect(self._height_changed)
        self.keep_aspect.toggled.connect(self._emit_changed)
        size_grid.addWidget(QLabel("Width"), 0, 0); size_grid.addWidget(self.width, 0, 1)
        size_grid.addWidget(QLabel("Height"), 0, 2); size_grid.addWidget(self.height, 0, 3)
        size_grid.addWidget(self.keep_aspect, 1, 0, 1, 4)
        root.addLayout(size_grid)

        form = QFormLayout()
        self.fit_mode = QComboBox(); self.fit_mode.addItem("Fit · show all", "fit"); self.fit_mode.addItem("Fill · crop edges", "fill"); self.fit_mode.addItem("Stretch", "stretch")
        self.fit_mode.currentIndexChanged.connect(self._emit_changed)
        form.addRow("Source fit", self.fit_mode)

        self.pixel_aspect = QComboBox()
        for label, value in PIXEL_ASPECT_PRESETS:
            self.pixel_aspect.addItem(label, value)
        self.pixel_aspect.currentIndexChanged.connect(self._pixel_aspect_changed)
        form.addRow("Pixel aspect", self.pixel_aspect)

        custom = QWidget(); cr = QHBoxLayout(custom); cr.setContentsMargins(0, 0, 0, 0)
        self.par_x = QDoubleSpinBox(); self.par_x.setRange(0.05, 20.0); self.par_x.setDecimals(3); self.par_x.setValue(1.0)
        self.par_y = QDoubleSpinBox(); self.par_y.setRange(0.05, 20.0); self.par_y.setDecimals(3); self.par_y.setValue(1.0)
        self.par_x.valueChanged.connect(self._emit_changed); self.par_y.valueChanged.connect(self._emit_changed)
        cr.addWidget(self.par_x); cr.addWidget(QLabel(":")); cr.addWidget(self.par_y)
        self.custom_par_host = custom
        form.addRow("Custom PAR", custom)

        self.view_mode = QComboBox(); self.view_mode.addItem("Raw framebuffer", "raw"); self.view_mode.addItem("Corrected pixels", "corrected"); self.view_mode.addItem("Display simulation", "display")
        self.view_mode.currentIndexChanged.connect(self._emit_changed)
        form.addRow("View", self.view_mode)
        self.display_export = QCheckBox("Use display view in export")
        self.display_export.toggled.connect(self._emit_changed)
        form.addRow("", self.display_export)
        root.addLayout(form)

        self._pixel_aspect_changed()

    def set_source_size(self, size: tuple[int, int] | None) -> None:
        self._source_size = size
        if size and not self.enabled.isChecked():
            self._loading = True
            self.width.setValue(size[0]); self.height.setValue(size[1])
            self._loading = False

    def _source_aspect(self) -> float:
        if self._source_size and self._source_size[1] > 0:
            return self._source_size[0] / self._source_size[1]
        return self.width.value() / max(1, self.height.value())

    def _preset_changed(self) -> None:
        if self._loading:
            return
        size = self.preset.currentData()
        if size:
            self._loading = True
            self.enabled.setChecked(True)
            self.width.setValue(int(size[0])); self.height.setValue(int(size[1]))
            self._loading = False
        self.changed.emit()

    def _width_changed(self, value: int) -> None:
        if self._loading:
            return
        if self.keep_aspect.isChecked():
            aspect = self._source_aspect()
            self._loading = True
            self.height.setValue(max(1, round(value / max(1e-6, aspect))))
            self._loading = False
        self._set_custom_preset()
        self.changed.emit()

    def _height_changed(self, value: int) -> None:
        if self._loading:
            return
        if self.keep_aspect.isChecked():
            aspect = self._source_aspect()
            self._loading = True
            self.width.setValue(max(1, round(value * aspect)))
            self._loading = False
        self._set_custom_preset()
        self.changed.emit()

    def _set_custom_preset(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.preset.setCurrentIndex(0)
        self._loading = False

    def _pixel_aspect_changed(self) -> None:
        value = self.pixel_aspect.currentData()
        custom = value is None
        self.custom_par_host.setVisible(custom)
        if value is not None and not self._loading:
            self._loading = True
            self.par_x.setValue(float(value[0])); self.par_y.setValue(float(value[1]))
            self._loading = False
            self.changed.emit()

    def _emit_changed(self, *_args) -> None:
        if not self._loading:
            self.changed.emit()

    def apply_to_settings(self, settings: ProcessingSettings) -> None:
        settings.target_enabled = self.enabled.isChecked()
        settings.target_width = self.width.value()
        settings.target_height = self.height.value()
        settings.keep_aspect = self.keep_aspect.isChecked()
        settings.fit_mode = str(self.fit_mode.currentData() or "fit")
        settings.pixel_aspect_x = self.par_x.value()
        settings.pixel_aspect_y = self.par_y.value()
        settings.display_mode = str(self.view_mode.currentData() or "corrected")
        settings.display_export = self.display_export.isChecked()

    def set_from_settings(self, settings: ProcessingSettings) -> None:
        self._loading = True
        try:
            self.enabled.setChecked(settings.target_enabled)
            self.width.setValue(settings.target_width or (self._source_size[0] if self._source_size else 320))
            self.height.setValue(settings.target_height or (self._source_size[1] if self._source_size else 200))
            self.keep_aspect.setChecked(settings.keep_aspect)
            idx = self.fit_mode.findData(settings.fit_mode); self.fit_mode.setCurrentIndex(max(0, idx))
            self.par_x.setValue(settings.pixel_aspect_x); self.par_y.setValue(settings.pixel_aspect_y)
            matched = -1
            for i in range(self.pixel_aspect.count()):
                value = self.pixel_aspect.itemData(i)
                if value and abs(value[0] - settings.pixel_aspect_x) < 1e-6 and abs(value[1] - settings.pixel_aspect_y) < 1e-6:
                    matched = i; break
            self.pixel_aspect.setCurrentIndex(matched if matched >= 0 else self.pixel_aspect.count() - 1)
            idx = self.view_mode.findData(settings.display_mode); self.view_mode.setCurrentIndex(max(0, idx))
            self.display_export.setChecked(settings.display_export)
            self.preset.setCurrentIndex(0)
        finally:
            self._loading = False
        self.custom_par_host.setVisible(self.pixel_aspect.currentData() is None)
