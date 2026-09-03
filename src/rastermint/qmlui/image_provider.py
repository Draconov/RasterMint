# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from threading import RLock

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage
from PySide6.QtQml import QQmlImageProviderBase
from PySide6.QtQuick import QQuickImageProvider


class RasterImageProvider(QQuickImageProvider):
    """Thread-safe image provider used by the QML preview and thumbnails."""

    def __init__(self) -> None:
        super().__init__(QQmlImageProviderBase.ImageType.Image)
        self._images: dict[str, QImage] = {"preview": QImage()}
        self._lock = RLock()

    def set_image(self, key: str, image: QImage) -> None:
        with self._lock:
            self._images[str(key)] = image.copy()

    def clear(self, key: str = "preview") -> None:
        with self._lock:
            self._images[str(key)] = QImage()

    def requestImage(self, image_id: str, size: QSize, requested_size: QSize) -> QImage:  # noqa: N802 - Qt API
        key = image_id.split("?", 1)[0]
        with self._lock:
            image = self._images.get(key, QImage()).copy()

        if image.isNull():
            placeholder = QImage(1, 1, QImage.Format.Format_ARGB32)
            placeholder.fill(0)
            size.setWidth(1)
            size.setHeight(1)
            return placeholder

        # Qt expects `size` to describe the unscaled source image. The returned
        # QImage may still honor the requested display size.
        size.setWidth(image.width())
        size.setHeight(image.height())

        if requested_size.isValid() and requested_size.width() > 0 and requested_size.height() > 0:
            return image.scaled(requested_size)
        return image
