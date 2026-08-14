# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from rastermint import __app_name__, __version__
from rastermint.ui.main_window import MainWindow
from rastermint.ui.style import APP_STYLE
from importlib import resources


def _load_app_icon() -> QIcon | None:
    try:
        icon_path = resources.files("rastermint").joinpath("data/icons/rastermint.png")
        if icon_path.is_file():
            return QIcon(str(icon_path))
    except Exception:
        pass
    return None


def main() -> int:
    QCoreApplication.setOrganizationName("RasterMint")
    QCoreApplication.setApplicationName(__app_name__)
    QCoreApplication.setApplicationVersion(__version__)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    font = QFont()
    font.setPointSize(10)
    app.setFont(font)

    icon = _load_app_icon()
    if icon is not None and not icon.isNull():
        app.setWindowIcon(icon)

    window = MainWindow()
    if icon is not None and not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    return app.exec()
