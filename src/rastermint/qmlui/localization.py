# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QCoreApplication, QLocale, QObject, QSettings, QTranslator, Signal, Slot
from PySide6.QtQml import QQmlEngine

from rastermint.core.extensions import asset_files


DEFAULT_LANGUAGE_ID = "en"
LANGUAGE_ORDER = (
    "en", "uk", "fr", "de", "es", "pt", "it", "he", "ar", "pl", "ga", "lv",
    "zh", "hi", "bn", "id", "ur", "pa", "ja", "vi", "tr", "ko",
)
LANGUAGE_NAMES = {
    "en": "English",
    "uk": "Українська",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "pt": "Português",
    "it": "Italiano",
    "he": "עברית",
    "ar": "العربية",
    "pl": "Polski",
    "ga": "Gaeilge",
    "lv": "Latviešu",
    "zh": "简体中文",
    "hi": "हिन्दी",
    "bn": "বাংলা",
    "id": "Bahasa Indonesia",
    "ur": "اردو",
    "pa": "ਪੰਜਾਬੀ",
    "ja": "日本語",
    "vi": "Tiếng Việt",
    "tr": "Türkçe",
    "ko": "한국어",
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


def _extension_translations() -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for path in asset_files("translations"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        language_id = str(payload.get("language") or path.stem).strip().lower().replace("-", "_").split("_", 1)[0]
        name = str(payload.get("name") or language_id).strip()
        messages = payload.get("messages")
        if not language_id or not name or not isinstance(messages, dict):
            continue
        records.append({"id": language_id, "name": name, "messages": messages, "path": Path(path)})
    return tuple(records)


class LocalizationManager(QObject):
    """Persistent runtime language switching for QML without Qt .qm tooling."""

    languageChanged = Signal()

    def __init__(self, engine: QQmlEngine | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._settings = QSettings("RasterMint", "RasterMint")
        self._translator = _JsonTranslator(self)
        self._translator_installed = False
        self._extension_translations = _extension_translations()
        extension_ids: list[str] = []
        self._language_names = dict(LANGUAGE_NAMES)
        for record in self._extension_translations:
            language_id = str(record["id"])
            if language_id not in self._language_names:
                self._language_names[language_id] = str(record["name"])
                extension_ids.append(language_id)
        self._language_order = tuple(LANGUAGE_ORDER) + tuple(sorted(extension_ids, key=lambda key: self._language_names[key].casefold()))

        setting_key = "appearance/language"
        if self._settings.contains(setting_key):
            requested = str(self._settings.value(setting_key, "") or "")
            # Old builds exposed a visible "System default" choice. Keep the
            # same intent internally, but resolve it to an actual language and
            # remove the legacy marker because it is no longer shown in the UI.
            if requested == _LEGACY_SYSTEM_LANGUAGE_ID:
                self._settings.remove(setting_key)
                requested = self._system_language_id()
        else:
            requested = self._system_language_id()

        self._language_id = requested if requested in self._language_order else DEFAULT_LANGUAGE_ID
        self._effective_language_id = self._language_id
        self._apply_language(retranslate=False)

    def _system_language_id(self) -> str:
        """Return the supported OS language, falling back to English."""
        try:
            locale = QLocale.system()
            candidates = [locale.name(), locale.bcp47Name()]
        except Exception:
            candidates = []

        aliases = {"iw": "he"}
        for candidate in candidates:
            code = str(candidate or "").replace("-", "_").split("_", 1)[0].lower()
            code = aliases.get(code, code)
            if code in self._language_order:
                return code
        return DEFAULT_LANGUAGE_ID

    def _load_messages(self, language_id: str) -> dict[str, str]:
        messages: dict[str, str] = {}
        if language_id != "en":
            try:
                path = resources.files("rastermint").joinpath(
                    f"data/translations/{language_id}.json"
                )
                payload: Any = json.loads(path.read_text(encoding="utf-8"))
                bundled = payload.get("messages", {}) if isinstance(payload, dict) else {}
                if isinstance(bundled, dict):
                    messages.update({
                        str(source): str(translated)
                        for source, translated in bundled.items()
                        if str(source) and str(translated)
                    })
            except Exception:
                pass

        # Extensions may add a completely new language or fill missing strings
        # for an existing language. Bundled non-empty translations remain the
        # baseline; deterministic extension order allows deliberate add-ons.
        for record in self._extension_translations:
            if str(record.get("id")) != language_id:
                continue
            extra = record.get("messages")
            if isinstance(extra, dict):
                messages.update({
                    str(source): str(translated)
                    for source, translated in extra.items()
                    if str(source) and str(translated)
                })
        return messages

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
        return list(self._language_order)

    @Property("QStringList", constant=True)
    def languageNames(self) -> list[str]:
        return [self._language_names[language_id] for language_id in self._language_order]

    @Slot(str, result=str)
    def translateText(self, source_text: str) -> str:
        """Translate runtime/data-driven UI text using the active dictionary.

        QML's qsTr() is ideal for literal strings, but several RasterMint models
        (effect metadata, preset categories and built-in preset descriptions)
        are populated at runtime. Routing those strings through the installed
        JSON translator makes them switch language just like literal QML text.
        """
        source = str(source_text or "")
        if not source or self._language_id == DEFAULT_LANGUAGE_ID:
            return source
        translated = self._translator.translate("", source)
        return translated or source

    @Slot(str, str, result=str)
    def translateRuntime(self, language_id: str, source_text: str) -> str:
        """QML-friendly runtime translation with an explicit language dependency.

        ``language_id`` is intentionally part of the call signature so QML
        bindings re-evaluate when ``effectiveLanguageId`` changes at runtime.
        The active translator remains the source of truth.
        """
        del language_id
        return self.translateText(source_text)

    @Slot(str)
    def setLanguage(self, language_id_or_name: str) -> None:
        value = str(language_id_or_name or "")
        selected = value if value in self._language_order else next(
            (key for key, name in self._language_names.items() if name == value),
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
        # Reset means "use RasterMint's default" rather than force English.
        # The default follows the OS language when supported and otherwise
        # resolves to English. Removing the key keeps future launches in auto
        # mode until the user explicitly chooses a language again.
        self._settings.remove("appearance/language")
        selected = self._system_language_id()
        if selected == self._language_id:
            return
        self._language_id = selected
        self._apply_language(retranslate=True)
        self.languageChanged.emit()
