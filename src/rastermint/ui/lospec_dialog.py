# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from rastermint import __version__
from rastermint.core.lospec import LOSPEC_PALETTE_LIST, palette_json_url, parse_lospec_palette


class LospecPaletteDialog(QDialog):
    palette_selected = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import palette from Lospec")
        self.resize(520, 250)
        self._palette = None
        self.network = QNetworkAccessManager(self)

        root = QVBoxLayout(self)
        intro = QLabel(
            "Browse Lospec, then paste a palette slug or full palette URL. "
            "RasterMint downloads the official palette JSON directly from Lospec."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.slug_edit = QLineEdit()
        self.slug_edit.setPlaceholderText("pico-8  or  https://lospec.com/palette-list/pico-8")
        self.slug_edit.returnPressed.connect(self.fetch_palette)
        form.addRow("Palette", self.slug_edit)
        root.addLayout(form)

        row = QHBoxLayout()
        self.browse_button = QPushButton("Browse Lospec")
        self.browse_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(LOSPEC_PALETTE_LIST))
        )
        self.fetch_button = QPushButton("Fetch")
        self.fetch_button.clicked.connect(self.fetch_palette)
        row.addWidget(self.browse_button)
        row.addWidget(self.fetch_button)
        row.addStretch(1)
        root.addLayout(row)

        self.result_label = QLabel("No palette loaded yet.")
        self.result_label.setWordWrap(True)
        root.addWidget(self.result_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        self.import_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.import_button.setText("Import palette")
        self.import_button.setEnabled(False)
        buttons.accepted.connect(self._accept_palette)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def fetch_palette(self) -> None:
        try:
            url = palette_json_url(self.slug_edit.text())
        except Exception as exc:
            QMessageBox.warning(self, "Invalid Lospec palette", str(exc))
            return
        self.fetch_button.setEnabled(False)
        self.result_label.setText("Downloading palette…")
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"User-Agent", f"RasterMint/{__version__}".encode("ascii", "ignore"))
        reply = self.network.get(request)
        reply.finished.connect(lambda r=reply: self._reply_finished(r))

    def _reply_finished(self, reply: QNetworkReply) -> None:
        self.fetch_button.setEnabled(True)
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                raise RuntimeError(reply.errorString())
            palette = parse_lospec_palette(self.slug_edit.text(), bytes(reply.readAll()))
            self._palette = palette
            self.result_label.setText(
                f"<b>{palette.name}</b> · {len(palette.colors)} colors<br>"
                f"Author: {palette.author}<br>{palette.source_url}"
            )
            self.import_button.setEnabled(True)
        except Exception as exc:
            self._palette = None
            self.import_button.setEnabled(False)
            self.result_label.setText("Palette could not be loaded.")
            QMessageBox.warning(self, "Lospec import failed", str(exc))
        finally:
            reply.deleteLater()

    def _accept_palette(self) -> None:
        if self._palette is None:
            return
        self.palette_selected.emit(self._palette)
        self.accept()
