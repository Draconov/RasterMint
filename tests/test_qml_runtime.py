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

from PySide6.QtCore import QCoreApplication, QMetaObject, QObject, QUrl, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

from rastermint.qmlui.backend import RasterMintBackend  # noqa: E402
from rastermint.qmlui.image_provider import RasterImageProvider  # noqa: E402
from rastermint.qmlui.theme import ThemeManager  # noqa: E402


# Match production: RasterMint uses customized QML menus and therefore keeps
# menu bars/popups in the Qt Quick scene rather than allowing native promotion.
# These attributes must be set before the first QGuiApplication is created.
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, True)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuWindows, True)


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



def test_top_menu_buttons_open_visible_nonzero_popups_offscreen():
    """Exercise the same explicit button->Menu popup path used by the app.

    This catches the regression where top-level labels reacted visually but the
    customized Menu had no visible geometry / did not appear below the button.
    Qt 6.8+ exposes AbstractButton.click(), which emits the normal clicked signal.
    """
    app = _app()
    engine, backend, provider, theme = _engine_with_context()
    qml_path = resources.files("rastermint").joinpath("qml/Main.qml")
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    app.processEvents()
    assert engine.rootObjects(), "Main.qml failed to create an ApplicationWindow"
    root = engine.rootObjects()[0]

    try:
        for label in ("File", "Edit", "View"):
            button = root.findChild(QObject, f"topMenuButton_{label}")
            menu = root.findChild(QObject, label.lower() + "Menu")
            assert button is not None, f"missing {label} top-menu button"
            assert menu is not None, f"missing {label} menu"

            # AbstractButton.click() is invokable from Qt 6.8 onward and follows
            # exactly the QML onClicked handler used by a real mouse click.
            assert QMetaObject.invokeMethod(button, "click", Qt.ConnectionType.DirectConnection)
            app.processEvents()

            assert bool(menu.property("opened")), f"{label} menu did not open"
            assert float(menu.property("width")) >= 200, f"{label} menu opened with zero/tiny width"
            assert float(menu.property("height")) > 20, f"{label} menu opened with zero/tiny height"
            menu.close()
            app.processEvents()
    finally:
        backend.shutdown()


def test_backend_undo_redo_restores_layer_parameter_and_action_text():
    _app()
    provider = RasterImageProvider()
    backend = RasterMintBackend(provider)
    try:
        backend.selectLayer(0)  # Adjustments
        before = backend.settings.effect_stack[0]["params"]["brightness"]
        backend.setLayerParam("brightness", 17)
        assert backend.settings.effect_stack[0]["params"]["brightness"] == 17
        assert backend.canUndo
        assert "Brightness" in backend.statusText

        backend.undo()
        assert backend.settings.effect_stack[0]["params"]["brightness"] == before
        assert backend.canRedo
        assert backend.statusText.startswith("Undo:")

        backend.redo()
        assert backend.settings.effect_stack[0]["params"]["brightness"] == 17
        assert backend.statusText.startswith("Redo:")
    finally:
        backend.shutdown()


def test_main_window_inspector_has_room_for_detailed_controls():
    app = _app()
    engine, backend, provider, theme = _engine_with_context()
    qml_path = resources.files("rastermint").joinpath("qml/Main.qml")
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    app.processEvents()
    assert engine.rootObjects()
    root = engine.rootObjects()[0]
    try:
        panel = root.findChild(QObject, "inspectorPanel")
        assert panel is not None
        assert float(panel.property("width")) >= 620
    finally:
        backend.shutdown()


def test_theme_manager_exposes_requested_theme_order():
    _app()
    theme = ThemeManager()
    assert theme.themeIds[:14] == [
        "rastermint-dark",
        "rastermint-light",
        "studio-gray",
        "midnight",
        "violet",
        "amber",
        "hacker",
        "oled",
        "trueblack",
        "solarized-dark",
        "solarized-light",
        "mint",
        "sunrise",
        "halloween",
    ]


def test_top_menu_button_releases_focus_when_popup_closes():
    app = _app()
    engine, backend, provider, theme = _engine_with_context()
    qml_path = resources.files("rastermint").joinpath("qml/Main.qml")
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    app.processEvents()
    assert engine.rootObjects()
    root = engine.rootObjects()[0]

    try:
        button = root.findChild(QObject, "topMenuButton_File")
        menu = root.findChild(QObject, "fileMenu")
        assert button is not None
        assert menu is not None

        assert QMetaObject.invokeMethod(button, "click", Qt.ConnectionType.DirectConnection)
        app.processEvents()
        assert bool(menu.property("opened"))

        menu.close()
        app.processEvents()
        assert not bool(button.property("focus"))
    finally:
        backend.shutdown()
