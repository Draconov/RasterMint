# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
SUPPORTED_MEDIA_SUFFIXES = SUPPORTED_IMAGE_SUFFIXES | SUPPORTED_VIDEO_SUFFIXES


class ImageView(QGraphicsView):
    file_dropped = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._pixmap_item = QGraphicsPixmapItem()
        self._placeholder = QGraphicsSimpleTextItem("Drop an image or video here\nor use Open Image / Open Video")
        placeholder_font = QFont()
        placeholder_font.setPointSize(13)
        self._placeholder.setFont(placeholder_font)
        self._placeholder.setBrush(QBrush(QColor("#7D8491")))

        self._scene.addItem(self._pixmap_item)
        self._scene.addItem(self._placeholder)
        self.setScene(self._scene)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor("#171A21")))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self._has_image = False
        self._show_empty_state()

    def _show_empty_state(self) -> None:
        self._scene.setSceneRect(QRectF(0, 0, 900, 600))
        bounds = self._placeholder.boundingRect()
        self._placeholder.setPos(
            (900 - bounds.width()) / 2,
            (600 - bounds.height()) / 2,
        )
        self._placeholder.setVisible(True)
        self.resetTransform()
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap_item.setPixmap(pixmap)
        first = not self._has_image
        self._has_image = not pixmap.isNull()
        self._placeholder.setVisible(not self._has_image)
        if self._has_image:
            self._scene.setSceneRect(self._pixmap_item.boundingRect())
            if first:
                self.fit_image()
        else:
            self._show_empty_state()

    def clear_image(self) -> None:
        self._pixmap_item.setPixmap(QPixmap())
        self._has_image = False
        self._show_empty_state()

    def fit_image(self) -> None:
        if self._has_image:
            self.resetTransform()
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    @staticmethod
    def _first_supported_path(event) -> str | None:
        if not event.mimeData().hasUrls():
            return None
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.suffix.lower() in SUPPORTED_MEDIA_SUFFIXES:
                return str(path)
        return None

    def dragEnterEvent(self, event) -> None:
        if self._first_supported_path(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if self._first_supported_path(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        path = self._first_supported_path(event)
        if path:
            self.file_dropped.emit(path)
            event.acceptProposedAction()
        else:
            event.ignore()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self._has_image:
            return super().wheelEvent(event)
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        current = self.transform().m11()
        target = current * factor
        if 0.03 <= target <= 64:
            self.scale(factor, factor)
