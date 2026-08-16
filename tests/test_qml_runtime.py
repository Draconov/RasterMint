from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

import pytest


# The local artifact environment used by repository tests may not have PySide6.
# On normal development installs and GitHub Actions, PySide6 is a project
# dependency. Linux CI installs Qt's required EGL/OpenGL runtime libraries, so
# this remains a real offscreen QML-engine smoke test rather than being skipped
# to hide missing system dependencies.
PySide6 = pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QSG_RHI_BACKEND", "software")

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

from rastermint.qmlui.backend import RasterMintBackend  # noqa: E402
from rastermint.qmlui.image_provider import RasterImageProvider  # noqa: E402
from rastermint.qmlui.theme import ThemeManager  # noqa: E402



_STYLE_CONFIGURED = False


def _app():
    global _STYLE_CONFIGURED
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(["rastermint-qml-smoke"])
    if not _STYLE_CONFIGURED:
        # Qt Quick Controls requires the style to be selected before any QML
        # importing Controls is loaded. Configure it exactly once per process.
        QQuickStyle.setStyle("Basic")
        _STYLE_CONFIGURED = True
    return app


def _engine_with_context():
    engine = QQmlApplicationEngine()
    provider = RasterImageProvider()
    backend = RasterMintBackend(provider)
    theme = ThemeManager()
    engine.addImageProvider("rastermint", provider)
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("theme", theme)
    return engine, backend, provider, theme


QML_DIR = Path(str(resources.files("rastermint").joinpath("qml")))
QML_COMPONENTS = sorted(path.relative_to(QML_DIR) for path in QML_DIR.rglob("*.qml"))


@pytest.mark.parametrize("relative_path", QML_COMPONENTS, ids=lambda p: str(p))
def test_every_qml_component_compiles_offscreen(relative_path):
    app = _app()
    engine, backend, provider, theme = _engine_with_context()
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / relative_path)))
    app.processEvents()

    errors = "\n".join(error.toString() for error in component.errors())
    try:
        assert not component.isError(), f"{relative_path} failed QML compilation:\n{errors}"
    finally:
        backend.shutdown()


def test_qml_main_window_loads_offscreen():
    app = _app()
    engine, backend, provider, theme = _engine_with_context()

    qml_path = resources.files("rastermint").joinpath("qml/Main.qml")
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    app.processEvents()

    assert engine.rootObjects(), "Main.qml failed to create an ApplicationWindow"
    assert engine.rootObjects()[0].property("title").startswith("RasterMint")

    backend.shutdown()
