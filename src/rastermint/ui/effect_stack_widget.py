# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from rastermint.core.effect_stack import (
    EFFECT_DEFINITIONS,
    animatable_targets,
    new_effect,
    normalize_effect_stack,
)


class EffectStackWidget(QWidget):
    stack_changed = Signal(list)
    targets_changed = Signal(list)

    def __init__(self, stack: list[dict] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._stack: list[dict] = []
        self._loading = False
        self._param_widgets: dict[str, QWidget] = {}
        self._animated_targets: set[str] = set()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.list = QListWidget()
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setMinimumHeight(165)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.itemChanged.connect(self._item_changed)
        self.list.currentItemChanged.connect(lambda *_: self._rebuild_param_form())
        self.list.model().rowsMoved.connect(lambda *_: self._sync_order_from_list())
        root.addWidget(self.list)

        buttons = QHBoxLayout()
        self.add_combo = QComboBox()
        self.add_combo.addItems(EFFECT_DEFINITIONS.keys())
        self.add_button = QPushButton("+")
        self.add_button.setToolTip("Add layer")
        self.add_button.clicked.connect(self._add_effect)
        self.up_button = QPushButton("↑")
        self.up_button.setToolTip("Move selected layer up")
        self.up_button.clicked.connect(lambda: self._move_selected(-1))
        self.down_button = QPushButton("↓")
        self.down_button.setToolTip("Move selected layer down")
        self.down_button.clicked.connect(lambda: self._move_selected(1))
        self.duplicate_button = QPushButton("⧉")
        self.duplicate_button.setToolTip("Duplicate selected layer")
        self.duplicate_button.clicked.connect(self._duplicate_selected)
        self.remove_button = QPushButton("−")
        self.remove_button.setToolTip("Remove selected layer")
        self.remove_button.clicked.connect(self._remove_selected)
        buttons.addWidget(self.add_combo, 1)
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.up_button)
        buttons.addWidget(self.down_button)
        buttons.addWidget(self.duplicate_button)
        buttons.addWidget(self.remove_button)
        root.addLayout(buttons)

        self.param_title = QLabel("Layer settings")
        self.param_title.setObjectName("sectionHint")
        root.addWidget(self.param_title)
        self.param_host = QWidget()
        self.param_form = QFormLayout(self.param_host)
        self.param_form.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.param_host)

        hint = QLabel("Drag layers to reorder. Uncheck a layer to bypass it.")
        hint.setWordWrap(True)
        hint.setObjectName("sectionHint")
        root.addWidget(hint)

        self.set_stack(stack or [])

    def stack(self) -> list[dict]:
        return deepcopy(self._stack)

    def set_stack(self, stack: list[dict], emit: bool = False) -> None:
        self._loading = True
        try:
            self._stack = normalize_effect_stack(stack)
            current_id = self.current_effect_id()
            self.list.clear()
            for step in self._stack:
                item = QListWidgetItem(step["kind"])
                item.setData(Qt.ItemDataRole.UserRole, step["id"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled)
                item.setCheckState(Qt.CheckState.Checked if step.get("enabled", True) else Qt.CheckState.Unchecked)
                self.list.addItem(item)
                if current_id and step["id"] == current_id:
                    self.list.setCurrentItem(item)
            if self.list.currentRow() < 0 and self.list.count():
                self.list.setCurrentRow(0)
            self._rebuild_param_form()
        finally:
            self._loading = False
        self._emit_targets()
        if emit:
            self.stack_changed.emit(self.stack())

    def current_effect_id(self) -> str | None:
        item = self.list.currentItem()
        return str(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def animatable_targets(self) -> list[tuple[str, str, float]]:
        return animatable_targets(self._stack)

    def set_animated_targets(self, targets: set[str] | list[str] | tuple[str, ...]) -> None:
        """Disable parameter editors currently driven by animation tracks."""
        self._animated_targets = {str(target) for target in targets}
        self._rebuild_param_form()

    def _step_by_id(self, effect_id: str | None) -> dict | None:
        return next((step for step in self._stack if step["id"] == effect_id), None)

    def _current_step(self) -> dict | None:
        return self._step_by_id(self.current_effect_id())

    def _emit_changed(self) -> None:
        if self._loading:
            return
        self.stack_changed.emit(self.stack())
        self._emit_targets()

    def _emit_targets(self) -> None:
        self.targets_changed.emit(self.animatable_targets())

    def _item_changed(self, item: QListWidgetItem) -> None:
        if self._loading:
            return
        step = self._step_by_id(str(item.data(Qt.ItemDataRole.UserRole)))
        if step is None:
            return
        step["enabled"] = item.checkState() == Qt.CheckState.Checked
        self._emit_changed()

    def _sync_order_from_list(self) -> None:
        if self._loading:
            return
        ordered_ids = [
            str(self.list.item(i).data(Qt.ItemDataRole.UserRole))
            for i in range(self.list.count())
        ]
        by_id = {step["id"]: step for step in self._stack}
        self._stack = [by_id[effect_id] for effect_id in ordered_ids if effect_id in by_id]
        self._emit_changed()

    def _add_effect(self) -> None:
        kind = self.add_combo.currentText()
        step = new_effect(kind)
        row = max(0, self.list.currentRow() + 1) if self.list.count() else 0
        self._stack.insert(row, step)
        self.set_stack(self._stack)
        self.list.setCurrentRow(row)
        self._emit_changed()

    def _duplicate_selected(self) -> None:
        row = self.list.currentRow()
        step = self._current_step()
        if row < 0 or step is None:
            return
        duplicate = new_effect(step["kind"], enabled=step.get("enabled", True))
        duplicate["params"] = deepcopy(step["params"])
        self._stack.insert(row + 1, duplicate)
        self.set_stack(self._stack)
        self.list.setCurrentRow(row + 1)
        self._emit_changed()

    def _remove_selected(self) -> None:
        row = self.list.currentRow()
        if row < 0:
            return
        self._stack.pop(row)
        self.set_stack(self._stack)
        if self.list.count():
            self.list.setCurrentRow(min(row, self.list.count() - 1))
        self._emit_changed()

    def _move_selected(self, delta: int) -> None:
        row = self.list.currentRow()
        target = row + delta
        if row < 0 or not (0 <= target < len(self._stack)):
            return
        self._stack[row], self._stack[target] = self._stack[target], self._stack[row]
        effect_id = self._stack[target]["id"]
        self.set_stack(self._stack)
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.ItemDataRole.UserRole) == effect_id:
                self.list.setCurrentRow(i)
                break
        self._emit_changed()

    def _clear_form(self) -> None:
        while self.param_form.rowCount():
            self.param_form.removeRow(0)
        self._param_widgets.clear()

    def _rebuild_param_form(self) -> None:
        self._clear_form()
        step = self._current_step()
        if step is None:
            self.param_title.setText("Layer settings")
            self.param_form.addRow(QLabel("Select or add a layer."))
            return
        self.param_title.setText(step["kind"])
        definition = EFFECT_DEFINITIONS[step["kind"]]
        params = definition.get("params", {})
        if not params:
            self.param_form.addRow(QLabel("No parameters"))
            return

        for key, spec in params.items():
            ptype = spec.get("type")
            value = step["params"].get(key, spec.get("default"))
            if ptype == "int":
                widget = QSpinBox()
                widget.setRange(int(spec["min"]), int(spec["max"]))
                widget.setSingleStep(int(spec.get("step", 1)))
                widget.setValue(int(round(float(value))))
                if spec.get("suffix"):
                    widget.setSuffix(str(spec["suffix"]))
                widget.valueChanged.connect(lambda new, k=key: self._parameter_changed(k, new))
            elif ptype == "float":
                widget = QDoubleSpinBox()
                widget.setRange(float(spec["min"]), float(spec["max"]))
                widget.setSingleStep(float(spec.get("step", 0.1)))
                widget.setDecimals(int(spec.get("decimals", 2)))
                widget.setValue(float(value))
                if spec.get("suffix"):
                    widget.setSuffix(str(spec["suffix"]))
                widget.valueChanged.connect(lambda new, k=key: self._parameter_changed(k, new))
            elif ptype == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(value))
                widget.toggled.connect(lambda new, k=key: self._parameter_changed(k, new))
            elif ptype == "choice":
                host = QWidget()
                choice_row = QHBoxLayout(host)
                choice_row.setContentsMargins(0, 0, 0, 0)
                choice_row.setSpacing(4)
                previous = QPushButton("‹")
                previous.setFixedWidth(28)
                previous.setToolTip("Previous option")
                combo = QComboBox()
                options = [str(option) for option in spec.get("options", [])]
                combo.addItems(options)
                combo.setCurrentText(str(value))
                combo.currentTextChanged.connect(lambda new, k=key: self._parameter_changed(k, new))
                next_button = QPushButton("›")
                next_button.setFixedWidth(28)
                next_button.setToolTip("Next option")
                previous.clicked.connect(lambda _=False, c=combo: c.setCurrentIndex((c.currentIndex() - 1) % max(1, c.count())))
                next_button.clicked.connect(lambda _=False, c=combo: c.setCurrentIndex((c.currentIndex() + 1) % max(1, c.count())))
                choice_row.addWidget(previous)
                choice_row.addWidget(combo, 1)
                choice_row.addWidget(next_button)
                widget = host
            elif ptype == "text":
                widget = QLineEdit(str(value))
                widget.editingFinished.connect(lambda w=widget, k=key: self._parameter_changed(k, w.text()))
            elif ptype == "color":
                widget = QPushButton(str(value))
                widget.setStyleSheet(f"QPushButton {{ background: {value}; }}")
                widget.clicked.connect(lambda _=False, w=widget, k=key: self._choose_color(k, w))
            elif ptype == "file":
                host = QWidget()
                row = QHBoxLayout(host)
                row.setContentsMargins(0, 0, 0, 0)
                edit = QLineEdit(str(value))
                browse = QPushButton("…")
                browse.setFixedWidth(32)
                edit.editingFinished.connect(lambda e=edit, k=key: self._parameter_changed(k, e.text()))
                browse.clicked.connect(lambda _=False, e=edit, k=key, sp=spec: self._choose_file(k, e, sp))
                row.addWidget(edit, 1)
                row.addWidget(browse)
                widget = host
            else:
                continue
            target_id = f"effect:{step['id']}:{key}"
            if target_id in self._animated_targets:
                widget.setEnabled(False)
                widget.setToolTip("This parameter is controlled by an animation track.")
            self._param_widgets[key] = widget
            self.param_form.addRow(str(spec.get("label", key)), widget)


    def _choose_color(self, key: str, button: QPushButton) -> None:
        step = self._current_step()
        if step is None:
            return
        current = QColor(str(step["params"].get(key, "#FFFFFF")))
        chosen = QColorDialog.getColor(current, self, "Choose color")
        if not chosen.isValid():
            return
        value = chosen.name(QColor.NameFormat.HexRgb).upper()
        button.setText(value)
        button.setStyleSheet(f"QPushButton {{ background: {value}; }}")
        self._parameter_changed(key, value)

    def _choose_file(self, key: str, edit: QLineEdit, spec: dict) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose file",
            edit.text(),
            str(spec.get("file_filter") or "All files (*.*)"),
        )
        if not path:
            return
        edit.setText(path)
        self._parameter_changed(key, path)

    def _parameter_changed(self, key: str, value) -> None:
        if self._loading:
            return
        step = self._current_step()
        if step is None:
            return
        step["params"][key] = value
        self._emit_changed()


# New UI terminology: processing effects are presented as layers.
LayerStackWidget = EffectStackWidget
