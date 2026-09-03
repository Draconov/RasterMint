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

from PySide6.QtCore import QCoreApplication, QEvent, QRect, QStandardPaths, QUrl, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter, QPen, QRasterWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from rastermint import __app_name__, __version__

_CRASH_LOG_HANDLE = None


class _StartupSplash(QRasterWindow):
    """Lightweight native splash shown before the QML engine is ready."""

    WIDTH = 460
    HEIGHT = 180

    def __init__(self) -> None:
        super().__init__()
        self._progress = 0.0
        self._message = "Starting…"
        self.setFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.resize(self.WIDTH, self.HEIGHT)
        self.setTitle("RasterMint")

    def center_on_primary_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.x() + max(0, (area.width() - self.width()) // 2)
        y = area.y() + max(0, (area.height() - self.height()) // 2)
        self.setGeometry(x, y, self.width(), self.height())

    def set_progress(self, value: float, message: str) -> None:
        self._progress = max(0.0, min(1.0, float(value)))
        self._message = str(message or "")
        self.update()
        QGuiApplication.processEvents()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt virtual name
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(QRect(0, 0, self.width(), self.height()), QColor("#171B21"))

        painter.setPen(QColor("#F2F5F7"))
        title_font = painter.font()
        title_font.setPointSize(20)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(
            QRect(28, 28, self.width() - 56, 38),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "RasterMint",
        )

        painter.setPen(QColor("#AAB3BE"))
        body_font = painter.font()
        body_font.setPointSize(9)
        body_font.setBold(False)
        painter.setFont(body_font)
        painter.drawText(
            QRect(28, 72, self.width() - 56, 24),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._message,
        )

        bar = QRect(28, 118, self.width() - 56, 12)
        painter.setPen(QPen(QColor("#39414C"), 1))
        painter.setBrush(QColor("#242A32"))
        painter.drawRoundedRect(bar, 6, 6)

        fill_width = round(bar.width() * self._progress)
        if fill_width > 0:
            fill = QRect(bar.x(), bar.y(), fill_width, bar.height())
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#A8C62C"))
            painter.drawRoundedRect(fill, 6, 6)

        painter.setPen(QColor("#7F8996"))
        painter.drawText(
            QRect(28, 140, self.width() - 56, 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{__version__}  ·  {round(self._progress * 100):d}%",
        )
        painter.end()


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
        _CRASH_LOG_HANDLE.write(
            f"\n--- RasterMint {__version__} session {datetime.now().isoformat(timespec='seconds')} ---\n"
        )
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


def _destroy_qml_engine(engine: QQmlApplicationEngine) -> None:
    """Destroy QML roots before the engine releases context properties.

    ``setContextProperty`` does not transfer ownership of the Python QObjects.
    If Python tears down local variables after ``app.exec()`` returns, the
    context can disappear while QML objects are still being destroyed, causing
    a flood of ``Cannot read property ... of null`` messages.  Delete the root
    object tree first while backend/theme/localization are still strongly held
    by ``main()``, then delete the engine itself.
    """
    try:
        roots = tuple(engine.rootObjects())
    except RuntimeError:
        roots = ()

    for root in roots:
        try:
            root.deleteLater()
        except RuntimeError:
            pass

    # The main event loop has already returned, so explicitly flush deferred
    # deletes.  This keeps QML bindings alive only while their context objects
    # are still valid.
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    try:
        engine.collectGarbage()
    except RuntimeError:
        pass
    try:
        engine.deleteLater()
    except RuntimeError:
        return
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def main() -> int:
    QCoreApplication.setOrganizationName("RasterMint")
    QCoreApplication.setApplicationName(__app_name__)
    QCoreApplication.setApplicationVersion(__version__)
    _install_crash_logging()
    # RasterMint owns its menu styling and behavior in QML. Qt 6.8+ may
    # otherwise promote menus/menu bars to native windows depending on the
    # platform/style, bypassing our QML delegates. Keep them inside the Qt
    # Quick scene so hit testing, theming and popup behavior are consistent.
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, True)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuWindows, True)
    app = QGuiApplication(sys.argv)
    splash = _StartupSplash()
    splash.center_on_primary_screen()
    splash.show()
    splash.set_progress(0.08, "Starting RasterMint…")

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
    splash.set_progress(0.22, "Loading application modules…")

    # Import RasterMint's QML/backend layer only after Qt itself is alive.
    # The backend is intentionally lightweight at import time: NumPy, Pillow,
    # FFmpeg and the rendering pipeline are loaded only when a source is opened
    # or a processing/export worker actually runs.
    from rastermint.qmlui.export_backend import RasterMintBackend
    from rastermint.qmlui.image_provider import RasterImageProvider
    from rastermint.qmlui.localization import LocalizationManager
    from rastermint.qmlui.theme import ThemeManager

    splash.set_progress(0.42, "Creating interface engine…")
    engine = QQmlApplicationEngine()
    provider = RasterImageProvider()

    splash.set_progress(0.58, "Initializing editor…")
    backend = RasterMintBackend(provider)

    splash.set_progress(0.72, "Loading theme and language…")
    theme = ThemeManager()
    localization = LocalizationManager(engine)
    engine.addImageProvider("rastermint", provider)
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("theme", theme)
    engine.rootContext().setContextProperty("localization", localization)
    qml_path = resources.files("rastermint").joinpath("qml/Main.qml")
    splash.set_progress(0.88, "Loading interface…")
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        splash.close()
        backend.shutdown()
        _destroy_qml_engine(engine)
        return 1
    splash.set_progress(1.0, "Ready")
    splash.close()
    splash.deleteLater()

    # Stop workers as soon as Qt begins quitting, but keep the backend object
    # itself alive until after the QML root tree has been explicitly destroyed.
    app.aboutToQuit.connect(backend.shutdown)
    exit_code = app.exec()
    backend.shutdown()
    _destroy_qml_engine(engine)
    return exit_code
