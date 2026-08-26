# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from PySide6.QtCore import Property, QCoreApplication, QObject, QSettings, QTranslator, Signal, Slot
from PySide6.QtQml import QQmlEngine


DEFAULT_LANGUAGE_ID = "en"
LANGUAGE_ORDER = ("en", "uk")
LANGUAGE_NAMES = {
    "en": "English",
    "uk": "Українська",
}
_LEGACY_SYSTEM_LANGUAGE_ID = "system"


class _JsonTranslator(QTranslator):
    """Tiny QTranslator backed by RasterMint's packaged JSON dictionaries."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._messages: dict[str, str] = {}

    def set_messages(self, messages: dict[str, str]) -> None:
        self._messages = dict(messages)

    def isEmpty(self) -> bool:
        return not self._messages

    def translate(
        self,
        context: str,
        source_text: str,
        disambiguation: str | None = None,
        n: int = -1,
    ) -> str:
        del context, disambiguation, n
        return self._messages.get(str(source_text), "")


class LocalizationManager(QObject):
    """Persistent runtime language switching for QML without Qt .qm tooling."""

    languageChanged = Signal()

    def __init__(self, engine: QQmlEngine | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._settings = QSettings("RasterMint", "RasterMint")
        self._translator = _JsonTranslator(self)
        self._translator_installed = False

        requested = str(
            self._settings.value("appearance/language", DEFAULT_LANGUAGE_ID)
            or DEFAULT_LANGUAGE_ID
        )
        # Migrate the old "System default" choice to the new explicit default.
        if requested == _LEGACY_SYSTEM_LANGUAGE_ID:
            requested = DEFAULT_LANGUAGE_ID
            self._settings.setValue("appearance/language", requested)
        self._language_id = requested if requested in LANGUAGE_ORDER else DEFAULT_LANGUAGE_ID
        self._effective_language_id = self._language_id
        self._apply_language(retranslate=False)

    @staticmethod
    def _load_messages(language_id: str) -> dict[str, str]:
        if language_id == "en":
            return {}
        try:
            path = resources.files("rastermint").joinpath(
                f"data/translations/{language_id}.json"
            )
            payload: Any = json.loads(path.read_text(encoding="utf-8"))
            messages = payload.get("messages", {}) if isinstance(payload, dict) else {}
            if not isinstance(messages, dict):
                return {}
            return {
                str(source): str(translated)
                for source, translated in messages.items()
                if str(source) and str(translated)
            }
        except Exception:
            return {}

    def _apply_language(self, *, retranslate: bool = True) -> None:
        self._effective_language_id = self._language_id

        if self._translator_installed:
            QCoreApplication.removeTranslator(self._translator)
            self._translator_installed = False

        messages = self._load_messages(self._language_id)
        self._translator.set_messages(messages)
        if messages:
            self._translator_installed = QCoreApplication.installTranslator(self._translator)

        if retranslate and self._engine is not None:
            self._engine.retranslate()

    @Property(str, notify=languageChanged)
    def languageId(self) -> str:
        return self._language_id

    @Property(str, notify=languageChanged)
    def effectiveLanguageId(self) -> str:
        return self._effective_language_id

    @Property("QStringList", constant=True)
    def languageIds(self) -> list[str]:
        return list(LANGUAGE_ORDER)

    @Property("QStringList", constant=True)
    def languageNames(self) -> list[str]:
        return [LANGUAGE_NAMES[language_id] for language_id in LANGUAGE_ORDER]

    @Slot(str)
    def setLanguage(self, language_id_or_name: str) -> None:
        value = str(language_id_or_name or "")
        selected = value if value in LANGUAGE_ORDER else next(
            (key for key, name in LANGUAGE_NAMES.items() if name == value),
            "",
        )
        if not selected or selected == self._language_id:
            return
        self._language_id = selected
        self._settings.setValue("appearance/language", selected)
        self._apply_language(retranslate=True)
        self.languageChanged.emit()

    @Slot()
    def resetLanguage(self) -> None:
        self.setLanguage(DEFAULT_LANGUAGE_ID)
