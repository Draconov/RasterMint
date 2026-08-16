# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from datetime import datetime
import faulthandler
from importlib import resources
from pathlib import Path
import sys
import threading
import traceback

from PySide6.QtCore import QCoreApplication, QStandardPaths, QUrl
from PySide6.QtGui import QFont, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from rastermint import __app_name__, __version__
from rastermint.qmlui.backend import RasterMintBackend
from rastermint.qmlui.image_provider import RasterImageProvider
from rastermint.qmlui.theme import ThemeManager

_CRASH_LOG_HANDLE = None


def _load_app_icon() -> QIcon | None:
    try:
        icon_path = resources.files("rastermint").joinpath("data/icons/rastermint.png")
        if icon_path.is_file():
            return QIcon(str(icon_path))
    except Exception:
        pass
    return None


def _install_crash_logging() -> Path | None:
    global _CRASH_LOG_HANDLE
    try:
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        folder = Path(base) if base else Path.home() / ".rastermint"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "crash.log"
        _CRASH_LOG_HANDLE = path.open("a", encoding="utf-8", buffering=1)
        _CRASH_LOG_HANDLE.write(f"\n--- RasterMint {__version__} session {datetime.now().isoformat(timespec='seconds')} ---\n")
        faulthandler.enable(_CRASH_LOG_HANDLE, all_threads=True)

        def write_exception(exc_type, exc_value, exc_tb) -> None:
            if issubclass(exc_type, KeyboardInterrupt):
                return sys.__excepthook__(exc_type, exc_value, exc_tb)
            _CRASH_LOG_HANDLE.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
            _CRASH_LOG_HANDLE.flush()

        sys.excepthook = write_exception

        def thread_exception(args: threading.ExceptHookArgs) -> None:
            write_exception(args.exc_type, args.exc_value, args.exc_traceback)

        threading.excepthook = thread_exception
        return path
    except Exception:
        return None


def main() -> int:
    QCoreApplication.setOrganizationName("RasterMint")
    QCoreApplication.setApplicationName(__app_name__)
    QCoreApplication.setApplicationVersion(__version__)

    _install_crash_logging()

    app = QGuiApplication(sys.argv)
    # Basic is intentionally neutral: RasterMint's QML components own the look,
    # while the theme JSON files control colors live at runtime. The style must
    # be selected before any Qt Quick Controls are loaded by the QML engine.
    QQuickStyle.setStyle("Basic")
    font = QFont()
    font.setPointSize(10)
    app.setFont(font)

    icon = _load_app_icon()
    if icon is not None and not icon.isNull():
        app.setWindowIcon(icon)

    engine = QQmlApplicationEngine()
    provider = RasterImageProvider()
    backend = RasterMintBackend(provider)
    theme = ThemeManager()
    engine.addImageProvider("rastermint", provider)
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("theme", theme)

    qml_path = resources.files("rastermint").joinpath("qml/Main.qml")
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    app.aboutToQuit.connect(backend.shutdown)
    return app.exec()
