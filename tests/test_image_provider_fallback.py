from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


class _FakeSize:
    def __init__(self, width: int = -1, height: int = -1) -> None:
        self._width = width
        self._height = height

    def setWidth(self, value: int) -> None:
        self._width = value

    def setHeight(self, value: int) -> None:
        self._height = value

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height

    def isValid(self) -> bool:
        return self._width > 0 and self._height > 0


class _FakeQImage:
    class Format:
        Format_ARGB32 = 1

    def __init__(self, width: int = 0, height: int = 0, _format=None) -> None:
        self._width = width
        self._height = height
        self._filled = None

    def copy(self):
        clone = _FakeQImage(self._width, self._height)
        clone._filled = self._filled
        return clone

    def isNull(self) -> bool:
        return self._width <= 0 or self._height <= 0

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height

    def fill(self, value) -> None:
        self._filled = value

    def scaled(self, size):
        return _FakeQImage(size.width(), size.height())


class _FakeImageProviderBase:
    class ImageType:
        Image = 1


class _FakeQuickImageProvider:
    def __init__(self, _image_type) -> None:
        pass


def _load_provider_module():
    pyside6 = types.ModuleType("PySide6")
    qtcore = types.ModuleType("PySide6.QtCore")
    qtgui = types.ModuleType("PySide6.QtGui")
    qtqml = types.ModuleType("PySide6.QtQml")
    qtquick = types.ModuleType("PySide6.QtQuick")
    qtcore.QSize = _FakeSize
    qtgui.QImage = _FakeQImage
    qtqml.QQmlImageProviderBase = _FakeImageProviderBase
    qtquick.QQuickImageProvider = _FakeQuickImageProvider
    sys.modules.update({
        "PySide6": pyside6,
        "PySide6.QtCore": qtcore,
        "PySide6.QtGui": qtgui,
        "PySide6.QtQml": qtqml,
        "PySide6.QtQuick": qtquick,
    })

    path = Path(__file__).resolve().parents[1] / "src/rastermint/qmlui/image_provider.py"
    spec = importlib.util.spec_from_file_location("rastermint_test_image_provider", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_provider_key_returns_transparent_placeholder_instead_of_null_image():
    module = _load_provider_module()
    provider = module.RasterImageProvider()
    size = _FakeSize()

    image = provider.requestImage("preset/does-not-exist?r=53", size, _FakeSize())

    assert not image.isNull()
    assert (image.width(), image.height()) == (1, 1)
    assert (size.width(), size.height()) == (1, 1)
    assert image._filled == 0
