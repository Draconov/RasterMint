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

from PySide6.QtCore import QCoreApplication, QMetaObject, QObject, QSize, QUrl, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

from rastermint.qmlui.backend import RasterMintBackend  # noqa: E402
from rastermint.qmlui.image_provider import RasterImageProvider  # noqa: E402
from rastermint.qmlui.localization import LocalizationManager  # noqa: E402
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
    localization = LocalizationManager(engine, engine)
    engine.addImageProvider("rastermint", provider)
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("theme", theme)
    engine.rootContext().setContextProperty("localization", localization)
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


def test_custom_dither_designer_is_draft_only_until_apply():
    _app()
    provider = RasterImageProvider()
    backend = RasterMintBackend(provider)
    try:
        dither_index = next(
            i for i, step in enumerate(backend.settings.effect_stack)
            if step.get("kind") == "Dither"
        )
        before = backend.settings.effect_stack[dither_index]["params"]["custom_matrix_json"]
        before_algorithm = backend.settings.effect_stack[dither_index]["params"]["algorithm"]

        backend.setCustomDitherMatrixCell(0, 0, 99.0)
        assert backend.customDitherMatrix[0][0] == 99.0
        assert backend.settings.effect_stack[dither_index]["params"]["custom_matrix_json"] == before
        assert backend.settings.effect_stack[dither_index]["params"]["algorithm"] == before_algorithm

        backend.setCustomDitherMatrixSize(99)
        assert backend.customDitherMatrixSize == 12
        backend.setCustomDitherMatrixSize(1)
        assert backend.customDitherMatrixSize == 2

        backend.setCustomDitherMatrixSize(4)
        backend.setCustomDitherMatrixCell(0, 0, 99.0)
        backend.applyCustomDitherMatrix()
        dither_index = next(
            i for i, step in enumerate(backend.settings.effect_stack)
            if step.get("kind") == "Dither"
        )
        params = backend.settings.effect_stack[dither_index]["params"]
        import json
        applied = json.loads(params["custom_matrix_json"])
        assert params["algorithm"] == "Custom Matrix"
        assert backend.settings.effect_stack[dither_index]["enabled"] is True
        assert applied[0][0] == 99.0
    finally:
        backend.shutdown()


def test_rotate_image_refreshes_preset_thumbnails(monkeypatch):
    _app()
    provider = RasterImageProvider()
    backend = RasterMintBackend(provider)
    calls = []
    try:
        from PIL import Image

        backend._source_image = Image.new("RGB", (8, 4), "white")
        monkeypatch.setattr(RasterMintBackend, "refreshPresetThumbnails", lambda self: calls.append(self.settings.rotation))

        backend.rotateImage(90)
        assert backend.settings.rotation == 90
        assert calls == [90]

        # Undo is also a rotation change, so preset cards must return to the
        # original source orientation instead of staying at 90 degrees.
        backend.undo()
        assert backend.settings.rotation == 0
        assert calls == [90, 0]
    finally:
        backend.shutdown()

def test_missing_provider_key_returns_transparent_placeholder_instead_of_null_image():
    provider = RasterImageProvider()
    size = QSize()

    image = provider.requestImage("preset/does-not-exist?r=53", size, QSize())

    assert not image.isNull()
    assert (image.width(), image.height()) == (1, 1)
    assert (size.width(), size.height()) == (1, 1)
    assert image.pixelColor(0, 0).alpha() == 0

