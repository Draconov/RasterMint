# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainter, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
SUPPORTED_VIDEO_SUFFIXES = {".gif", ".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
SUPPORTED_MEDIA_SUFFIXES = SUPPORTED_IMAGE_SUFFIXES | SUPPORTED_VIDEO_SUFFIXES


class ImageView(QGraphicsView):
    file_dropped = Signal(str)
    mirror_axis_changed = Signal(str, float)

    # At this view scale one image pixel is large enough that a grid is useful.
    AUTO_GRID_ZOOM = 8.0

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._pixmap_item = QGraphicsPixmapItem()
        self._pixmap_item.setTransformationMode(Qt.TransformationMode.FastTransformation)
        self._placeholder = QGraphicsSimpleTextItem("")
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
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

        self._has_image = False
        self._mirror_horizontal = False
        self._mirror_vertical = False
        self._mirror_horizontal_axis = 0.5
        self._mirror_vertical_axis = 0.5
        self._dragging_axis: str | None = None
        self._show_empty_state()

    def _show_empty_state(self) -> None:
        self._scene.setSceneRect(QRectF(0, 0, 900, 600))
        bounds = self._placeholder.boundingRect()
        self._placeholder.setPos((900 - bounds.width()) / 2, (600 - bounds.height()) / 2)
        self._placeholder.setVisible(True)
        self.resetTransform()
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.viewport().update()

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
        self.viewport().update()

    def clear_image(self) -> None:
        self._pixmap_item.setPixmap(QPixmap())
        self._has_image = False
        self._show_empty_state()

    def fit_image(self) -> None:
        if self._has_image:
            self.resetTransform()
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            self.viewport().update()

    def set_mirror_axes(
        self,
        horizontal: bool,
        horizontal_axis: float,
        vertical: bool,
        vertical_axis: float,
    ) -> None:
        self._mirror_horizontal = bool(horizontal)
        self._mirror_vertical = bool(vertical)
        self._mirror_horizontal_axis = max(0.0, min(1.0, float(horizontal_axis)))
        self._mirror_vertical_axis = max(0.0, min(1.0, float(vertical_axis)))
        if not self._mirror_horizontal and self._dragging_axis == "horizontal":
            self._dragging_axis = None
        if not self._mirror_vertical and self._dragging_axis == "vertical":
            self._dragging_axis = None
        self.viewport().update()

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
        current = abs(self.transform().m11())
        target = current * factor
        if 0.03 <= target <= 64:
            self.scale(factor, factor)
            self.viewport().update()

    def _axis_view_positions(self) -> dict[str, float]:
        if not self._has_image:
            return {}
        rect = self._pixmap_item.boundingRect()
        result: dict[str, float] = {}
        if self._mirror_horizontal:
            x = rect.left() + self._mirror_horizontal_axis * rect.width()
            result["horizontal"] = float(self.mapFromScene(QPointF(x, rect.center().y())).x())
        if self._mirror_vertical:
            y = rect.top() + self._mirror_vertical_axis * rect.height()
            result["vertical"] = float(self.mapFromScene(QPointF(rect.center().x(), y)).y())
        return result

    def _axis_hit(self, pos) -> str | None:
        positions = self._axis_view_positions()
        candidates: list[tuple[float, str]] = []
        if "horizontal" in positions:
            candidates.append((abs(float(pos.x()) - positions["horizontal"]), "horizontal"))
        if "vertical" in positions:
            candidates.append((abs(float(pos.y()) - positions["vertical"]), "vertical"))
        if not candidates:
            return None
        distance, mode = min(candidates)
        return mode if distance <= 9.0 else None

    def _set_axis_from_scene(self, mode: str, scene_pos: QPointF) -> None:
        rect = self._pixmap_item.boundingRect()
        if rect.width() <= 0 or rect.height() <= 0:
            return
        if mode == "horizontal":
            value = (scene_pos.x() - rect.left()) / rect.width()
            self._mirror_horizontal_axis = max(0.0, min(1.0, float(value)))
            self.mirror_axis_changed.emit("horizontal", self._mirror_horizontal_axis)
        else:
            value = (scene_pos.y() - rect.top()) / rect.height()
            self._mirror_vertical_axis = max(0.0, min(1.0, float(value)))
            self.mirror_axis_changed.emit("vertical", self._mirror_vertical_axis)
        self.viewport().update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._has_image:
            mode = self._axis_hit(event.position())
            if mode is not None:
                self._dragging_axis = mode
                self.setCursor(Qt.CursorShape.SizeHorCursor if mode == "horizontal" else Qt.CursorShape.SizeVerCursor)
                self._set_axis_from_scene(mode, self.mapToScene(event.position().toPoint()))
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging_axis is not None:
            self._set_axis_from_scene(self._dragging_axis, self.mapToScene(event.position().toPoint()))
            event.accept()
            return
        super().mouseMoveEvent(event)
        mode = self._axis_hit(event.position()) if self._has_image else None
        if mode is not None:
            self.setCursor(Qt.CursorShape.SizeHorCursor if mode == "horizontal" else Qt.CursorShape.SizeVerCursor)
        elif not (event.buttons() & Qt.MouseButton.LeftButton):
            self.unsetCursor()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging_axis is not None and event.button() == Qt.MouseButton.LeftButton:
            self._set_axis_from_scene(self._dragging_axis, self.mapToScene(event.position().toPoint()))
            self._dragging_axis = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawForeground(painter, rect)
        if not self._has_image:
            return

        image_rect = self._pixmap_item.boundingRect()
        visible = rect.intersected(image_rect)
        if visible.isEmpty():
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # The pixel grid is a view aid only. It appears automatically when
        # individual pixels become large enough to inspect and is never baked
        # into preview/export renders.
        zoom = abs(self.transform().m11())
        if zoom >= self.AUTO_GRID_ZOOM:
            minor_pen = QPen(QColor(230, 238, 248, 54))
            minor_pen.setCosmetic(True)
            minor_pen.setWidth(1)
            major_pen = QPen(QColor(230, 238, 248, 105))
            major_pen.setCosmetic(True)
            major_pen.setWidth(1)

            x0 = max(0, math.floor(visible.left()))
            x1 = min(math.ceil(image_rect.right()), math.ceil(visible.right()))
            y0 = max(0, math.floor(visible.top()))
            y1 = min(math.ceil(image_rect.bottom()), math.ceil(visible.bottom()))

            minor_lines: list[QLineF] = []
            major_lines: list[QLineF] = []
            for x in range(x0, x1 + 1):
                line = QLineF(float(x), visible.top(), float(x), visible.bottom())
                (major_lines if x % 8 == 0 else minor_lines).append(line)
            for y in range(y0, y1 + 1):
                line = QLineF(visible.left(), float(y), visible.right(), float(y))
                (major_lines if y % 8 == 0 else minor_lines).append(line)
            painter.setPen(minor_pen)
            for line in minor_lines:
                painter.drawLine(line)
            painter.setPen(major_pen)
            for line in major_lines:
                painter.drawLine(line)

        # Mirror tools use a high-contrast blue axis that stays visible at any
        # zoom level. Dragging the line updates the renderer through a signal.
        axis_pen = QPen(QColor("#3D9CFF"))
        axis_pen.setCosmetic(True)
        axis_pen.setWidth(2)
        painter.setPen(axis_pen)
        if self._mirror_horizontal:
            x = image_rect.left() + self._mirror_horizontal_axis * image_rect.width()
            painter.drawLine(QLineF(x, image_rect.top(), x, image_rect.bottom()))
        if self._mirror_vertical:
            y = image_rect.top() + self._mirror_vertical_axis * image_rect.height()
            painter.drawLine(QLineF(image_rect.left(), y, image_rect.right(), y))

        painter.restore()
