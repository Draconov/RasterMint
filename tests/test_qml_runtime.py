from __future__ import annotations

import os
from importlib import resources

import pytest


# The local artifact environment used by repository tests may not have PySide6.
# On normal development installs and GitHub Actions, PySide6 is a project
# dependency, so this becomes a real QML engine smoke test rather than a static
# source check.
PySide6 = pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QSG_RHI_BACKEND", "software")

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

from rastermint.qmlui.backend import RasterMintBackend  # noqa: E402
from rastermint.qmlui.image_provider import RasterImageProvider  # noqa: E402
from rastermint.qmlui.theme import ThemeManager  # noqa: E402


def test_qml_main_window_loads_offscreen():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(["rastermint-qml-smoke"])

    QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    provider = RasterImageProvider()
    backend = RasterMintBackend(provider)
    theme = ThemeManager()
    engine.addImageProvider("rastermint", provider)
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("theme", theme)

    qml_path = resources.files("rastermint").joinpath("qml/Main.qml")
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    app.processEvents()

    assert engine.rootObjects(), "Main.qml failed to create an ApplicationWindow"
    assert engine.rootObjects()[0].property("title").startswith("RasterMint")

    backend.shutdown()
