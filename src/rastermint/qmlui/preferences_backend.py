# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot

from rastermint.core.history import UndoHistory
from rastermint.qmlui.backend import RasterMintBackend as BaseRasterMintBackend


DEFAULT_HISTORY_LIMIT = 50
MIN_HISTORY_LIMIT = 10
MAX_HISTORY_LIMIT = 200


def _clamp_history_limit(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_HISTORY_LIMIT
    return max(MIN_HISTORY_LIMIT, min(MAX_HISTORY_LIMIT, parsed))


class RasterMintBackend(BaseRasterMintBackend):
    """RasterMint backend with persistent UI-level history preferences."""

    historyLimitChanged = Signal()

    def __init__(self, image_provider, parent=None) -> None:
        super().__init__(image_provider, parent)
        self._history_limit = _clamp_history_limit(
            self.app_settings.value("historyLimitQml", DEFAULT_HISTORY_LIMIT)
        )
        # The base backend creates history during construction, before any user
        # edits can exist. Recreate it with the persisted depth immediately.
        self._history = UndoHistory(limit=self._history_limit)

    def _get_history_limit(self) -> int:
        return self._history_limit

    @Slot(int)
    def _set_history_limit(self, limit: int) -> None:
        value = _clamp_history_limit(limit)
        if value == self._history_limit:
            return
        self._history_limit = value
        self._history.set_limit(value)
        self.app_settings.setValue("historyLimitQml", value)
        self.historyLimitChanged.emit()
        self._set_status(f"Undo history: {value} actions")

    historyLimit = Property(
        int,
        _get_history_limit,
        _set_history_limit,
        notify=historyLimitChanged,
    )

    @Slot()
    def resetSettings(self) -> None:
        super().resetSettings()
        changed = self._history_limit != DEFAULT_HISTORY_LIMIT
        self._history_limit = DEFAULT_HISTORY_LIMIT
        self._history.set_limit(DEFAULT_HISTORY_LIMIT)
        self.app_settings.setValue("historyLimitQml", DEFAULT_HISTORY_LIMIT)
        if changed:
            self.historyLimitChanged.emit()
