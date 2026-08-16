# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from PySide6.QtCore import QObject, Property, QSettings, Signal, Slot

DEFAULT_THEME_ID = "rastermint-dark"


class ThemeManager(QObject):
    themeChanged = Signal()
    themeNamesChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = QSettings("RasterMint", "RasterMint")
        self._themes = self._load_themes()
        requested = str(self._settings.value("appearance/theme", DEFAULT_THEME_ID) or DEFAULT_THEME_ID)
        self._theme_id = requested if requested in self._themes else DEFAULT_THEME_ID
        if self._theme_id not in self._themes and self._themes:
            self._theme_id = next(iter(self._themes))

    @staticmethod
    def _load_themes() -> dict[str, dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        root = resources.files("rastermint").joinpath("data/themes")
        try:
            entries = sorted(root.iterdir(), key=lambda p: p.name.casefold())
        except Exception:
            return found
        for entry in entries:
            if not entry.name.lower().endswith(".json"):
                continue
            try:
                data = json.loads(entry.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("id") and data.get("name"):
                    found[str(data["id"])] = data
            except Exception:
                continue
        if DEFAULT_THEME_ID in found:
            default = found.pop(DEFAULT_THEME_ID)
            found = {DEFAULT_THEME_ID: default, **found}
        return found

    def _value(self, key: str, fallback: str) -> str:
        return str(self._themes.get(self._theme_id, {}).get(key, fallback))

    @Property(str, notify=themeChanged)
    def themeId(self) -> str:
        return self._theme_id

    @Property(str, notify=themeChanged)
    def themeName(self) -> str:
        return self._value("name", "RasterMint Dark")

    @Property("QStringList", notify=themeNamesChanged)
    def themeNames(self) -> list[str]:
        return [str(v.get("name", k)) for k, v in self._themes.items()]

    @Property("QStringList", notify=themeNamesChanged)
    def themeIds(self) -> list[str]:
        return list(self._themes.keys())

    @Slot(str)
    def setTheme(self, theme_id_or_name: str) -> None:
        value = str(theme_id_or_name)
        selected = value if value in self._themes else next(
            (key for key, data in self._themes.items() if str(data.get("name")) == value),
            "",
        )
        if not selected or selected == self._theme_id:
            return
        self._theme_id = selected
        self._settings.setValue("appearance/theme", selected)
        self.themeChanged.emit()

    @Slot()
    def resetTheme(self) -> None:
        self.setTheme(DEFAULT_THEME_ID)

    @Property(str, notify=themeChanged)
    def windowColor(self) -> str:
        return self._value("window", "#15181D")

    @Property(str, notify=themeChanged)
    def canvasColor(self) -> str:
        return self._value("canvas", "#111318")

    @Property(str, notify=themeChanged)
    def panelColor(self) -> str:
        return self._value("panel", "#20242B")

    @Property(str, notify=themeChanged)
    def panelRaisedColor(self) -> str:
        return self._value("panelRaised", "#292E36")

    @Property(str, notify=themeChanged)
    def panelHoverColor(self) -> str:
        return self._value("panelHover", "#303640")

    @Property(str, notify=themeChanged)
    def borderColor(self) -> str:
        return self._value("border", "#363C46")

    @Property(str, notify=themeChanged)
    def textColor(self) -> str:
        return self._value("text", "#F1F3F0")

    @Property(str, notify=themeChanged)
    def mutedTextColor(self) -> str:
        return self._value("textMuted", "#969DA7")

    @Property(str, notify=themeChanged)
    def accentColor(self) -> str:
        return self._value("accent", "#A5BD34")

    @Property(str, notify=themeChanged)
    def accentHoverColor(self) -> str:
        return self._value("accentHover", "#C3DA45")

    @Property(str, notify=themeChanged)
    def accentTextColor(self) -> str:
        return self._value("accentText", "#111318")

    @Property(str, notify=themeChanged)
    def dangerColor(self) -> str:
        return self._value("danger", "#D86A6A")

    @Property(str, notify=themeChanged)
    def selectionColor(self) -> str:
        return self._value("selection", "#33455A")

    @Property(str, notify=themeChanged)
    def mirrorAxisColor(self) -> str:
        return self._value("mirrorAxis", "#4DA3FF")
