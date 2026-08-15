# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from rastermint.core.hardware import HardwareProfile, load_builtin_profiles, load_profile_file, profile_summary, strict_supported


class HardwarePanel(QWidget):
    apply_requested = Signal(object, str, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.profiles: list[HardwareProfile] = load_builtin_profiles()
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(6)
        top = QHBoxLayout()
        self.profile_combo = QComboBox(); self.mode_combo = QComboBox(); self.mode_combo.addItem("Visual", "visual"); self.mode_combo.addItem("Strict", "strict")
        top.addWidget(self.profile_combo, 1); top.addWidget(self.mode_combo)
        root.addLayout(top)

        opts = QHBoxLayout()
        self.apply_resolution = QCheckBox("Raster"); self.apply_resolution.setChecked(True)
        self.apply_palette = QCheckBox("Palette"); self.apply_palette.setChecked(True)
        self.apply_par = QCheckBox("PAR"); self.apply_par.setChecked(True)
        self.apply_limits = QCheckBox("Limits"); self.apply_limits.setChecked(True)
        self.apply_display = QCheckBox("Display"); self.apply_display.setChecked(True)
        for w in (self.apply_resolution, self.apply_palette, self.apply_par, self.apply_limits, self.apply_display): opts.addWidget(w)
        root.addLayout(opts)

        buttons = QHBoxLayout()
        self.apply_button = QPushButton("Apply profile"); self.apply_button.clicked.connect(self._apply)
        load = QPushButton("Load profile JSON…"); load.clicked.connect(self._load_custom)
        buttons.addWidget(self.apply_button); buttons.addWidget(load); root.addLayout(buttons)
        self.profile_combo.currentIndexChanged.connect(self._update_info); self.mode_combo.currentIndexChanged.connect(self._update_info)
        self._rebuild_combo()

    def _rebuild_combo(self, selected_id: str | None = None) -> None:
        self.profile_combo.clear()
        self.profile_combo.addItem("Custom / current settings", "custom")
        self.profile_combo.setItemData(0, None, role=256)
        for profile in self.profiles:
            self.profile_combo.addItem(f"{profile.category} · {profile.name}", profile.id)
            index = self.profile_combo.count() - 1
            self.profile_combo.setItemData(index, profile, role=256)
            self.profile_combo.setItemData(index, self._tooltip_for(profile), Qt.ItemDataRole.ToolTipRole)
        if selected_id:
            idx = self.profile_combo.findData(selected_id)
            if idx >= 0: self.profile_combo.setCurrentIndex(idx)
        self._update_info()

    def current_profile(self) -> HardwareProfile | None:
        idx = self.profile_combo.currentIndex()
        if idx < 0: return None
        return self.profile_combo.itemData(idx, role=256)

    def select_profile(self, profile_id: str, mode: str = "visual") -> None:
        idx = self.profile_combo.findData(profile_id)
        if idx >= 0: self.profile_combo.setCurrentIndex(idx)
        midx = self.mode_combo.findData(mode); self.mode_combo.setCurrentIndex(max(0, midx))

    def _tooltip_for(self, profile: HardwareProfile) -> str:
        mode = str(self.mode_combo.currentData() or "visual")
        text = profile_summary(profile, mode)
        if mode == "strict" and not strict_supported(profile):
            text += "\nStrict mode falls back to the visual profile for this system."
        return text

    def _update_info(self, *_args) -> None:
        profile = self.current_profile()
        self.apply_button.setEnabled(profile is not None)
        self.profile_combo.setToolTip(self._tooltip_for(profile) if profile else "Custom settings")
        for i in range(1, self.profile_combo.count()):
            candidate = self.profile_combo.itemData(i, role=256)
            if isinstance(candidate, HardwareProfile):
                self.profile_combo.setItemData(i, self._tooltip_for(candidate), Qt.ItemDataRole.ToolTipRole)

    def _options(self) -> dict[str, bool]:
        return {"apply_resolution": self.apply_resolution.isChecked(), "apply_palette": self.apply_palette.isChecked(), "apply_pixel_aspect": self.apply_par.isChecked(), "apply_constraints": self.apply_limits.isChecked(), "apply_display": self.apply_display.isChecked()}

    def _apply(self) -> None:
        profile = self.current_profile()
        if profile: self.apply_requested.emit(profile, str(self.mode_combo.currentData() or "visual"), self._options())

    def _load_custom(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load hardware profile", "", "RasterMint hardware profile (*.json);;JSON (*.json)")
        if not path: return
        try:
            profile = load_profile_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Could not load profile", str(exc)); return
        self.profiles = [p for p in self.profiles if p.id != profile.id] + [profile]
        self.profiles.sort(key=lambda p: (p.category.lower(), p.name.lower()))
        self._rebuild_combo(profile.id)
