# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from rastermint.core.animation import EASINGS, normalize_tracks


class AnimationPanel(QWidget):
    animation_changed = Signal()
    time_changed = Signal(float)
    playback_changed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._targets: list[tuple[str, str, float]] = []
        self._tracks: list[dict] = []
        self._playing = False
        self._loading_tracks = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        form = QFormLayout()
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 600.0)
        self.duration_spin.setValue(4.0)
        self.duration_spin.setDecimals(2)
        self.duration_spin.setSuffix(" s")
        self.duration_spin.valueChanged.connect(self._duration_changed)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(12)
        self.fps_spin.valueChanged.connect(self._fps_changed)
        form.addRow("Duration", self.duration_spin)
        form.addRow("FPS", self.fps_spin)
        root.addLayout(form)

        timeline_row = QHBoxLayout()
        self.play_button = QPushButton("▶")
        self.play_button.setCheckable(True)
        self.play_button.toggled.connect(self._toggle_playback)
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, 1000)
        self.timeline.valueChanged.connect(self._timeline_changed)
        self.time_label = QLabel("0.00 s")
        self.time_label.setMinimumWidth(62)
        timeline_row.addWidget(self.play_button)
        timeline_row.addWidget(self.timeline, 1)
        timeline_row.addWidget(self.time_label)
        root.addLayout(timeline_row)

        self.track_list = QListWidget()
        self.track_list.setMaximumHeight(130)
        self.track_list.itemChanged.connect(self._track_item_changed)
        root.addWidget(self.track_list)

        self.target_combo = QComboBox()
        self.from_spin = QDoubleSpinBox()
        self.to_spin = QDoubleSpinBox()
        for spin in (self.from_spin, self.to_spin):
            spin.setRange(-10000.0, 10000.0)
            spin.setDecimals(3)
        self.easing_combo = QComboBox()
        self.easing_combo.addItems(EASINGS)

        add_form = QFormLayout()
        add_form.addRow("Animate", self.target_combo)
        pair = QHBoxLayout()
        pair.addWidget(self.from_spin)
        pair.addWidget(QLabel("→"))
        pair.addWidget(self.to_spin)
        pair.addWidget(self.easing_combo)
        add_form.addRow("From / To", pair)

        time_pair = QHBoxLayout()
        self.start_spin = QDoubleSpinBox()
        self.end_spin = QDoubleSpinBox()
        for spin in (self.start_spin, self.end_spin):
            spin.setRange(0.0, 600.0)
            spin.setDecimals(2)
            spin.setSuffix(" s")
        self.start_spin.setValue(0.0)
        self.end_spin.setValue(self.duration())
        time_pair.addWidget(self.start_spin)
        time_pair.addWidget(QLabel("→"))
        time_pair.addWidget(self.end_spin)
        add_form.addRow("Start / End", time_pair)
        root.addLayout(add_form)

        controls = QHBoxLayout()
        self.add_track_button = QPushButton("Add track")
        self.add_track_button.clicked.connect(self._add_track)
        self.remove_track_button = QPushButton("Remove")
        self.remove_track_button.clicked.connect(self._remove_track)
        controls.addWidget(self.add_track_button)
        controls.addWidget(self.remove_track_button)
        controls.addStretch(1)
        root.addLayout(controls)

        hint = QLabel("Animated parameters are locked in the effect editor while their track is enabled.")
        hint.setWordWrap(True)
        hint.setObjectName("sectionHint")
        root.addWidget(hint)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._play_tick)
        self.target_combo.currentIndexChanged.connect(self._target_changed)

    def duration(self) -> float:
        return self.duration_spin.value()

    def fps(self) -> int:
        return self.fps_spin.value()

    def current_time(self) -> float:
        return self.duration() * (self.timeline.value() / 1000.0)

    def is_playing(self) -> bool:
        return self._playing

    def tracks(self) -> list[dict]:
        return deepcopy(self._tracks)

    def animated_target_ids(self) -> set[str]:
        return {
            str(track.get("target", ""))
            for track in self._tracks
            if track.get("enabled", True) and track.get("target")
        }

    def set_animation(self, duration: float, fps: int, tracks: list[dict]) -> None:
        self.duration_spin.blockSignals(True)
        self.fps_spin.blockSignals(True)
        self.duration_spin.setValue(duration)
        self.fps_spin.setValue(fps)
        self.duration_spin.blockSignals(False)
        self.fps_spin.blockSignals(False)
        self.start_spin.setMaximum(self.duration())
        self.end_spin.setMaximum(self.duration())
        self.end_spin.setValue(self.duration())
        self._tracks = normalize_tracks(tracks)
        self._rebuild_track_list()
        self._update_timer_interval()

    def set_targets(self, targets: list[tuple[str, str, float]]) -> None:
        current = self.target_combo.currentData()
        self._targets = list(targets)
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        for target, label, value in self._targets:
            self.target_combo.addItem(label, target)
            self.target_combo.setItemData(
                self.target_combo.count() - 1,
                value,
                Qt.ItemDataRole.UserRole + 1,
            )
        if current:
            index = self.target_combo.findData(current)
            if index >= 0:
                self.target_combo.setCurrentIndex(index)
        self.target_combo.blockSignals(False)
        self._target_changed(self.target_combo.currentIndex())
        self._rebuild_track_list()

    def _target_changed(self, index: int) -> None:
        if index < 0:
            return
        value = self.target_combo.itemData(index, Qt.ItemDataRole.UserRole + 1)
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.0
        self.from_spin.setValue(numeric)
        self.to_spin.setValue(numeric)

    def _duration_changed(self, *_args) -> None:
        duration = self.duration()
        self.start_spin.setMaximum(duration)
        self.end_spin.setMaximum(duration)
        if self.end_spin.value() > duration or self.end_spin.value() <= self.start_spin.value():
            self.end_spin.setValue(duration)
        # Clip existing tracks instead of silently leaving them outside the project.
        for track in self._tracks:
            track["start"] = min(float(track.get("start", 0.0)), duration)
            track["end"] = min(max(float(track.get("end", duration)), track["start"]), duration)
        self._rebuild_track_list()
        self.animation_changed.emit()
        self._timeline_changed()

    def _fps_changed(self, *_args) -> None:
        self._update_timer_interval()
        self.animation_changed.emit()

    def _update_timer_interval(self) -> None:
        self.timer.setInterval(max(8, round(1000 / max(1, self.fps()))))

    def _timeline_changed(self, *_args) -> None:
        value = self.current_time()
        self.time_label.setText(f"{value:.2f} s")
        self.time_changed.emit(value)

    def _toggle_playback(self, playing: bool) -> None:
        self._playing = bool(playing)
        self.play_button.setText("❚❚" if playing else "▶")
        if playing:
            self._update_timer_interval()
            self.timer.start()
        else:
            self.timer.stop()
        self.playback_changed.emit(bool(playing))

    def _play_tick(self) -> None:
        # Slider has 1000 logical ticks. Convert one animation frame to ticks.
        step = max(1, round(1000.0 / (max(1, self.fps()) * max(0.1, self.duration()))))
        value = self.timeline.value() + step
        if value > self.timeline.maximum():
            value = self.timeline.minimum()
        self.timeline.setValue(value)

    def _add_track(self) -> None:
        target = self.target_combo.currentData()
        if not target:
            return
        start = min(self.start_spin.value(), self.duration())
        end = min(self.end_spin.value(), self.duration())
        if end <= start:
            end = min(self.duration(), start + max(1.0 / self.fps(), 0.01))
        self._tracks.append(
            {
                "target": str(target),
                "from": self.from_spin.value(),
                "to": self.to_spin.value(),
                "start": start,
                "end": end,
                "easing": self.easing_combo.currentText(),
                "enabled": True,
            }
        )
        self._rebuild_track_list()
        self.animation_changed.emit()

    def _remove_track(self) -> None:
        row = self.track_list.currentRow()
        if row < 0:
            return
        self._tracks.pop(row)
        self._rebuild_track_list()
        self.animation_changed.emit()

    def _track_item_changed(self, item: QListWidgetItem) -> None:
        if self._loading_tracks:
            return
        row = self.track_list.row(item)
        if 0 <= row < len(self._tracks):
            self._tracks[row]["enabled"] = item.checkState() == Qt.CheckState.Checked
            self.animation_changed.emit()

    def _rebuild_track_list(self) -> None:
        labels = {target: label for target, label, _ in self._targets}
        self._loading_tracks = True
        try:
            current_row = self.track_list.currentRow()
            self.track_list.clear()
            for track in self._tracks:
                label = labels.get(track["target"], track["target"])
                item = QListWidgetItem(
                    f"{label}: {track['from']:g} → {track['to']:g} · "
                    f"{track['start']:.2f}–{track['end']:.2f}s · {track['easing']}"
                )
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.CheckState.Checked if track.get("enabled", True) else Qt.CheckState.Unchecked
                )
                self.track_list.addItem(item)
            if self.track_list.count() and current_row >= 0:
                self.track_list.setCurrentRow(min(current_row, self.track_list.count() - 1))
        finally:
            self._loading_tracks = False
