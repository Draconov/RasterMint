# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
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
from rastermint.core.animation_presets import ANIMATION_PRESETS


class AnimationPanel(QWidget):
    animation_changed = Signal()
    time_changed = Signal(float)
    playback_changed = Signal(bool)
    render_preview_requested = Signal()
    preview_mode_changed = Signal(str)
    preset_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._targets: list[tuple[str, str, float]] = []
        self._tracks: list[dict] = []
        self._playing = False
        self._loading_tracks = False
        self._rendered_ready = False
        self._rendered_description = "Not rendered"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(7)

        project_form = QFormLayout()
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
        project_form.addRow("Duration", self.duration_spin)
        project_form.addRow("FPS", self.fps_spin)
        root.addLayout(project_form)

        preview_row = QHBoxLayout()
        self.preview_mode_combo = QComboBox()
        self.preview_mode_combo.addItem("Quick playback", "quick")
        self.preview_mode_combo.addItem("Rendered playback", "rendered")
        self.preview_mode_combo.currentIndexChanged.connect(self._preview_mode_combo_changed)
        self.render_button = QPushButton("Render Preview")
        self.render_button.setToolTip("Pre-render the animation at preview resolution for smooth, accurate playback")
        self.render_button.clicked.connect(self.render_preview_requested.emit)
        preview_row.addWidget(self.preview_mode_combo, 1)
        preview_row.addWidget(self.render_button)
        root.addLayout(preview_row)
        self.render_status = QLabel("Quick playback processes frames live at the fast preview budget.")
        self.render_status.setWordWrap(True)
        self.render_status.setObjectName("sectionHint")
        root.addWidget(self.render_status)

        transport = QHBoxLayout()
        self.start_button = QPushButton("|‹")
        self.prev_frame_button = QPushButton("‹")
        self.play_button = QPushButton("▶")
        self.play_button.setCheckable(True)
        self.next_frame_button = QPushButton("›")
        self.end_button = QPushButton("›|")
        for button in (self.start_button, self.prev_frame_button, self.play_button, self.next_frame_button, self.end_button):
            button.setFixedWidth(34)
        self.start_button.clicked.connect(lambda: self._seek_time(0.0))
        self.prev_frame_button.clicked.connect(lambda: self._step_frames(-1))
        self.play_button.toggled.connect(self._toggle_playback)
        self.next_frame_button.clicked.connect(lambda: self._step_frames(1))
        self.end_button.clicked.connect(lambda: self._seek_time(self.duration()))
        self.loop_check = QCheckBox("Loop")
        self.loop_check.setChecked(True)
        self.loop_check.toggled.connect(lambda _v: self.animation_changed.emit())
        transport.addWidget(self.start_button)
        transport.addWidget(self.prev_frame_button)
        transport.addWidget(self.play_button)
        transport.addWidget(self.next_frame_button)
        transport.addWidget(self.end_button)
        transport.addWidget(self.loop_check)
        transport.addStretch(1)
        root.addLayout(transport)

        timeline_row = QHBoxLayout()
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, 10000)
        self.timeline.valueChanged.connect(self._timeline_changed)
        self.time_label = QLabel("0.00 s · f 0")
        self.time_label.setMinimumWidth(100)
        timeline_row.addWidget(self.timeline, 1)
        timeline_row.addWidget(self.time_label)
        root.addLayout(timeline_row)

        preset_row = QHBoxLayout()
        self.preset_combo = QComboBox()
        for preset in ANIMATION_PRESETS:
            self.preset_combo.addItem(preset.name, preset.id)
            self.preset_combo.setItemData(self.preset_combo.count() - 1, preset.description, Qt.ItemDataRole.ToolTipRole)
        self.apply_preset_button = QPushButton("Apply motion preset")
        self.apply_preset_button.clicked.connect(self._apply_selected_preset)
        preset_row.addWidget(self.preset_combo, 1)
        preset_row.addWidget(self.apply_preset_button)
        root.addLayout(preset_row)

        dither_row = QHBoxLayout()
        dither_in = QPushButton("Dither In")
        dither_out = QPushButton("Dither Out")
        dither_both = QPushButton("In / Out")
        dither_in.clicked.connect(lambda: self.preset_requested.emit("dither-in"))
        dither_out.clicked.connect(lambda: self.preset_requested.emit("dither-out"))
        dither_both.clicked.connect(lambda: self.preset_requested.emit("dither-in-out"))
        dither_row.addWidget(dither_in)
        dither_row.addWidget(dither_out)
        dither_row.addWidget(dither_both)
        root.addLayout(dither_row)

        self.track_list = QListWidget()
        self.track_list.setMaximumHeight(170)
        self.track_list.itemChanged.connect(self._track_item_changed)
        self.track_list.currentRowChanged.connect(self._track_selected)
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
        self.add_track_button = QPushButton("Add")
        self.add_track_button.clicked.connect(self._add_track)
        self.update_track_button = QPushButton("Update")
        self.update_track_button.clicked.connect(self._update_track)
        self.duplicate_track_button = QPushButton("Duplicate")
        self.duplicate_track_button.clicked.connect(self._duplicate_track)
        self.remove_track_button = QPushButton("Remove")
        self.remove_track_button.clicked.connect(self._remove_track)
        controls.addWidget(self.add_track_button)
        controls.addWidget(self.update_track_button)
        controls.addWidget(self.duplicate_track_button)
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
        self._update_track_buttons()

    def duration(self) -> float:
        return self.duration_spin.value()

    def fps(self) -> int:
        return self.fps_spin.value()

    def loop_enabled(self) -> bool:
        return self.loop_check.isChecked()

    def preview_mode(self) -> str:
        return str(self.preview_mode_combo.currentData() or "quick")

    def current_time(self) -> float:
        return self.duration() * (self.timeline.value() / max(1, self.timeline.maximum()))

    def stop_playback(self) -> None:
        """Stop timeline playback without exposing internal timer details."""
        if self.play_button.isChecked():
            self.play_button.setChecked(False)
        else:
            self.timer.stop()

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

    def set_animation(self, duration: float, fps: int, tracks: list[dict], loop: bool = True) -> None:
        self.duration_spin.blockSignals(True)
        self.fps_spin.blockSignals(True)
        self.loop_check.blockSignals(True)
        self.duration_spin.setValue(duration)
        self.fps_spin.setValue(fps)
        self.loop_check.setChecked(bool(loop))
        self.duration_spin.blockSignals(False)
        self.fps_spin.blockSignals(False)
        self.loop_check.blockSignals(False)
        self.start_spin.setMaximum(self.duration())
        self.end_spin.setMaximum(self.duration())
        self.end_spin.setValue(self.duration())
        self._tracks = normalize_tracks(tracks)
        self._rebuild_track_list()
        self._update_timer_interval()
        self.set_rendered_ready(False)

    def set_targets(self, targets: list[tuple[str, str, float]]) -> None:
        current = self.target_combo.currentData()
        self._targets = list(targets)
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        for target, label, value in self._targets:
            self.target_combo.addItem(label, target)
            self.target_combo.setItemData(self.target_combo.count() - 1, value, Qt.ItemDataRole.UserRole + 1)
        if current:
            index = self.target_combo.findData(current)
            if index >= 0:
                self.target_combo.setCurrentIndex(index)
        self.target_combo.blockSignals(False)
        self._target_changed(self.target_combo.currentIndex())
        self._rebuild_track_list()

    def set_rendered_ready(self, ready: bool, *, frame_count: int = 0, fps: float = 0.0) -> None:
        self._rendered_ready = bool(ready)
        if ready:
            self._rendered_description = f"Cached {frame_count} frames at {fps:.1f} FPS · preview resolution"
            self.render_status.setText(self._rendered_description)
            self.render_button.setText("Re-render Preview")
        else:
            self._rendered_description = "Rendered playback needs a fresh cache after source/effect/track changes."
            if self.preview_mode() == "rendered":
                self.render_status.setText(self._rendered_description)
            else:
                self.render_status.setText("Quick playback processes frames live at the fast preview budget.")
            self.render_button.setText("Render Preview")

    def rendered_ready(self) -> bool:
        return self._rendered_ready

    def set_preview_mode(self, mode: str) -> None:
        index = self.preview_mode_combo.findData(mode)
        if index >= 0:
            self.preview_mode_combo.setCurrentIndex(index)

    def _preview_mode_combo_changed(self, *_args) -> None:
        mode = self.preview_mode()
        if mode == "rendered":
            self.render_status.setText(self._rendered_description)
        else:
            self.render_status.setText("Quick playback processes frames live at the fast preview budget.")
        self.preview_mode_changed.emit(mode)

    def _apply_selected_preset(self) -> None:
        preset_id = self.preset_combo.currentData()
        if preset_id:
            self.preset_requested.emit(str(preset_id))

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
        for track in self._tracks:
            track["start"] = min(float(track.get("start", 0.0)), duration)
            track["end"] = min(max(float(track.get("end", duration)), track["start"]), duration)
        self._rebuild_track_list()
        self.set_rendered_ready(False)
        self.animation_changed.emit()
        self._timeline_changed()

    def _fps_changed(self, *_args) -> None:
        self._update_timer_interval()
        self.set_rendered_ready(False)
        self.animation_changed.emit()
        self._timeline_changed()

    def _update_timer_interval(self) -> None:
        self.timer.setInterval(max(8, round(1000 / max(1, self.fps()))))

    def _timeline_changed(self, *_args) -> None:
        value = self.current_time()
        frame = max(0, round(value * self.fps()))
        self.time_label.setText(f"{value:.2f} s · f {frame}")
        self.time_changed.emit(value)

    def _seek_time(self, seconds: float) -> None:
        value = round(max(0.0, min(self.duration(), seconds)) / max(0.001, self.duration()) * self.timeline.maximum())
        self.timeline.setValue(value)

    def _step_frames(self, count: int) -> None:
        self._seek_time(self.current_time() + count / max(1, self.fps()))

    def _toggle_playback(self, playing: bool) -> None:
        self._playing = bool(playing)
        self.play_button.setText("❚❚" if playing else "▶")
        if playing:
            if self.preview_mode() == "rendered" and not self._rendered_ready:
                self.play_button.blockSignals(True)
                self.play_button.setChecked(False)
                self.play_button.setText("▶")
                self.play_button.blockSignals(False)
                self._playing = False
                self.render_preview_requested.emit()
                return
            self._update_timer_interval()
            self.timer.start()
        else:
            self.timer.stop()
        self.playback_changed.emit(self._playing)

    def _play_tick(self) -> None:
        next_time = self.current_time() + 1.0 / max(1, self.fps())
        if next_time > self.duration() + 1e-9:
            if self.loop_enabled():
                next_time = 0.0
            else:
                self._seek_time(self.duration())
                self.play_button.setChecked(False)
                return
        self._seek_time(next_time)

    def _new_track_from_form(self) -> dict | None:
        target = self.target_combo.currentData()
        if not target:
            return None
        start = min(self.start_spin.value(), self.duration())
        end = min(self.end_spin.value(), self.duration())
        if end <= start:
            end = min(self.duration(), start + max(1.0 / self.fps(), 0.01))
        return {
            "target": str(target),
            "from": self.from_spin.value(),
            "to": self.to_spin.value(),
            "start": start,
            "end": end,
            "easing": self.easing_combo.currentText(),
            "enabled": True,
        }

    def _add_track(self) -> None:
        track = self._new_track_from_form()
        if track is None:
            return
        self._tracks.append(track)
        self._rebuild_track_list(select_row=len(self._tracks) - 1)
        self.set_rendered_ready(False)
        self.animation_changed.emit()

    def _update_track(self) -> None:
        row = self.track_list.currentRow()
        track = self._new_track_from_form()
        if row < 0 or track is None:
            return
        track["enabled"] = bool(self._tracks[row].get("enabled", True))
        self._tracks[row] = track
        self._rebuild_track_list(select_row=row)
        self.set_rendered_ready(False)
        self.animation_changed.emit()

    def _duplicate_track(self) -> None:
        row = self.track_list.currentRow()
        if row < 0:
            return
        duplicate = deepcopy(self._tracks[row])
        self._tracks.insert(row + 1, duplicate)
        self._rebuild_track_list(select_row=row + 1)
        self.set_rendered_ready(False)
        self.animation_changed.emit()

    def _remove_track(self) -> None:
        row = self.track_list.currentRow()
        if row < 0:
            return
        self._tracks.pop(row)
        self._rebuild_track_list(select_row=min(row, len(self._tracks) - 1))
        self.set_rendered_ready(False)
        self.animation_changed.emit()

    def _track_selected(self, row: int) -> None:
        self._update_track_buttons()
        if row < 0 or row >= len(self._tracks):
            return
        track = self._tracks[row]
        index = self.target_combo.findData(track.get("target"))
        if index >= 0:
            self.target_combo.setCurrentIndex(index)
        self.from_spin.setValue(float(track.get("from", 0.0)))
        self.to_spin.setValue(float(track.get("to", 0.0)))
        self.start_spin.setValue(float(track.get("start", 0.0)))
        self.end_spin.setValue(float(track.get("end", self.duration())))
        easing_index = self.easing_combo.findText(str(track.get("easing", "Linear")))
        if easing_index >= 0:
            self.easing_combo.setCurrentIndex(easing_index)

    def _update_track_buttons(self) -> None:
        selected = self.track_list.currentRow() >= 0
        self.update_track_button.setEnabled(selected)
        self.duplicate_track_button.setEnabled(selected)
        self.remove_track_button.setEnabled(selected)

    def _track_item_changed(self, item: QListWidgetItem) -> None:
        if self._loading_tracks:
            return
        row = self.track_list.row(item)
        if 0 <= row < len(self._tracks):
            self._tracks[row]["enabled"] = item.checkState() == Qt.CheckState.Checked
            self.set_rendered_ready(False)
            self.animation_changed.emit()

    def _rebuild_track_list(self, *, select_row: int | None = None) -> None:
        labels = {target: label for target, label, _ in self._targets}
        self._loading_tracks = True
        try:
            current_row = self.track_list.currentRow() if select_row is None else select_row
            self.track_list.clear()
            for track in self._tracks:
                label = labels.get(track["target"], track["target"])
                item = QListWidgetItem(
                    f"{label}: {track['from']:g} → {track['to']:g} · "
                    f"{track['start']:.2f}–{track['end']:.2f}s · {track['easing']}"
                )
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if track.get("enabled", True) else Qt.CheckState.Unchecked)
                self.track_list.addItem(item)
            if self.track_list.count() and current_row is not None and current_row >= 0:
                self.track_list.setCurrentRow(min(current_row, self.track_list.count() - 1))
        finally:
            self._loading_tracks = False
        self._update_track_buttons()
