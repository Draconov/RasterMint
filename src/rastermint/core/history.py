# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass
class HistoryEntry:
    state: dict[str, Any]
    action: str


class UndoHistory:
    """Bounded undo/redo storage with optional interaction grouping.
    A history entry stores the state *before* an edit and the human-readable
    action that produced the new state. Groups are used for continuous input
    such as slider/mirror-axis drags so one gesture becomes one undo step.
    """

    def __init__(self, limit: int = 100) -> None:
        self.limit = max(1, int(limit))
        self._undo: list[HistoryEntry] = []
        self._redo: list[HistoryEntry] = []
        self._group_active = False
        self._group_recorded = False
        self._group_action = ""

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def set_limit(self, limit: int) -> None:
        """Change the history depth while preserving the newest useful entries."""
        self.limit = max(1, int(limit))
        if len(self._undo) > self.limit:
            del self._undo[: len(self._undo) - self.limit]
        if len(self._redo) > self.limit:
            del self._redo[: len(self._redo) - self.limit]

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
        self.end_group()

    def begin_group(self, action: str = "") -> None:
        if self._group_active:
            return
        self._group_active = True
        self._group_recorded = False
        self._group_action = str(action or "")

    def end_group(self) -> None:
        self._group_active = False
        self._group_recorded = False
        self._group_action = ""

    def record(self, state: dict[str, Any], action: str) -> bool:
        if self._group_active and self._group_recorded:
            return False
        label = self._group_action or str(action or "Edit")
        self._undo.append(HistoryEntry(deepcopy(state), label))
        if len(self._undo) > self.limit:
            del self._undo[: len(self._undo) - self.limit]
        self._redo.clear()
        if self._group_active:
            self._group_recorded = True
        return True

    def undo(self, current_state: dict[str, Any]) -> tuple[dict[str, Any], str] | None:
        self.end_group()
        if not self._undo:
            return None
        entry = self._undo.pop()
        self._redo.append(HistoryEntry(deepcopy(current_state), entry.action))
        return deepcopy(entry.state), entry.action

    def redo(self, current_state: dict[str, Any]) -> tuple[dict[str, Any], str] | None:
        self.end_group()
        if not self._redo:
            return None
        entry = self._redo.pop()
        self._undo.append(HistoryEntry(deepcopy(current_state), entry.action))
        if len(self._undo) > self.limit:
            del self._undo[: len(self._undo) - self.limit]
        return deepcopy(entry.state), entry.action
