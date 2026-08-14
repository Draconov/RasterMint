# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from rastermint import __version__
from rastermint.core.lospec import LOSPEC_PALETTE_LIST, palette_json_url, parse_lospec_palette


class LospecPaletteDialog(QDialog):
    palette_selected = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import palette from Lospec")
        self.resize(570, 420)
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
        self.browse_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(LOSPEC_PALETTE_LIST)))
        self.fetch_button = QPushButton("Fetch")
        self.fetch_button.clicked.connect(self.fetch_palette)
        row.addWidget(self.browse_button)
        row.addWidget(self.fetch_button)
        row.addStretch(1)
        root.addLayout(row)

        self.result_label = QLabel("No palette loaded yet.")
        self.result_label.setWordWrap(True)
        root.addWidget(self.result_label)

        self.swatch_scroll = QScrollArea()
        self.swatch_scroll.setWidgetResizable(True)
        self.swatch_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.swatch_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.swatch_scroll.setMinimumHeight(140)
        self.swatch_scroll.setMaximumHeight(180)
        self.swatch_host = QWidget()
        self.swatch_grid = QGridLayout(self.swatch_host)
        self.swatch_grid.setContentsMargins(6, 6, 6, 6)
        self.swatch_grid.setSpacing(4)
        self.swatch_scroll.setWidget(self.swatch_host)
        root.addWidget(self.swatch_scroll)
        self._rebuild_swatches([])

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        self.import_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.import_button.setText("Import palette")
        self.import_button.setEnabled(False)
        buttons.accepted.connect(self._accept_palette)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _rebuild_swatches(self, colors: list[str]) -> None:
        while self.swatch_grid.count():
            item = self.swatch_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        if not colors:
            empty = QLabel("Palette colors will appear here after Fetch.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #929AA8; padding: 24px;")
            self.swatch_grid.addWidget(empty, 0, 0, 1, 12)
            return
        columns = 12
        for i, color in enumerate(colors):
            swatch = QLabel()
            swatch.setFixedSize(36, 28)
            swatch.setToolTip(f"{i + 1}: {color}")
            swatch.setStyleSheet(
                f"background: {color}; border: 1px solid #6B7483; border-radius: 3px;"
            )
            self.swatch_grid.addWidget(swatch, i // columns, i % columns)
        self.swatch_grid.setColumnStretch(columns, 1)

    def fetch_palette(self) -> None:
        try:
            url = palette_json_url(self.slug_edit.text())
        except Exception as exc:
            QMessageBox.warning(self, "Invalid Lospec palette", str(exc))
            return
        self.fetch_button.setEnabled(False)
        self.result_label.setText("Downloading palette…")
        self._rebuild_swatches([])
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
            self._rebuild_swatches(palette.colors)
            self.import_button.setEnabled(True)
        except Exception as exc:
            self._palette = None
            self.import_button.setEnabled(False)
            self.result_label.setText("Palette could not be loaded.")
            self._rebuild_swatches([])
            QMessageBox.warning(self, "Lospec import failed", str(exc))
        finally:
            reply.deleteLater()

    def _accept_palette(self) -> None:
        if self._palette is None:
            return
        self.palette_selected.emit(self._palette)
        self.accept()
