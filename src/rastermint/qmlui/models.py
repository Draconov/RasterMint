# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal


def _format_summary_value(value: Any) -> str:
    """Format compact layer-summary values without binary float artifacts."""
    if isinstance(value, float):
        text = f"{value:.8f}".rstrip("0").rstrip(".")
        return "0" if text in {"", "-0"} else text
    return str(value)


class LayerListModel(QAbstractListModel):
    changed = Signal()

    NameRole = Qt.ItemDataRole.UserRole + 1
    KindRole = Qt.ItemDataRole.UserRole + 2
    IdRole = Qt.ItemDataRole.UserRole + 3
    EnabledRole = Qt.ItemDataRole.UserRole + 4
    SummaryRole = Qt.ItemDataRole.UserRole + 5
    OpacityRole = Qt.ItemDataRole.UserRole + 6
    BlendModeRole = Qt.ItemDataRole.UserRole + 7
    MaskRole = Qt.ItemDataRole.UserRole + 8
    GroupRole = Qt.ItemDataRole.UserRole + 9

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.KindRole: b"kind",
            self.IdRole: b"layerId",
            self.EnabledRole: b"layerEnabled",
            self.SummaryRole: b"summary",
            self.OpacityRole: b"layerOpacity",
            self.BlendModeRole: b"blendMode",
            self.MaskRole: b"layerMask",
            self.GroupRole: b"groupId",
        }

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role in (Qt.ItemDataRole.DisplayRole, self.NameRole):
            return str(item.get("kind", "Layer"))
        if role == self.KindRole:
            return str(item.get("kind", ""))
        if role == self.IdRole:
            return str(item.get("id", ""))
        if role == self.EnabledRole:
            return bool(item.get("enabled", True))
        if role == self.OpacityRole:
            return float(item.get("opacity", 1.0) or 0.0)
        if role == self.BlendModeRole:
            return str(item.get("blend_mode", "Normal") or "Normal")
        if role == self.MaskRole:
            return dict(item.get("mask") or {})
        if role == self.GroupRole:
            return str(item.get("group_id", "") or "")
        if role == self.SummaryRole:
            params = item.get("params") if isinstance(item.get("params"), dict) else {}
            kind = str(item.get("kind", ""))
            pieces = []
            for key, value in params.items():
                if key in {"profile_palette_json", "profile_group_indices_json"}:
                    continue
                if kind == "Hardware Limits" and key == "palette_source":
                    if str(params.get("profile_palette_json", "[]") or "[]") == "[]":
                        continue
                pieces.append(f"{key}: {_format_summary_value(value)}")
                if len(pieces) >= 2:
                    break
            return " · ".join(pieces)
        return None

    def replace(self, items: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()
        self.changed.emit()

    def item(self, row: int) -> dict[str, Any] | None:
        return self._items[row] if 0 <= row < len(self._items) else None

    def notify_row(self, row: int) -> None:
        if 0 <= row < len(self._items):
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx)
            self.changed.emit()
