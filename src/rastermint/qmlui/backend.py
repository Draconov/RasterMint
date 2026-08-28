# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import colorsys
from copy import deepcopy
import json
import math
import random
import re
import traceback
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QCoreApplication, QObject, Property, QRect, QSettings, QThreadPool, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QImage, QPainter, QPen, QRasterWindow
from PySide6.QtQuick import QQuickWindow

from rastermint import __version__
from rastermint.core.animation import EASINGS, MODULATORS, normalize_tracks, settings_at_time
from rastermint.core.animation_presets import ANIMATION_PRESETS, apply_animation_preset
from rastermint.core.builtin_presets import BUILTIN_PRESETS, build_builtin_preset
from rastermint.core.dither_metadata import ALGORITHMS
from rastermint.core.effect_schema import (
    BLEND_MODES, EFFECT_DEFINITIONS, FIXED_STAGE_KINDS, MASK_TYPES,
    default_effect_stack, default_layer_mask, effect_categories, new_effect, normalize_effect_stack,
)
from rastermint.core.gradient_presets import GRADIENT_PRESETS
from rastermint.core.hardware_profiles import apply_profile_to_settings, load_builtin_profiles, load_profile_file, profile_summary
from rastermint.core.history import UndoHistory
from rastermint.core.lospec import fetch_lospec_palette
from rastermint.core.palette_library import PALETTE_LIBRARY, find_palette, interpolate_palette, interpolate_palette_stops
from rastermint.core.presets import load_preset, save_preset
from rastermint.core.settings import ProcessingSettings

from .image_provider import RasterImageProvider
from .models import LayerListModel
from .workers import (
    AudioEnvelopeWorker,
    BatchWorker,
    MediaExportWorker,
    ProcessingWorker,
    BenchmarkWorker,
    RenderedPreviewWorker,
    SequenceExportWorker,
    VideoFrameWorker,
)

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".gif"}
PALETTE_OPTIMIZERS = ["Median Cut", "K-Means", "Octree", "Wu Quantization"]
PREVIEW_MAX_SIDE = 640
FAST_PREVIEW_MAX_SIDE = 320
MAX_FULL_PREVIEW_PIXELS = 12_000_000


def adaptive_preview_max_side(settings: ProcessingSettings, requested: int) -> int:
    from rastermint.core.processor import adaptive_preview_max_side as impl
    return impl(settings, requested)


def make_preview_settings(settings: ProcessingSettings, final_size: tuple[int, int], preview_size: tuple[int, int]) -> ProcessingSettings:
    from rastermint.core.processor import make_preview_settings as impl
    return impl(settings, final_size, preview_size)


def make_preview_source(source: Any, *, max_side: int, settings: ProcessingSettings):
    from rastermint.core.processor import make_preview_source as impl
    return impl(source, max_side=max_side, settings=settings)


def processed_raster_size(source_size: tuple[int, int], settings: ProcessingSettings) -> tuple[int, int]:
    from rastermint.core.processor import processed_raster_size as impl
    return impl(source_size, settings)


def target_raster_size(source_size: tuple[int, int], settings: ProcessingSettings) -> tuple[int, int]:
    from rastermint.core.processor import target_raster_size as impl
    return impl(source_size, settings)


def _palette_analysis(*args, **kwargs):
    from rastermint.core.palette_lab import palette_analysis as impl
    return impl(*args, **kwargs)


def _palette_mapping(*args, **kwargs):
    from rastermint.core.palette_lab import palette_mapping as impl
    return impl(*args, **kwargs)


def _sort_palette(*args, **kwargs):
    from rastermint.core.palette_lab import sort_palette as impl
    return impl(*args, **kwargs)


def probe_video(path: str | Path):
    from rastermint.core.media import probe_video as impl
    return impl(path)


def read_video_frame(path: str | Path, time_seconds: float = 0.0):
    from rastermint.core.media import read_video_frame as impl
    return impl(path, time_seconds)


def extract_palette(image: Any, colors: int, method: str):
    from rastermint.core.palette import extract_palette as impl
    return impl(image, colors, method)


def read_palette_file(path: str | Path):
    from rastermint.core.palette import read_palette_file as impl
    return impl(path)


def write_hex_palette(path: str | Path, colors: list[str]) -> None:
    from rastermint.core.palette import write_hex_palette as impl
    impl(path, colors)


def save_svg(image: Any, path: str | Path) -> None:
    from rastermint.core.svg_export import save_svg as impl
    impl(image, path)


def _is_pil_image(value: object) -> bool:
    from PIL import Image
    return isinstance(value, Image.Image)


def _local_path(value: str | QUrl) -> str:
    if isinstance(value, QUrl):
        return value.toLocalFile() if value.isLocalFile() else value.toString()
    text = str(value or "")
    url = QUrl(text)
    if url.isValid() and url.isLocalFile():
        return url.toLocalFile()
    return text


def _tr(source_text: str) -> str:
    return QCoreApplication.translate("RasterMintBackend", source_text)


def _qimage_to_pil(image: QImage):
    """Convert a clipboard QImage to a detached Pillow RGBA image."""
    from PIL import Image

    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    if rgba.isNull() or rgba.width() <= 0 or rgba.height() <= 0:
        raise ValueError("Clipboard image is empty.")
    raw = bytes(rgba.constBits())
    return Image.frombuffer(
        "RGBA",
        (rgba.width(), rgba.height()),
        raw,
        "raw",
        "RGBA",
        rgba.bytesPerLine(),
        1,
    ).copy()


class _ScreenEyedropperLoupe(QRasterWindow):
    """Always-on-top pixel loupe that follows the screen eyedropper cursor."""

    SAMPLE_SIZE = 17
    ZOOM = 10
    MARGIN = 8
    FOOTER_HEIGHT = 30

    def __init__(self) -> None:
        super().__init__()
        self.setFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setTitle("RasterMint Eyedropper Loupe")
        self._sample = QImage()
        self._center_color = QColor("#000000")
        side = self.SAMPLE_SIZE * self.ZOOM
        self.resize(side + self.MARGIN * 2, side + self.MARGIN * 2 + self.FOOTER_HEIGHT)

    def set_sample(self, image: QImage, color: QColor) -> None:
        self._sample = image.copy()
        self._center_color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt virtual name
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.fillRect(0, 0, self.width(), self.height(), QColor("#20262F"))

        side = self.SAMPLE_SIZE * self.ZOOM
        view = QRect(self.MARGIN, self.MARGIN, side, side)
        if not self._sample.isNull():
            painter.drawImage(view, self._sample)

        # Pixel grid keeps neighbouring colours readable at high zoom.
        painter.setPen(QPen(QColor(255, 255, 255, 48), 1))
        for index in range(1, self.SAMPLE_SIZE):
            pos = self.MARGIN + index * self.ZOOM
            painter.drawLine(pos, self.MARGIN, pos, self.MARGIN + side)
            painter.drawLine(self.MARGIN, pos, self.MARGIN + side, pos)

        # The center cell is the exact pixel that a left click will select.
        center = self.SAMPLE_SIZE // 2
        cx = self.MARGIN + center * self.ZOOM
        cy = self.MARGIN + center * self.ZOOM
        cell = QRect(cx, cy, self.ZOOM, self.ZOOM)
        painter.setPen(QPen(QColor("#000000"), 3))
        painter.drawRect(cell.adjusted(-2, -2, 2, 2))
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawRect(cell.adjusted(-1, -1, 1, 1))

        footer_y = self.MARGIN + side + 6
        swatch = QRect(self.MARGIN, footer_y, 18, 18)
        painter.fillRect(swatch, self._center_color)
        painter.setPen(QPen(QColor(255, 255, 255, 90), 1))
        painter.drawRect(swatch)
        painter.setPen(QColor("#F3F6FA"))
        painter.drawText(
            QRect(self.MARGIN + 26, footer_y, self.width() - self.MARGIN * 2 - 26, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._center_color.name(QColor.NameFormat.HexRgb).upper(),
        )
        painter.end()


class _ScreenEyedropperWindow(QQuickWindow):
    """Transparent top-level hit target used for one-click screen sampling."""

    picked = Signal(int, int)
    cancelled = Signal()

    def __init__(self, screen) -> None:
        super().__init__()
        self.setScreen(screen)
        self.setFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # A nearly-transparent surface remains an input target on Windows while
        # leaving the desktop visually unchanged. It is hidden before sampling.
        self.setColor(QColor(0, 0, 0, 1))
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(screen.geometry())
        self.setTitle("RasterMint Eyedropper")

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt virtual name
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.globalPosition().toPoint()
            self.picked.emit(point.x(), point.y())
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self.cancelled.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt virtual name
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            event.accept()
            return
        super().keyPressEvent(event)


def _pil_to_qimage(image: Any) -> QImage:
    rgb = image if image.mode == "RGB" else image.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    return QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888).copy()


class RasterMintBackend(QObject):
    previewChanged = Signal()
    sourceChanged = Signal()
    settingsChanged = Signal()
    layerSelectionChanged = Signal()
    layerWorkflowChanged = Signal()
    statusChanged = Signal()
    renderProgressChanged = Signal()
    playbackChanged = Signal()
    renderedPreviewChanged = Signal()
    hardwareProfilesChanged = Signal()
    paletteLibraryChanged = Signal()
    paletteLabChanged = Signal()
    ditherMatrixLibraryChanged = Signal()
    projectChanged = Signal()
    comparisonChanged = Signal()
    audioExportChanged = Signal()
    benchmarkChanged = Signal()
    errorOccurred = Signal(str, str)
    infoOccurred = Signal(str, str)
    historyChanged = Signal()
    showHotkeysChanged = Signal()
    screenColorPicked = Signal(str)
    screenEyedropperCancelled = Signal()

    def __init__(self, image_provider: RasterImageProvider, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.provider = image_provider
        self.app_settings = QSettings("RasterMint", "RasterMint")
        raw_show_hotkeys = self.app_settings.value("showHotkeysQml", True)
        if isinstance(raw_show_hotkeys, str):
            self._show_hotkeys = raw_show_hotkeys.strip().lower() not in {"0", "false", "no", "off", ""}
        else:
            self._show_hotkeys = bool(raw_show_hotkeys)

        self.settings = ProcessingSettings()
        self.settings.effect_stack = default_effect_stack(self.settings)
        self.layer_model = LayerListModel(self)
        self.layer_model.replace(self.settings.effect_stack)
        self._selected_layer = min(len(self.settings.effect_stack) - 1, 0)
        self._selected_layers: set[int] = {self._selected_layer} if self._selected_layer >= 0 else set()
        self._layer_clipboard: dict[str, Any] | None = None

        self._source_image: Any | None = None
        self._clipboard_source_image: Any | None = None
        self._current_frame: Any | None = None
        self._current_file: Path | None = None
        self._video_path: Path | None = None
        self._video_info: Any | None = None
        self._current_time = 0.0
        self._playback_speed = 1.0
        self._playback_mode = "Quick"
        self._preserve_audio = True
        self._playing = False
        self._rendered_frames: list[Any] = []
        self._rendered_times: list[float] = []
        self._rendered_fps = 0.0

        self._preview_mode = str(self.app_settings.value("previewModeQml", "Quick") or "Quick")
        if self._preview_mode not in {"Quick", "Stable", "Full"}:
            self._preview_mode = "Quick"
        self._preview_revision = 0
        self._preview_width = 1
        self._preview_height = 1
        self._source_revision = 0
        self._settings_revision = 0
        self._job_counter = 0
        self._latest_preview_job = 0
        self._preview_running = False
        self._pending_preview_side = 0
        self._preview_temporal_state: Any | None = None
        self._export_jobs: set[int] = set()
        self._status = ""
        self._render_busy = False
        self._render_progress = 0.0
        self._render_eta_seconds = -1.0
        self._render_stage = ""
        self._render_progress_visible = False
        self._render_started_at = 0.0
        self._render_job_id = 0
        self._render_estimate_key = ""
        self._render_estimates: dict[str, float] = {}
        self._history = UndoHistory(limit=120)
        self._screen_eyedropper_windows: list[_ScreenEyedropperWindow] = []
        self._screen_eyedropper_loupe: _ScreenEyedropperLoupe | None = None
        self._screen_eyedropper_loupe_timer = QTimer(self)
        self._screen_eyedropper_loupe_timer.setInterval(30)
        self._screen_eyedropper_loupe_timer.timeout.connect(self._update_screen_eyedropper_loupe)

        self._random_history: list[dict[str, Any]] = []
        self._random_index = -1
        self._hardware_profiles = load_builtin_profiles()
        self._palette_lab_data: dict[str, Any] = {}
        self._palette_mapping_data: list[dict[str, Any]] = []
        self._dither_matrix_library = self._load_dither_matrix_library()
        self._keyframe_clipboard: dict[str, Any] | None = None
        self._animation_clip_library = self._load_animation_clip_library()
        self._project_path: Path | None = None
        self._snapshot_a: dict[str, Any] | None = None
        self._snapshot_b: dict[str, Any] | None = None
        self._comparison_split = 0.5
        self._comparison_enabled = False
        self._benchmark_summary = ""
        # Created lazily on the first eligible preview so importing the QML
        # backend remains lightweight during application startup.
        self._layer_render_cache: Any | None = None

        # Initialize base-owned user-palette state without virtual dispatch.
        # PreferencesBackend overrides _load_user_palettes(); calling it from
        # this base constructor can run subclass code before the subclass has
        # created its own _user_palettes storage.
        self._user_palettes: list[dict[str, Any]] = []
        loaded_user_palettes = RasterMintBackend._load_user_palettes(self)
        if loaded_user_palettes is not None:
            self._user_palettes = loaded_user_palettes

        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(max(2, min(4, QThreadPool.globalInstance().maxThreadCount())))

        self._quick_timer = QTimer(self)
        self._quick_timer.setSingleShot(True)
        self._quick_timer.setInterval(55)
        self._quick_timer.timeout.connect(lambda: self._request_preview(self._quick_side()))
        self._stable_timer = QTimer(self)
        self._stable_timer.setSingleShot(True)
        self._stable_timer.setInterval(330)
        self._stable_timer.timeout.connect(self._request_refined_preview)
        self._play_timer = QTimer(self)
        self._play_timer.setInterval(33)
        self._play_timer.timeout.connect(self._play_tick)

    def _close_screen_eyedropper(self) -> None:
        self._screen_eyedropper_loupe_timer.stop()
        loupe = self._screen_eyedropper_loupe
        self._screen_eyedropper_loupe = None
        if loupe is not None:
            try:
                loupe.hide()
                loupe.close()
                loupe.deleteLater()
            except RuntimeError:
                pass

        windows = self._screen_eyedropper_windows
        self._screen_eyedropper_windows = []
        for window in windows:
            try:
                window.hide()
                window.close()
                window.deleteLater()
            except RuntimeError:
                pass

    def _update_screen_eyedropper_loupe(self) -> None:
        loupe = self._screen_eyedropper_loupe
        if loupe is None or not self._screen_eyedropper_windows:
            return

        point = QCursor.pos()
        screen = QGuiApplication.screenAt(point)
        if screen is None:
            return

        geometry = screen.geometry()
        radius = _ScreenEyedropperLoupe.SAMPLE_SIZE // 2
        sample_size = _ScreenEyedropperLoupe.SAMPLE_SIZE
        local_x = int(point.x() - geometry.x())
        local_y = int(point.y() - geometry.y())
        capture_left = local_x - radius
        capture_top = local_y - radius

        # Clip the desktop grab at monitor edges, then pad it back to a fixed
        # square so the cursor pixel always remains the center loupe cell.
        clipped_left = max(0, capture_left)
        clipped_top = max(0, capture_top)
        clipped_right = min(geometry.width(), capture_left + sample_size)
        clipped_bottom = min(geometry.height(), capture_top + sample_size)
        clipped_width = max(0, clipped_right - clipped_left)
        clipped_height = max(0, clipped_bottom - clipped_top)
        if clipped_width <= 0 or clipped_height <= 0:
            return

        pixmap = screen.grabWindow(
            0,
            int(clipped_left),
            int(clipped_top),
            int(clipped_width),
            int(clipped_height),
        )
        grabbed = pixmap.toImage()
        if grabbed.isNull():
            return
        if grabbed.width() != clipped_width or grabbed.height() != clipped_height:
            grabbed = grabbed.scaled(
                clipped_width,
                clipped_height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )

        sample = QImage(sample_size, sample_size, QImage.Format.Format_RGB32)
        sample.fill(QColor("#000000"))
        sample_painter = QPainter(sample)
        sample_painter.drawImage(
            int(clipped_left - capture_left),
            int(clipped_top - capture_top),
            grabbed,
        )
        sample_painter.end()
        center_color = sample.pixelColor(radius, radius)
        if not center_color.isValid():
            center_color = QColor("#000000")

        loupe.setScreen(screen)
        loupe.set_sample(sample, center_color)

        gap = 24
        x = point.x() + gap
        y = point.y() + gap
        screen_right = geometry.x() + geometry.width()
        screen_bottom = geometry.y() + geometry.height()
        if x + loupe.width() > screen_right:
            x = point.x() - gap - loupe.width()
        if y + loupe.height() > screen_bottom:
            y = point.y() - gap - loupe.height()
        x = max(geometry.x(), min(x, screen_right - loupe.width()))
        y = max(geometry.y(), min(y, screen_bottom - loupe.height()))
        loupe.setPosition(int(x), int(y))
        if not loupe.isVisible():
            loupe.show()

    def _cancel_screen_eyedropper(self) -> None:
        if not self._screen_eyedropper_windows:
            return
        self._close_screen_eyedropper()
        self.screenEyedropperCancelled.emit()

    def _capture_screen_color(self, global_x: int, global_y: int) -> None:
        # Remove the transparent hit windows before grabbing the pixel so the
        # sample is the exact desktop/application colour underneath them.
        self._close_screen_eyedropper()

        def capture() -> None:
            point = QCursor.pos()
            # Keep the click coordinates authoritative; QCursor is only a
            # fallback for platforms that report an invalid global event point.
            if global_x or global_y:
                from PySide6.QtCore import QPoint
                point = QPoint(int(global_x), int(global_y))
            screen = QGuiApplication.screenAt(point)
            if screen is None:
                screen = QGuiApplication.primaryScreen()
            if screen is None:
                self.screenEyedropperCancelled.emit()
                return

            geometry = screen.geometry()
            local_x = int(point.x() - geometry.x())
            local_y = int(point.y() - geometry.y())
            pixmap = screen.grabWindow(0, local_x, local_y, 1, 1)
            image = pixmap.toImage()
            if image.isNull() or image.width() < 1 or image.height() < 1:
                self.screenEyedropperCancelled.emit()
                return
            color = image.pixelColor(0, 0)
            if not color.isValid():
                self.screenEyedropperCancelled.emit()
                return
            self.screenColorPicked.emit(color.name(QColor.NameFormat.HexRgb).upper())

            for window in QGuiApplication.topLevelWindows():
                if window not in self._screen_eyedropper_windows and window.isVisible():
                    try:
                        window.requestActivate()
                        break
                    except RuntimeError:
                        pass

        # Let the compositor remove the overlay before reading the desktop.
        QTimer.singleShot(0, capture)

    @Slot()
    def startScreenEyedropper(self) -> None:
        self._close_screen_eyedropper()
        screens = list(QGuiApplication.screens())
        if not screens:
            self.screenEyedropperCancelled.emit()
            return

        for screen in screens:
            window = _ScreenEyedropperWindow(screen)
            window.picked.connect(self._capture_screen_color)
            window.cancelled.connect(self._cancel_screen_eyedropper)
            self._screen_eyedropper_windows.append(window)
            window.show()

        self._screen_eyedropper_loupe = _ScreenEyedropperLoupe()
        self._update_screen_eyedropper_loupe()
        self._screen_eyedropper_loupe_timer.start()

        cursor_screen = QGuiApplication.screenAt(QCursor.pos())
        active = next(
            (window for window in self._screen_eyedropper_windows if window.screen() is cursor_screen),
            self._screen_eyedropper_windows[0],
        )
        QTimer.singleShot(0, active.requestActivate)

    # ---------- exposed models/data ----------
    @Property(QObject, constant=True)
    def layerModel(self) -> QObject:
        return self.layer_model

    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    @Property(bool, notify=sourceChanged)
    def hasSource(self) -> bool:
        return self._active_source() is not None

    @Property(str, notify=sourceChanged)
    def currentFileName(self) -> str:
        if self._current_file:
            return self._current_file.name
        if self._source_image is not None:
            return _tr("Clipboard Image")
        return ""

    @Property(str, notify=sourceChanged)
    def sourceInfo(self) -> str:
        source = self._active_source()
        if source is None:
            return ""
        if self._video_info:
            return f"{source.width} × {source.height} · {self._video_info.duration:.2f}s · {self._video_info.fps:.2f} fps"
        return f"{source.width} × {source.height}"

    @Property(int, notify=previewChanged)
    def previewRevision(self) -> int:
        return self._preview_revision

    @Property(int, notify=previewChanged)
    def previewWidth(self) -> int:
        return self._preview_width

    @Property(int, notify=previewChanged)
    def previewHeight(self) -> int:
        return self._preview_height

    @Property(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status

    @Property(bool, notify=renderProgressChanged)
    def renderBusy(self) -> bool:
        return self._render_busy

    @Property(float, notify=renderProgressChanged)
    def renderProgress(self) -> float:
        return self._render_progress

    @Property(float, notify=renderProgressChanged)
    def renderEtaSeconds(self) -> float:
        return self._render_eta_seconds

    @Property(bool, notify=renderProgressChanged)
    def renderProgressVisible(self) -> bool:
        return self._render_progress_visible

    @Property(str, notify=renderProgressChanged)
    def renderStage(self) -> str:
        return self._render_stage

    @Property(bool, notify=showHotkeysChanged)
    def showHotkeys(self) -> bool:
        return self._show_hotkeys

    @Slot(bool)
    def setShowHotkeys(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if self._show_hotkeys == enabled:
            return
        self._show_hotkeys = enabled
        self.app_settings.setValue("showHotkeysQml", enabled)
        self.showHotkeysChanged.emit()

    @Property(bool, notify=historyChanged)
    def canUndo(self) -> bool:
        return self._history.can_undo

    @Property(bool, notify=historyChanged)
    def canRedo(self) -> bool:
        return self._history.can_redo

    @Property(str, notify=settingsChanged)
    def previewMode(self) -> str:
        return self._preview_mode

    @Property("QVariantMap", notify=settingsChanged)
    def settingsMap(self) -> dict[str, Any]:
        return self.settings.to_dict()

    @Property("QStringList", constant=True)
    def layerKinds(self) -> list[str]:
        return list(EFFECT_DEFINITIONS.keys())

    @Property("QVariantList", constant=True)
    def layerCategories(self) -> list[dict[str, Any]]:
        return effect_categories()

    @Property(int, notify=layerSelectionChanged)
    def selectedLayerIndex(self) -> int:
        return self._selected_layer

    @Property(str, notify=layerSelectionChanged)
    def selectedLayerName(self) -> str:
        item = self.layer_model.item(self._selected_layer)
        return str(item.get("kind", "Layer")) if item else "Layer"

    @Property("QStringList", constant=True)
    def layerBlendModes(self) -> list[str]:
        return list(BLEND_MODES)

    @Property("QStringList", constant=True)
    def layerMaskTypes(self) -> list[str]:
        return list(MASK_TYPES)

    @Property("QVariantList", notify=layerWorkflowChanged)
    def selectedLayerIndices(self) -> list[int]:
        return sorted(i for i in self._selected_layers if 0 <= i < len(self.settings.effect_stack))

    @Property(float, notify=layerSelectionChanged)
    def selectedLayerOpacity(self) -> float:
        item = self.layer_model.item(self._selected_layer)
        return float(item.get("opacity", 1.0) or 0.0) if item else 1.0

    @Property(str, notify=layerSelectionChanged)
    def selectedLayerBlendMode(self) -> str:
        item = self.layer_model.item(self._selected_layer)
        return str(item.get("blend_mode", "Normal") or "Normal") if item else "Normal"

    @Property("QVariantMap", notify=layerSelectionChanged)
    def selectedLayerMask(self) -> dict[str, Any]:
        item = self.layer_model.item(self._selected_layer)
        return dict(item.get("mask") or default_layer_mask()) if item else default_layer_mask()

    @Property(bool, notify=layerWorkflowChanged)
    def layerClipboardAvailable(self) -> bool:
        return self._layer_clipboard is not None

    @Property(bool, notify=settingsChanged)
    def selectedLayerSolo(self) -> bool:
        item = self.layer_model.item(self._selected_layer)
        return bool(item and str(item.get("id", "")) == str(self.settings.solo_layer_id or ""))

    @Property("QVariantList", notify=settingsChanged)
    def layerGroups(self) -> list[dict[str, Any]]:
        return [dict(group) for group in self.settings.layer_groups]

    @Property("QVariantList", notify=layerSelectionChanged)
    def selectedLayerParams(self) -> list[dict[str, Any]]:
        item = self.layer_model.item(self._selected_layer)
        if not item:
            return []
        kind = str(item.get("kind", ""))
        definition = EFFECT_DEFINITIONS.get(kind, {})
        values = item.get("params") if isinstance(item.get("params"), dict) else {}
        result = []
        current_font = str(values.get("font", "Mono"))
        current_character_set = str(values.get("character_set", "Classic ASCII"))
        current_custom_chars = str(values.get("custom_chars", " .:-=+*#%@"))
        current_inject_chars = str(values.get("inject_chars", ""))
        current_cell_size = int(values.get("cell_size", 10) or 10)
        current_font_scale = float(values.get("font_scale", 0.9) or 0.9)
        current_font_size = max(2, round(current_cell_size * max(0.4, min(1.5, current_font_scale))))
        for key, spec in definition.get("params", {}).items():
            row = dict(spec)
            row["key"] = key
            row["value"] = values.get(key, spec.get("default"))
            row["options"] = list(spec.get("options", []))
            row["suffix"] = str(spec.get("suffix", ""))
            if kind == "ASCII / Glyph" and key == "depth":
                from rastermint.core.effect_stack import ascii_depth_max
                row["max"] = ascii_depth_max(
                    current_character_set,
                    current_custom_chars,
                    current_font,
                    current_font_size,
                    current_inject_chars,
                )
                try:
                    row["value"] = min(int(row["value"]), int(row["max"]))
                except (TypeError, ValueError):
                    row["value"] = min(int(spec.get("default", 10)), int(row["max"]))
            target_id = f"effect:{item.get('id', '')}:{key}"
            row["animated"] = any(
                track.get("enabled", True) and str(track.get("target", "")) == target_id
                for track in normalize_tracks(self.settings.animation_tracks)
            )
            result.append(row)
        return result

    _USER_PALETTES_SETTINGS_KEY = "userPalettesV1"

    @staticmethod
    def _palette_slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-")
        return slug or "palette"

    @staticmethod
    def _normalized_user_palette(item: object) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None
        name = str(item.get("name", "")).strip()
        category = str(item.get("category", "Custom")).strip() or "Custom"
        colors = [str(color).strip().upper() for color in list(item.get("colors") or []) if str(color).strip()]
        if not name or not colors:
            return None
        palette_id = str(item.get("id", "")).strip() or f"user-palette-{RasterMintBackend._palette_slug(name)}"
        return {
            "id": palette_id,
            "name": name,
            "category": category,
            "description": str(item.get("description", "User palette")).strip() or "User palette",
            "colors": colors[:256],
            "user": True,
        }

    def _load_user_palettes(self) -> list[dict[str, Any]]:
        raw = self.app_settings.value(self._USER_PALETTES_SETTINGS_KEY, "[]")
        try:
            payload = json.loads(str(raw or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = []
        result: list[dict[str, Any]] = []
        for item in payload if isinstance(payload, list) else []:
            normalized = self._normalized_user_palette(item)
            if normalized is not None:
                result.append(normalized)
        return result

    def _save_user_palettes(self) -> None:
        self.app_settings.setValue(self._USER_PALETTES_SETTINGS_KEY, json.dumps(self._user_palettes, ensure_ascii=False))
        self.app_settings.sync()

    @Property("QVariantList", constant=True)
    def gradientPresets(self) -> list[dict[str, Any]]:
        return [
            {
                "name": str(item["name"]),
                "colors": list(item["colors"]),
                "positions": list(item["positions"]),
            }
            for item in GRADIENT_PRESETS
        ]

    @Property("QVariantList", notify=paletteLibraryChanged)
    def paletteLibrary(self) -> list[dict[str, Any]]:
        builtins = [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "description": p.description,
                "colors": list(p.colors),
                "user": False,
            }
            for p in PALETTE_LIBRARY
        ]
        return builtins + [dict(item) for item in self._user_palettes]

    def _find_user_palette(self, name_or_id: str) -> dict[str, Any] | None:
        needle = str(name_or_id).strip()
        for palette in self._user_palettes:
            if needle == str(palette.get("id", "")) or needle == str(palette.get("name", "")):
                return palette
        return None

    @Property("QVariantMap", notify=paletteLabChanged)
    def paletteLabData(self) -> dict[str, Any]:
        return dict(self._palette_lab_data)

    @Property("QVariantList", notify=paletteLabChanged)
    def paletteMappingData(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._palette_mapping_data]

    @Slot()
    def refreshPaletteLab(self) -> None:
        try:
            self._palette_lab_data = _palette_analysis(
                list(self.settings.palette),
                self._active_source(),
                max_pixels=60_000,
            )
        except Exception as exc:
            self._palette_lab_data = {"error": str(exc)}
        self.paletteLabChanged.emit()

    @Slot(str)
    def sortPalette(self, mode: str) -> None:
        old_colors = list(self.settings.palette)
        old_locks = list(self.settings.palette_locks)
        sorted_colors = _sort_palette(old_colors, mode)
        if sorted_colors == old_colors:
            return
        # Preserve lock association even when a palette contains duplicate hexes.
        remaining = list(enumerate(old_colors))
        sorted_locks: list[bool] = []
        for color in sorted_colors:
            match = next((pair for pair in remaining if pair[1] == color), remaining[0])
            remaining.remove(match)
            sorted_locks.append(bool(old_locks[match[0]]) if match[0] < len(old_locks) else False)
        data = self.settings.to_dict()
        data["palette"] = sorted_colors
        data["palette_locks"] = sorted_locks
        data["palette_name"] = "Custom"
        self._replace_settings(ProcessingSettings.from_dict(data), action=f"Palette sorted by {mode}")
        self.refreshPaletteLab()

    @Slot()
    def removeUnusedPaletteColors(self) -> None:
        if not self._palette_lab_data:
            self.refreshPaletteLab()
        rows = list(self._palette_lab_data.get("colors") or [])
        if not rows:
            return
        keep = [int(row["index"]) for row in rows if not bool(row.get("unused", False))]
        if len(keep) < 1 or len(keep) == len(self.settings.palette):
            self._set_status("No unused palette colours to remove")
            return
        data = self.settings.to_dict()
        data["palette"] = [self.settings.palette[i] for i in keep]
        data["palette_locks"] = [self.settings.palette_locks[i] for i in keep]
        data["palette_name"] = "Custom"
        self._replace_settings(ProcessingSettings.from_dict(data), action=f"Removed {len(self.settings.palette) - len(keep)} unused palette colours")
        self.refreshPaletteLab()

    @Slot()
    def applyPaletteReductionSuggestion(self) -> None:
        if not self._palette_lab_data:
            self.refreshPaletteLab()
        target = int(self._palette_lab_data.get("suggested_count", len(self.settings.palette)) or len(self.settings.palette))
        target = max(1, min(len(self.settings.palette), target))
        if target >= len(self.settings.palette):
            self._set_status("Palette is already compact")
            return
        source = self._active_source()
        if source is None:
            # Without an image, remove the least-separated colours first.
            duplicates = list(self._palette_lab_data.get("near_duplicates") or [])
            remove = {int(item.get("b", -1)) for item in duplicates if int(item.get("b", -1)) >= 0}
            keep = [i for i in range(len(self.settings.palette)) if i not in remove][:target]
            if len(keep) < target:
                keep.extend(i for i in range(len(self.settings.palette)) if i not in keep and len(keep) < target)
            colors = [self.settings.palette[i] for i in keep]
        else:
            from rastermint.core.palette import extract_palette
            colors = extract_palette(source, colors=target, method="K-Means")
        data = self.settings.to_dict()
        data["palette"] = list(colors)
        data["palette_locks"] = [False] * len(colors)
        data["palette_name"] = "Custom"
        self._replace_settings(ProcessingSettings.from_dict(data), action=f"Reduced palette to {len(colors)} colours")
        self.refreshPaletteLab()

    @Slot(str)
    def analyzePaletteMapping(self, palette_id_or_name: str) -> None:
        target_colors: list[str] = []
        needle = str(palette_id_or_name or "")
        for record in self.paletteLibrary:
            if needle in {str(record.get("id", "")), str(record.get("name", ""))}:
                target_colors = list(record.get("colors") or [])
                break
        if not target_colors:
            self._palette_mapping_data = []
        else:
            self._palette_mapping_data = _palette_mapping(list(self.settings.palette), target_colors)
        self.paletteLabChanged.emit()

    _DITHER_MATRIX_SETTINGS_KEY = "customDitherMatricesV1"

    def _load_dither_matrix_library(self) -> list[dict[str, Any]]:
        raw = self.app_settings.value(self._DITHER_MATRIX_SETTINGS_KEY, "[]")
        try:
            payload = json.loads(str(raw or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = []
        result: list[dict[str, Any]] = []
        for item in payload if isinstance(payload, list) else []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            matrix = item.get("matrix")
            if name and isinstance(matrix, list) and 2 <= len(matrix) <= 16 and all(isinstance(row, list) and len(row) == len(matrix) for row in matrix):
                result.append({"name": name, "matrix": matrix})
        return result

    def _save_dither_matrix_library(self) -> None:
        self.app_settings.setValue(self._DITHER_MATRIX_SETTINGS_KEY, json.dumps(self._dither_matrix_library, ensure_ascii=False))
        self.app_settings.sync()

    def _dither_layer_index(self) -> int:
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        return next((i for i, step in enumerate(stack) if str(step.get("kind")) == "Dither"), -1)

    def _current_dither_matrix(self) -> list[list[float]]:
        index = self._dither_layer_index()
        if index < 0:
            return [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
        raw = self.settings.effect_stack[index].get("params", {}).get("custom_matrix_json", "")
        try:
            matrix = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            matrix = None
        if not isinstance(matrix, list) or not (2 <= len(matrix) <= 16) or not all(isinstance(row, list) and len(row) == len(matrix) for row in matrix):
            return [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
        return [[float(value) for value in row] for row in matrix]

    @Property("QVariantList", notify=settingsChanged)
    def customDitherMatrix(self) -> list[list[float]]:
        return self._current_dither_matrix()

    @Property(int, notify=settingsChanged)
    def customDitherMatrixSize(self) -> int:
        return len(self._current_dither_matrix())

    @Property("QVariantList", notify=ditherMatrixLibraryChanged)
    def ditherMatrixLibrary(self) -> list[dict[str, Any]]:
        return deepcopy(self._dither_matrix_library)

    def _set_custom_dither_matrix(self, matrix: list[list[float]], action: str) -> None:
        index = self._dither_layer_index()
        if index < 0:
            return
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        stack[index]["params"]["custom_matrix_json"] = json.dumps(matrix, separators=(",", ":"))
        data = self.settings.to_dict()
        data["effect_stack"] = stack
        self._replace_settings(ProcessingSettings.from_dict(data), action=action, selected_layer=self._selected_layer)

    @Slot(int)
    def setCustomDitherMatrixSize(self, size: int) -> None:
        size = max(2, min(16, int(size)))
        old = self._current_dither_matrix()
        matrix = [[float((y * size + x) % (size * size)) for x in range(size)] for y in range(size)]
        for y in range(min(size, len(old))):
            for x in range(min(size, len(old[y]))):
                matrix[y][x] = float(old[y][x])
        self._set_custom_dither_matrix(matrix, f"Custom dither matrix: {size}×{size}")

    @Slot(int, int, float)
    def setCustomDitherMatrixCell(self, row: int, column: int, value: float) -> None:
        matrix = self._current_dither_matrix()
        row, column = int(row), int(column)
        if not (0 <= row < len(matrix) and 0 <= column < len(matrix)):
            return
        matrix[row][column] = float(value)
        self._set_custom_dither_matrix(matrix, f"Dither matrix cell {row + 1},{column + 1}: {value:g}")

    @Slot()
    def resetCustomDitherMatrix(self) -> None:
        matrix = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
        self._set_custom_dither_matrix(matrix, "Reset custom dither matrix")

    @Slot(str)
    def saveCustomDitherMatrix(self, name: str) -> None:
        clean = str(name or "").strip() or "Custom Matrix"
        matrix = self._current_dither_matrix()
        existing = next((item for item in self._dither_matrix_library if str(item.get("name", "")).casefold() == clean.casefold()), None)
        if existing is None:
            self._dither_matrix_library.append({"name": clean, "matrix": matrix})
        else:
            existing["matrix"] = matrix
        self._save_dither_matrix_library()
        self.ditherMatrixLibraryChanged.emit()
        self._set_status(f"Saved dither matrix: {clean}")

    @Slot(str)
    def loadCustomDitherMatrix(self, name: str) -> None:
        record = next((item for item in self._dither_matrix_library if str(item.get("name", "")) == str(name)), None)
        if record:
            self._set_custom_dither_matrix(deepcopy(record["matrix"]), f"Dither matrix: {name}")

    @Property("QStringList", constant=True)
    def paletteOptimizerNames(self) -> list[str]:
        return list(PALETTE_OPTIMIZERS)

    @Property("QStringList", notify=hardwareProfilesChanged)
    def hardwareProfileNames(self) -> list[str]:
        return [p.name for p in self._hardware_profiles]

    @Property("QStringList", notify=hardwareProfilesChanged)
    def hardwareProfileIds(self) -> list[str]:
        return [p.id for p in self._hardware_profiles]

    @Property("QVariantList", notify=hardwareProfilesChanged)
    def hardwareProfiles(self) -> list[dict[str, Any]]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "summary": p.summary,
                "visualTooltip": profile_summary(p, "visual"),
                "strictTooltip": profile_summary(p, "strict"),
            }
            for p in self._hardware_profiles
        ]

    @Property("QStringList", constant=True)
    def paletteNames(self) -> list[str]:
        return [p.name for p in PALETTE_LIBRARY]

    @Property("QStringList", constant=True)
    def builtinPresetNames(self) -> list[str]:
        return [p.name for p in BUILTIN_PRESETS]

    @Property("QStringList", constant=True)
    def builtinPresetIds(self) -> list[str]:
        return [p.id for p in BUILTIN_PRESETS]

    @Property("QVariantList", constant=True)
    def builtinPresets(self) -> list[dict[str, Any]]:
        return [{"id": p.id, "name": p.name, "description": p.description} for p in BUILTIN_PRESETS]

    @Property("QStringList", constant=True)
    def animationPresetNames(self) -> list[str]:
        return [p.name for p in ANIMATION_PRESETS]

    @Property("QStringList", constant=True)
    def animationPresetIds(self) -> list[str]:
        return [p.id for p in ANIMATION_PRESETS]

    @Property("QVariantList", constant=True)
    def animationPresets(self) -> list[dict[str, Any]]:
        return [{"id": p.id, "name": p.name, "description": p.description} for p in ANIMATION_PRESETS]

    @Property(float, notify=playbackChanged)
    def currentTime(self) -> float:
        return self._current_time

    @Property(float, notify=playbackChanged)
    def timelineDuration(self) -> float:
        if self._video_info:
            return max(0.01, self._video_info.duration)
        return max(0.01, self.settings.animation_duration)

    @Property(bool, notify=playbackChanged)
    def playing(self) -> bool:
        return self._playing

    @Property(str, notify=playbackChanged)
    def playbackMode(self) -> str:
        return self._playback_mode

    @Property(float, notify=playbackChanged)
    def playbackSpeed(self) -> float:
        return self._playback_speed

    @Property(bool, notify=renderedPreviewChanged)
    def renderedPreviewReady(self) -> bool:
        return bool(self._rendered_frames)

    @Property(bool, notify=audioExportChanged)
    def preserveAudio(self) -> bool:
        return self._preserve_audio

    @Property(bool, notify=settingsChanged)
    def audioEnvelopeReady(self) -> bool:
        return bool(self.settings.audio_envelope)

    @Property(int, notify=settingsChanged)
    def audioEnvelopeSamples(self) -> int:
        return len(self.settings.audio_envelope)

    @Slot()
    def analyzeAudioModulation(self) -> None:
        path = self._video_path or self._current_file
        if path is None:
            self.errorOccurred.emit("Audio analysis", "Load a video or media file with an audio track first.")
            return
        job = self._next_job()
        worker = AudioEnvelopeWorker(job, str(path), 30.0)
        self._connect_worker(worker)
        self.thread_pool.start(worker)
        self._set_status("Analysing audio amplitude…")

    @Property("QStringList", constant=True)
    def easingNames(self) -> list[str]:
        return list(EASINGS)

    @Property("QStringList", constant=True)
    def modulatorNames(self) -> list[str]:
        return list(MODULATORS)

    @Property("QVariantList", notify=settingsChanged)
    def animationTargets(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for step in normalize_effect_stack(self.settings.effect_stack, self.settings):
            kind = str(step.get("kind", "Layer"))
            effect_id = str(step.get("id", ""))
            params = step.get("params") if isinstance(step.get("params"), dict) else {}
            definition = EFFECT_DEFINITIONS.get(kind, {})
            for key, spec in definition.get("params", {}).items():
                if not spec.get("animatable", False) or spec.get("type") not in {"int", "float", "duration"}:
                    continue
                value = params.get(key, spec.get("default", 0.0))
                result.append({
                    "id": f"effect:{effect_id}:{key}",
                    "label": f"{kind} · {spec.get('label', key)}",
                    "default": float(value),
                    "min": float(spec.get("min", -10000.0)),
                    "max": float(spec.get("max", 10000.0)),
                    "decimals": int(spec.get("decimals", 0 if spec.get("type") == "int" else 2)),
                })
            result.append({
                "id": f"effect:{effect_id}:__opacity__",
                "label": f"{kind} · Opacity",
                "default": float(step.get("opacity", 1.0)),
                "min": 0.0,
                "max": 1.0,
                "decimals": 2,
            })
        return result

    @Property("QStringList", notify=settingsChanged)
    def animationTargetNames(self) -> list[str]:
        return [str(item["label"]) for item in self.animationTargets]

    @Property("QStringList", notify=settingsChanged)
    def animationTargetIds(self) -> list[str]:
        return [str(item["id"]) for item in self.animationTargets]

    @Property("QVariantList", notify=settingsChanged)
    def animationTracks(self) -> list[dict[str, Any]]:
        labels = {item["id"]: item["label"] for item in self.animationTargets}
        result: list[dict[str, Any]] = []
        for index, track in enumerate(normalize_tracks(self.settings.animation_tracks)):
            row = dict(track)
            row["index"] = index
            row["label"] = labels.get(str(track.get("target", "")), str(track.get("target", "Parameter")))
            result.append(row)
        return result

    @Property(str, notify=projectChanged)
    def projectPath(self) -> str:
        return str(self._project_path) if self._project_path else ""

    @Property(str, notify=projectChanged)
    def projectName(self) -> str:
        return self._project_path.stem if self._project_path else ""

    @Property(bool, notify=comparisonChanged)
    def snapshotAReady(self) -> bool:
        return self._snapshot_a is not None

    @Property(bool, notify=comparisonChanged)
    def snapshotBReady(self) -> bool:
        return self._snapshot_b is not None

    @Property(float, notify=comparisonChanged)
    def comparisonSplit(self) -> float:
        return float(self._comparison_split)

    @Property(bool, notify=comparisonChanged)
    def comparisonEnabled(self) -> bool:
        return bool(self._comparison_enabled and self._snapshot_a is not None and self._snapshot_b is not None)

    def _project_extra_state(self) -> dict[str, Any]:
        return {}

    def _restore_project_extra_state(self, payload: dict[str, Any]) -> None:
        del payload

    @Slot(str)
    def saveProject(self, value: str) -> None:
        try:
            from rastermint.core.project import save_project_file
            path = Path(_local_path(value))
            source_ref = str(self._current_file) if self._current_file else ""
            payload = {
                "app_version": self.version,
                "source": {"path": source_ref, "kind": "video" if self._video_path else ("image" if source_ref else "clipboard")},
                "settings": self.settings.to_dict(),
                "timeline": {
                    "current_time": float(self._current_time),
                    "playback_mode": str(self._playback_mode),
                    "playback_speed": float(self._playback_speed),
                },
                "ui": {"selected_layer": int(self._selected_layer), "preview_mode": str(self._preview_mode)},
                "snapshots": {"a": deepcopy(self._snapshot_a), "b": deepcopy(self._snapshot_b), "split": float(self._comparison_split)},
                "export": self._project_extra_state(),
            }
            self._project_path = save_project_file(path, payload)
            self.projectChanged.emit()
            self._set_status(f"Saved project: {self._project_path.name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not save project", str(exc))

    @Slot(str)
    def loadProject(self, value: str) -> None:
        try:
            from rastermint.core.project import load_project_file
            path = Path(_local_path(value))
            payload = load_project_file(path)
            source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
            source_path = Path(str(source.get("path", ""))) if str(source.get("path", "")) else None
            if source_path is not None:
                if not source_path.exists():
                    raise FileNotFoundError(f"Project source file is missing: {source_path}")
                self.openFile(str(source_path))
            settings_payload = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
            loaded = ProcessingSettings.from_dict(settings_payload)
            ui = payload.get("ui") if isinstance(payload.get("ui"), dict) else {}
            selected = int(ui.get("selected_layer", 0) or 0)
            self._replace_settings(loaded, action=f"Loaded project: {path.name}", selected_layer=selected, record_history=False)
            self._preview_mode = str(ui.get("preview_mode", self._preview_mode) or self._preview_mode)
            timeline = payload.get("timeline") if isinstance(payload.get("timeline"), dict) else {}
            self._current_time = max(0.0, min(self.timelineDuration, float(timeline.get("current_time", 0.0) or 0.0)))
            self._playback_mode = str(timeline.get("playback_mode", self._playback_mode) or self._playback_mode)
            self._playback_speed = float(timeline.get("playback_speed", self._playback_speed) or self._playback_speed)
            snapshots = payload.get("snapshots") if isinstance(payload.get("snapshots"), dict) else {}
            self._snapshot_a = deepcopy(snapshots.get("a")) if isinstance(snapshots.get("a"), dict) else None
            self._snapshot_b = deepcopy(snapshots.get("b")) if isinstance(snapshots.get("b"), dict) else None
            self._comparison_split = max(0.0, min(1.0, float(snapshots.get("split", 0.5) or 0.5)))
            self._restore_project_extra_state(payload.get("export") if isinstance(payload.get("export"), dict) else {})
            self._project_path = path
            self.projectChanged.emit()
            self.comparisonChanged.emit()
            self.playbackChanged.emit()
            self.schedulePreview(force=True)
            self._set_status(f"Loaded project: {path.name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not load project", str(exc))

    @Slot(str)
    def captureSnapshot(self, slot: str) -> None:
        payload = self.settings.to_dict()
        if str(slot).upper() == "A":
            self._snapshot_a = payload
            self.provider.set_image("snapshot-a", self.provider.get_image("preview"))
        else:
            self._snapshot_b = payload
            self.provider.set_image("snapshot-b", self.provider.get_image("preview"))
        self.comparisonChanged.emit()
        self._set_status(f"Captured snapshot {str(slot).upper()}")

    @Slot(str)
    def applySnapshot(self, slot: str) -> None:
        payload = self._snapshot_a if str(slot).upper() == "A" else self._snapshot_b
        if payload is not None:
            self._replace_settings(ProcessingSettings.from_dict(deepcopy(payload)), action=f"Applied snapshot {str(slot).upper()}")

    @Slot(float)
    def setComparisonSplit(self, value: float) -> None:
        self._comparison_split = max(0.0, min(1.0, float(value)))
        self.comparisonChanged.emit()

    @Slot(bool)
    def setComparisonEnabled(self, enabled: bool) -> None:
        self._comparison_enabled = bool(enabled)
        self.comparisonChanged.emit()

    # ---------- basic mutation ----------
    def _active_source(self) -> Any | None:
        return self._current_frame or self._source_image

    def _set_status(self, text: str) -> None:
        self._status = str(text)
        self.statusChanged.emit()

    @Slot(str)
    def reportAction(self, text: str) -> None:
        self._set_status(str(text))

    def _next_job(self) -> int:
        self._job_counter += 1
        return self._job_counter

    def _invalidate_rendered(self) -> None:
        self._rendered_frames = []
        self._rendered_times = []
        self._rendered_fps = 0.0
        self.renderedPreviewChanged.emit()

    def _reset_preview_temporal_state(self) -> None:
        # Do not mutate a state object that may still be owned by a running
        # preview worker. Dropping our reference is enough; the worker can
        # finish safely and the old history is then collected.
        self._preview_temporal_state = None

    def _history_state(self) -> dict[str, Any]:
        return {
            "settings": self.settings.to_dict(),
            "selected_layer": int(self._selected_layer),
            "selected_layers": sorted(self._selected_layers),
            "preserve_audio": bool(self._preserve_audio),
            "preview_mode": str(self._preview_mode),
        }

    def _restore_history_state(self, state: dict[str, Any]) -> None:
        settings = ProcessingSettings.from_dict(dict(state.get("settings") or {}))
        self._selected_layer = max(0, int(state.get("selected_layer", 0)))
        raw_selected = state.get("selected_layers", [self._selected_layer])
        self._selected_layers = {int(i) for i in raw_selected if isinstance(i, (int, float)) and int(i) >= 0}
        if not self._selected_layers:
            self._selected_layers = {self._selected_layer}
        self._preserve_audio = bool(state.get("preserve_audio", self._preserve_audio))
        preview_mode = str(state.get("preview_mode", self._preview_mode)).title()
        if preview_mode in {"Quick", "Stable", "Full"}:
            self._preview_mode = preview_mode
            self.app_settings.setValue("previewModeQml", preview_mode)
        self._replace_settings(settings, record_history=False)
        self.audioExportChanged.emit()
        self.historyChanged.emit()

    @staticmethod
    def _pretty_key(key: str) -> str:
        labels = {
            "target_enabled": "Target raster", "target_width": "Raster width", "target_height": "Raster height",
            "keep_aspect": "Keep aspect ratio", "fit_mode": "Fit mode", "position_x": "Fill position X",
            "position_y": "Fill position Y", "pixel_aspect_x": "Pixel aspect width", "pixel_aspect_y": "Pixel aspect height",
            "display_mode": "Display view", "display_export": "Display view on export", "crop_left": "Crop left",
            "crop_right": "Crop right", "crop_top": "Crop top", "crop_bottom": "Crop bottom",
            "animation_duration": "Animation duration", "animation_fps": "Animation FPS", "animation_loop": "Animation loop",
            "random_locks": "Randomize locks",
        }
        return labels.get(str(key), str(key).replace("_", " ").strip().title())

    @staticmethod
    def _format_action_value(value: Any, *, decimals: int | None = None, suffix: str = "") -> str:
        if isinstance(value, bool):
            return "On" if value else "Off"
        if isinstance(value, (dict, list, tuple)):
            return "Updated"
        if isinstance(value, float):
            if decimals is None:
                decimals = 2
            text = f"{value:.{max(0, decimals)}f}"
        else:
            text = str(value)
        return text + str(suffix or "")

    def _replace_settings(
        self,
        settings: ProcessingSettings,
        *,
        schedule: bool = True,
        action: str | None = None,
        selected_layer: int | None = None,
        record_history: bool = True,
    ) -> bool:
        settings.effect_stack = normalize_effect_stack(settings.effect_stack, settings)
        canonical = ProcessingSettings.from_dict(settings.to_dict())
        desired_layer = self._selected_layer if selected_layer is None else int(selected_layer)
        desired_layer = max(0, min(desired_layer, max(0, len(canonical.effect_stack) - 1)))
        if canonical.to_dict() == self.settings.to_dict() and desired_layer == self._selected_layer:
            return False
        if action and record_history:
            self._history.record(self._history_state(), action)
            self.historyChanged.emit()
        self.settings = canonical
        self._selected_layer = desired_layer
        self._selected_layers = {desired_layer} if canonical.effect_stack else set()
        self.layer_model.replace(self.settings.effect_stack)
        self._settings_revision += 1
        self._reset_preview_temporal_state()
        self._invalidate_rendered()
        self.settingsChanged.emit()
        self.layerSelectionChanged.emit()
        self.layerWorkflowChanged.emit()
        if schedule and self.hasSource:
            self.schedulePreview()
        if action:
            self._set_status(action)
        return True

    @Slot(str)
    def beginHistoryGroup(self, action: str) -> None:
        self._history.begin_group(str(action))

    @Slot()
    def endHistoryGroup(self) -> None:
        self._history.end_group()

    @Slot()
    def undo(self) -> None:
        restored = self._history.undo(self._history_state())
        if restored is None:
            self._set_status("Nothing to undo")
            return
        state, action = restored
        self._restore_history_state(state)
        self._set_status(f"Undo: {action}")

    @Slot()
    def redo(self) -> None:
        restored = self._history.redo(self._history_state())
        if restored is None:
            self._set_status("Nothing to redo")
            return
        state, action = restored
        self._restore_history_state(state)
        self._set_status(f"Redo: {action}")

    def _target_source_size(self) -> tuple[int, int]:
        source = self._active_source()
        if source is not None:
            return max(1, int(source.width)), max(1, int(source.height))
        width = max(1, int(self.settings.target_width or 1))
        height = max(1, int(self.settings.target_height or 1))
        return width, height

    def _linked_target_size(self, *, width: int | None = None, height: int | None = None) -> tuple[int, int]:
        from rastermint.core.processor import linked_target_size
        return linked_target_size(
            self._target_source_size(),
            self.settings,
            width=width,
            height=height,
        )

    @Slot(str, "QVariant")
    def setSetting(self, key: str, value: Any) -> None:
        key = str(key)
        if not hasattr(self.settings, key):
            return
        if key == "target_width":
            self.setTargetRasterWidth(int(value))
            return
        if key == "target_height":
            self.setTargetRasterHeight(int(value))
            return

        data = self.settings.to_dict()
        data[key] = value

        if key == "target_enabled" and bool(value):
            if int(data.get("target_width", 0)) <= 0 or int(data.get("target_height", 0)) <= 0:
                from rastermint.core.processor import source_raster_size
                width, height = source_raster_size(self._target_source_size(), self.settings)
                data["target_width"] = width
                data["target_height"] = height
        elif key == "keep_aspect" and bool(value) and bool(data.get("target_enabled", False)):
            current_width = max(1, int(data.get("target_width", 1) or 1))
            width, height = self._linked_target_size(width=current_width)
            data["target_width"] = width
            data["target_height"] = height

        action = f"{self._pretty_key(key)}: {self._format_action_value(value)}"
        self._replace_settings(ProcessingSettings.from_dict(data), action=action)

    @Slot(str)
    def setPreviewMode(self, mode: str) -> None:
        label = str(mode).title()
        if label not in {"Quick", "Stable", "Full"} or label == self._preview_mode:
            return
        self._preview_mode = label
        self.app_settings.setValue("previewModeQml", label)
        self.settingsChanged.emit()
        self.schedulePreview(force=True)
        self._set_status(f"Preview render: {label}")

    @Slot(int)
    def setTargetRasterWidth(self, width: int) -> None:
        width = max(1, min(16384, int(width)))
        data = self.settings.to_dict()
        if bool(self.settings.keep_aspect):
            width, height = self._linked_target_size(width=width)
            data.update(target_width=width, target_height=height)
            action = f"Target raster: {width} × {height} · aspect linked"
        else:
            data["target_width"] = width
            action = f"Raster width: {width}"
        self._replace_settings(ProcessingSettings.from_dict(data), action=action)

    @Slot(int)
    def setTargetRasterHeight(self, height: int) -> None:
        height = max(1, min(16384, int(height)))
        data = self.settings.to_dict()
        if bool(self.settings.keep_aspect):
            width, height = self._linked_target_size(height=height)
            data.update(target_width=width, target_height=height)
            action = f"Target raster: {width} × {height} · aspect linked"
        else:
            data["target_height"] = height
            action = f"Raster height: {height}"
        self._replace_settings(ProcessingSettings.from_dict(data), action=action)

    @Slot(int, int)
    def setRasterSize(self, width: int, height: int) -> None:
        data = self.settings.to_dict()
        data.update(target_enabled=True, target_width=max(1, int(width)), target_height=max(1, int(height)))
        self._replace_settings(ProcessingSettings.from_dict(data), action=f"Target raster: {max(1, int(width))} × {max(1, int(height))}")

    @Slot(float, float)
    def setPixelAspect(self, width: float, height: float) -> None:
        data = self.settings.to_dict()
        data.update(pixel_aspect_x=float(width), pixel_aspect_y=float(height))
        self._replace_settings(ProcessingSettings.from_dict(data), action=f"Pixel aspect: {float(width):g}:{float(height):g}")

    # ---------- file/source ----------
    @Slot(str)
    def openFile(self, value: str) -> None:
        path = Path(_local_path(value))
        if not path.is_file():
            self.errorOccurred.emit("Could not open file", "The selected file does not exist.")
            return
        try:
            suffix = path.suffix.lower()
            self._current_file = path
            self._current_time = 0.0
            self._video_path = None
            self._video_info = None
            self._source_image = None
            self._clipboard_source_image = None
            self._current_frame = None
            if suffix in SUPPORTED_VIDEO_SUFFIXES:
                self._video_path = path
                self._video_info = probe_video(path)
                self._current_frame = read_video_frame(path, 0.0)
            elif suffix in IMAGE_SUFFIXES:
                from PIL import Image
                with Image.open(path) as img:
                    self._source_image = img.convert("RGB").copy()
            else:
                raise ValueError(f"Unsupported file type: {suffix or '(none)'}")
            self._source_revision += 1
            self._clear_layer_render_cache()
            self._reset_preview_temporal_state()
            self._invalidate_rendered()
            self.sourceChanged.emit()
            self.playbackChanged.emit()
            self._history.clear()
            self.historyChanged.emit()
            self._set_status(f"Opened {path.name}")
            self.schedulePreview(force=True)
            self.refreshPresetThumbnails()
        except Exception as exc:
            self.errorOccurred.emit("Could not open file", str(exc))

    @Slot()
    def pasteImageFromClipboard(self) -> None:
        """Load image pixels (or a copied image file) from the system clipboard."""
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            self.errorOccurred.emit(_tr("Clipboard"), _tr("The clipboard does not contain an image."))
            return

        try:
            qimage = clipboard.image()
            if qimage is None or qimage.isNull():
                mime = clipboard.mimeData()
                if mime is not None:
                    for url in mime.urls():
                        path = Path(_local_path(url))
                        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                            self.openFile(str(path))
                            return
                self.errorOccurred.emit(_tr("Clipboard"), _tr("The clipboard does not contain an image."))
                return

            pasted = _qimage_to_pil(qimage)
            alpha = pasted.getchannel("A")
            alpha_min, _alpha_max = alpha.getextrema()

            self._current_file = None
            self._current_time = 0.0
            self._video_path = None
            self._video_info = None
            self._current_frame = None
            self._clipboard_source_image = pasted if int(alpha_min) < 255 else None
            self._source_image = pasted.convert("RGB")

            self._source_revision += 1
            self._clear_layer_render_cache()
            self._reset_preview_temporal_state()
            self._invalidate_rendered()
            self.sourceChanged.emit()
            self.playbackChanged.emit()
            self._history.clear()
            self.historyChanged.emit()
            self._set_status(_tr("Pasted image from clipboard"))
            self.schedulePreview(force=True)
            self.refreshPresetThumbnails()
        except Exception as exc:
            self.errorOccurred.emit(_tr("Could not paste image"), str(exc))

    @Slot(str)
    def exportImage(self, value: str) -> None:
        path = Path(_local_path(value))
        source = self._active_source()
        if source is None:
            return
        if not path.suffix:
            path = path.with_suffix(".png")
        animated = settings_at_time(self.settings, self._current_time)
        job = self._next_job()
        self._export_jobs.add(job)
        worker = ProcessingWorker(
            job,
            "export-image",
            source.copy(),
            animated,
            {"path": str(path)},
            frame_time=self._current_time,
            frame_index=max(0, round(self._current_time * (self._video_info.fps if self._video_info else animated.animation_fps))),
            display_mode=animated.display_mode if animated.display_export else "raw",
            include_grid=False,
        )
        self._connect_worker(worker)
        self.thread_pool.start(worker)
        self._set_status(f"Exporting {path.name}…")

    @Slot(str)
    def exportMedia(self, value: str) -> None:
        path = Path(_local_path(value))
        source = self._active_source()
        if source is None:
            return
        job = self._next_job()
        self._export_jobs.add(job)
        worker = MediaExportWorker(
            job,
            self.settings,
            str(path),
            image=self._source_image if self._video_path is None else None,
            video_path=str(self._video_path) if self._video_path else None,
            include_audio=bool(self._preserve_audio) if self._video_path else False,
        )
        self._connect_worker(worker)
        self.thread_pool.start(worker)
        self._set_status(f"Exporting {path.name}…")

    @Slot(str)
    def exportSequence(self, value: str) -> None:
        folder = Path(_local_path(value))
        if not self.hasSource:
            return
        folder.mkdir(parents=True, exist_ok=True)
        stem = self._current_file.stem if self._current_file else "frame"
        output_dir = folder / f"{stem}-rastermint-frames"
        output_dir.mkdir(parents=True, exist_ok=True)
        job = self._next_job()
        self._export_jobs.add(job)
        worker = SequenceExportWorker(
            job,
            self.settings,
            str(output_dir),
            image=self._source_image if self._video_path is None else None,
            video_path=str(self._video_path) if self._video_path else None,
            prefix=stem,
        )
        self._connect_worker(worker)
        self.thread_pool.start(worker)
        self._set_status(f"Exporting PNG sequence to {output_dir.name}…")

    @Slot("QVariantList", str)
    def batchExport(self, urls: list[Any], output_value: str) -> None:
        paths = [_local_path(str(item)) for item in urls]
        paths = [p for p in paths if Path(p).is_file()]
        output = _local_path(output_value)
        if not paths or not output:
            return
        job = self._next_job()
        self._export_jobs.add(job)
        worker = BatchWorker(job, paths, output, self.settings)
        self._connect_worker(worker)
        self.thread_pool.start(worker)
        self._set_status(f"Batch processing {len(paths)} images…")

    # ---------- layers ----------
    @Slot(int)
    def selectLayer(self, index: int) -> None:
        index = int(index)
        if 0 <= index < len(self.settings.effect_stack):
            self._selected_layer = index
            self._selected_layers = {index}
            self.layerSelectionChanged.emit()
            self.layerWorkflowChanged.emit()

    @Slot(int)
    def toggleLayerSelection(self, index: int) -> None:
        index = int(index)
        if not (0 <= index < len(self.settings.effect_stack)):
            return
        if index in self._selected_layers and len(self._selected_layers) > 1:
            self._selected_layers.remove(index)
        else:
            self._selected_layers.add(index)
            self._selected_layer = index
        self.layerSelectionChanged.emit()
        self.layerWorkflowChanged.emit()

    @Slot()
    def clearLayerMultiSelection(self) -> None:
        self._selected_layers = {self._selected_layer} if self._selected_layer >= 0 else set()
        self.layerWorkflowChanged.emit()

    @Slot(str)
    def addLayer(self, kind: str) -> None:
        if kind not in EFFECT_DEFINITIONS:
            return
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if kind in FIXED_STAGE_KINDS:
            existing = next((index for index, step in enumerate(stack) if step.get("kind") == kind), -1)
            if existing >= 0:
                self._selected_layer = existing
                self.layerSelectionChanged.emit()
                return
        stack.append(new_effect(kind))
        stack = normalize_effect_stack(stack, self.settings)
        selected = next((index for index, step in enumerate(stack) if step.get("kind") == kind and index >= len(stack) - 2), len(stack) - 1) if kind in FIXED_STAGE_KINDS else len(stack) - 1
        data = self.settings.to_dict()
        data["effect_stack"] = stack
        if kind == "Hardware Display":
            data["display_mode"] = "display"
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=f"Added layer: {kind}",
            selected_layer=selected,
        )

    @Slot(int)
    def removeLayer(self, index: int) -> None:
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= index < len(stack)):
            return
        kind = str(stack[index].get("kind", "Layer"))
        removed_id = str(stack[index].get("id", ""))
        del stack[index]
        used_groups = {str(step.get("group_id", "")) for step in stack if str(step.get("group_id", ""))}
        data = self.settings.to_dict()
        data["effect_stack"] = stack
        data["layer_groups"] = [dict(group) for group in self.settings.layer_groups if str(group.get("id", "")) in used_groups]
        if str(data.get("solo_layer_id", "")) == removed_id:
            data["solo_layer_id"] = ""
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=f"Removed layer: {kind}",
            selected_layer=max(0, min(index, len(stack) - 1)),
        )

    @Slot(int)
    def duplicateLayer(self, index: int) -> None:
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= index < len(stack)):
            return
        original = stack[index]
        kind = str(original["kind"])
        if kind in FIXED_STAGE_KINDS:
            return
        copy = new_effect(kind, enabled=bool(original.get("enabled", True)))
        copy["params"].update(deepcopy(dict(original.get("params") or {})))
        copy["opacity"] = float(original.get("opacity", 1.0) or 0.0)
        copy["blend_mode"] = str(original.get("blend_mode", "Normal") or "Normal")
        copy["mask"] = deepcopy(dict(original.get("mask") or default_layer_mask()))
        copy["group_id"] = str(original.get("group_id", "") or "")
        stack.insert(index + 1, copy)
        data = self.settings.to_dict()
        data["effect_stack"] = stack
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=f"Duplicated layer: {kind}",
            selected_layer=index + 1,
        )

    @Slot(int, int)
    def moveLayer(self, source: int, target: int) -> None:
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= source < len(stack)):
            return
        if str(stack[source].get("kind")) in FIXED_STAGE_KINDS:
            return
        first_fixed = next((i for i, step in enumerate(stack) if str(step.get("kind")) in FIXED_STAGE_KINDS), len(stack))
        max_target = max(0, first_fixed - 1)
        target = max(0, min(int(target), max_target))
        if target == source:
            return
        item = stack.pop(source)
        stack.insert(target, item)
        data = self.settings.to_dict()
        data["effect_stack"] = stack
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=f"Moved layer: {item.get('kind', 'Layer')}",
            selected_layer=target,
        )

    @Slot(int, bool)
    def setLayerEnabled(self, index: int, enabled: bool) -> None:
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= index < len(stack)):
            return
        kind = str(stack[index].get("kind", "Layer"))
        stack[index]["enabled"] = bool(enabled)
        data = self.settings.to_dict()
        data["effect_stack"] = stack
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=f"{kind}: {'Enabled' if enabled else 'Disabled'}",
            selected_layer=index,
        )

    def _replace_layer_metadata(self, stack: list[dict[str, Any]], index: int, action: str) -> None:
        data = self.settings.to_dict()
        data["effect_stack"] = stack
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=action,
            selected_layer=index,
        )

    @Slot(float)
    def setLayerOpacity(self, value: float) -> None:
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= self._selected_layer < len(stack)):
            return
        value = max(0.0, min(1.0, float(value)))
        stack[self._selected_layer]["opacity"] = value
        self._replace_layer_metadata(stack, self._selected_layer, f"{stack[self._selected_layer]['kind']} · Opacity: {round(value * 100)}%")

    @Slot(str)
    def setLayerBlendMode(self, mode: str) -> None:
        mode = str(mode or "Normal")
        if mode not in BLEND_MODES:
            return
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= self._selected_layer < len(stack)):
            return
        stack[self._selected_layer]["blend_mode"] = mode
        self._replace_layer_metadata(stack, self._selected_layer, f"{stack[self._selected_layer]['kind']} · Blend: {mode}")

    def _set_layer_mask_value(self, key: str, value: Any, action_value: str) -> None:
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= self._selected_layer < len(stack)):
            return
        mask = dict(stack[self._selected_layer].get("mask") or default_layer_mask())
        mask[str(key)] = value
        stack[self._selected_layer]["mask"] = mask
        self._replace_layer_metadata(stack, self._selected_layer, f"{stack[self._selected_layer]['kind']} · Mask {action_value}")

    @Slot(str)
    def setLayerMaskType(self, mask_type: str) -> None:
        mask_type = str(mask_type or "None")
        if mask_type not in MASK_TYPES:
            return
        self._set_layer_mask_value("type", mask_type, f"type: {mask_type}")

    @Slot(bool)
    def setLayerMaskInvert(self, invert: bool) -> None:
        self._set_layer_mask_value("invert", bool(invert), f"invert: {'On' if invert else 'Off'}")

    @Slot(float)
    def setLayerMaskFeather(self, feather: float) -> None:
        value = max(0.0, min(1.0, float(feather)))
        self._set_layer_mask_value("feather", value, f"feather: {round(value * 100)}%")

    @Slot(float)
    def setLayerMaskStrength(self, strength: float) -> None:
        value = max(0.0, min(1.0, float(strength)))
        self._set_layer_mask_value("strength", value, f"strength: {round(value * 100)}%")

    @Slot()
    def duplicateSelectedLayer(self) -> None:
        self.duplicateLayer(self._selected_layer)

    @Slot()
    def copySelectedLayerSettings(self) -> None:
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= self._selected_layer < len(stack)):
            return
        self._layer_clipboard = deepcopy(stack[self._selected_layer])
        self.layerWorkflowChanged.emit()
        self._set_status(f"Copied layer settings: {stack[self._selected_layer].get('kind', 'Layer')}")

    @Slot()
    def pasteSelectedLayerSettings(self) -> None:
        if self._layer_clipboard is None:
            return
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= self._selected_layer < len(stack)):
            return
        target = stack[self._selected_layer]
        source = self._layer_clipboard
        if str(target.get("kind")) != str(source.get("kind")):
            self._set_status("Layer settings can only be pasted onto the same effect type")
            return
        target["params"] = deepcopy(dict(source.get("params") or {}))
        target["opacity"] = float(source.get("opacity", 1.0) or 0.0)
        target["blend_mode"] = str(source.get("blend_mode", "Normal") or "Normal")
        target["mask"] = deepcopy(dict(source.get("mask") or default_layer_mask()))
        self._replace_layer_metadata(stack, self._selected_layer, f"Pasted layer settings: {target.get('kind', 'Layer')}")

    @Slot()
    def resetSelectedLayer(self) -> None:
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= self._selected_layer < len(stack)):
            return
        old = stack[self._selected_layer]
        kind = str(old.get("kind", ""))
        reset = new_effect(kind, enabled=bool(old.get("enabled", True)), effect_id=str(old.get("id", "")))
        reset["group_id"] = str(old.get("group_id", "") or "")
        stack[self._selected_layer] = reset
        self._replace_layer_metadata(stack, self._selected_layer, f"Reset layer: {kind}")

    @Slot()
    def toggleSoloSelectedLayer(self) -> None:
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= self._selected_layer < len(stack)):
            return
        layer_id = str(stack[self._selected_layer].get("id", ""))
        data = self.settings.to_dict()
        data["solo_layer_id"] = "" if str(self.settings.solo_layer_id or "") == layer_id else layer_id
        enabled = bool(data["solo_layer_id"])
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=f"Solo {stack[self._selected_layer].get('kind', 'Layer')}: {'On' if enabled else 'Off'}",
            selected_layer=self._selected_layer,
        )

    @Slot()
    def removeSelectedLayers(self) -> None:
        selected = sorted(i for i in self._selected_layers if 0 <= i < len(self.settings.effect_stack))
        if not selected:
            return
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        removed_ids = {str(stack[i].get("id", "")) for i in selected}
        removed_names = [str(stack[i].get("kind", "Layer")) for i in selected]
        stack = [step for i, step in enumerate(stack) if i not in set(selected)]
        used_groups = {str(step.get("group_id", "")) for step in stack if str(step.get("group_id", ""))}
        groups = [dict(group) for group in self.settings.layer_groups if str(group.get("id", "")) in used_groups]
        data = self.settings.to_dict()
        data["effect_stack"] = stack
        data["layer_groups"] = groups
        if str(data.get("solo_layer_id", "")) in removed_ids:
            data["solo_layer_id"] = ""
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=f"Removed {len(selected)} layer{'s' if len(selected) != 1 else ''}: {', '.join(removed_names[:3])}",
            selected_layer=max(0, min(selected[0], len(stack) - 1)),
        )

    @Slot(str)
    def groupSelectedLayers(self, name: str) -> None:
        selected = sorted(i for i in self._selected_layers if 0 <= i < len(self.settings.effect_stack))
        if not selected:
            return
        group_id = f"group-{uuid4().hex[:10]}"
        clean_name = str(name or "").strip() or "Layer Group"
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        for index in selected:
            stack[index]["group_id"] = group_id
        groups = [dict(group) for group in self.settings.layer_groups]
        groups.append({"id": group_id, "name": clean_name, "collapsed": False, "enabled": True})
        data = self.settings.to_dict()
        data["effect_stack"] = stack
        data["layer_groups"] = groups
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=f"Grouped {len(selected)} layers: {clean_name}",
            selected_layer=selected[-1],
        )

    @Slot()
    def ungroupSelectedLayers(self) -> None:
        selected = sorted(i for i in self._selected_layers if 0 <= i < len(self.settings.effect_stack))
        if not selected:
            return
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        touched = {str(stack[index].get("group_id", "")) for index in selected if str(stack[index].get("group_id", ""))}
        for index in selected:
            stack[index]["group_id"] = ""
        used = {str(step.get("group_id", "")) for step in stack if str(step.get("group_id", ""))}
        groups = [dict(group) for group in self.settings.layer_groups if str(group.get("id", "")) in used]
        data = self.settings.to_dict()
        data["effect_stack"] = stack
        data["layer_groups"] = groups
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=f"Ungrouped {len(selected)} layer{'s' if len(selected) != 1 else ''}",
            selected_layer=selected[-1],
        )

    def _group_by_id(self, group_id: str) -> dict[str, Any] | None:
        key = str(group_id or "")
        return next((group for group in self.settings.layer_groups if str(group.get("id", "")) == key), None)

    @Slot(str, result=str)
    def layerGroupName(self, group_id: str) -> str:
        group = self._group_by_id(group_id)
        return str(group.get("name", "")) if group else ""

    @Slot(str, result=bool)
    def layerGroupCollapsed(self, group_id: str) -> bool:
        group = self._group_by_id(group_id)
        return bool(group and group.get("collapsed", False))

    @Slot(str, result=bool)
    def layerGroupEnabled(self, group_id: str) -> bool:
        group = self._group_by_id(group_id)
        return bool(group is None or group.get("enabled", True))

    @Slot(str, result=int)
    def layerGroupCount(self, group_id: str) -> int:
        key = str(group_id or "")
        return sum(1 for step in self.settings.effect_stack if str(step.get("group_id", "")) == key)

    @Slot(int, result=bool)
    def isFirstLayerInGroup(self, index: int) -> bool:
        index = int(index)
        if not (0 <= index < len(self.settings.effect_stack)):
            return False
        group_id = str(self.settings.effect_stack[index].get("group_id", "") or "")
        if not group_id:
            return False
        return not any(str(step.get("group_id", "") or "") == group_id for step in self.settings.effect_stack[:index])

    def _update_group(self, group_id: str, key: str, value: Any, action: str) -> None:
        groups = [dict(group) for group in self.settings.layer_groups]
        changed = False
        for group in groups:
            if str(group.get("id", "")) == str(group_id):
                group[key] = value
                changed = True
                break
        if not changed:
            return
        data = self.settings.to_dict()
        data["layer_groups"] = groups
        self._replace_settings(ProcessingSettings.from_dict(data), action=action, selected_layer=self._selected_layer)

    @Slot(str, bool)
    def setLayerGroupCollapsed(self, group_id: str, collapsed: bool) -> None:
        self._update_group(group_id, "collapsed", bool(collapsed), "Layer group collapsed" if collapsed else "Layer group expanded")

    @Slot(str, bool)
    def setLayerGroupEnabled(self, group_id: str, enabled: bool) -> None:
        self._update_group(group_id, "enabled", bool(enabled), f"Layer group: {'Enabled' if enabled else 'Disabled'}")

    @Slot(str, str)
    def renameLayerGroup(self, group_id: str, name: str) -> None:
        clean = str(name or "").strip()
        if clean:
            self._update_group(group_id, "name", clean, f"Renamed layer group: {clean}")

    @Slot(str, "QVariant")
    def setLayerParam(self, key: str, value: Any) -> None:
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        if not (0 <= self._selected_layer < len(stack)):
            return
        step = stack[self._selected_layer]
        kind = str(step.get("kind", "Layer"))
        key = str(key)
        params = step.setdefault("params", {})
        params[key] = value
        if kind == "ASCII / Glyph" and key in {"character_set", "custom_chars", "inject_chars", "font", "cell_size", "font_scale", "depth"}:
            from rastermint.core.effect_stack import ascii_depth_max
            character_set = str(params.get("character_set", "Classic ASCII"))
            custom_chars = str(params.get("custom_chars", " .:-=+*#%@"))
            inject_chars = str(params.get("inject_chars", ""))
            font_name = str(params.get("font", "Mono"))
            cell_size = int(params.get("cell_size", 10) or 10)
            font_scale = float(params.get("font_scale", 0.9) or 0.9)
            font_size = max(2, round(cell_size * max(0.4, min(1.5, font_scale))))
            max_depth = ascii_depth_max(character_set, custom_chars, font_name, font_size, inject_chars)
            try:
                params["depth"] = max(2, min(max_depth, int(round(float(params.get("depth", max_depth))))))
            except (TypeError, ValueError):
                params["depth"] = max_depth
        spec = EFFECT_DEFINITIONS.get(kind, {}).get("params", {}).get(key, {})
        label = str(spec.get("label", self._pretty_key(key)))
        decimals = spec.get("decimals")
        if decimals is None and spec.get("type") == "int":
            decimals = 0
        decimals = int(decimals) if decimals is not None else None
        display = self._format_action_value(value, decimals=decimals, suffix=str(spec.get("suffix", "")))
        data = self.settings.to_dict()
        data["effect_stack"] = stack
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=f"{kind} · {label}: {display}",
            selected_layer=self._selected_layer,
        )

    # ---------- transforms ----------
    def _transform_change(self, action: str, **changes: Any) -> None:
        data = self.settings.to_dict()
        data.update(changes)
        self._replace_settings(ProcessingSettings.from_dict(data), action=action)

    @Slot()
    def flipHorizontal(self) -> None:
        enabled = not self.settings.flip_horizontal
        self._transform_change(f"Flip horizontal: {'On' if enabled else 'Off'}", flip_horizontal=enabled)

    @Slot()
    def flipVertical(self) -> None:
        enabled = not self.settings.flip_vertical
        self._transform_change(f"Flip vertical: {'On' if enabled else 'Off'}", flip_vertical=enabled)

    @Slot()
    def toggleMirrorHorizontal(self) -> None:
        enabled = not self.settings.mirror_horizontal
        self._transform_change(f"Mirror horizontal: {'On' if enabled else 'Off'}", mirror_horizontal=enabled)

    @Slot()
    def toggleMirrorVertical(self) -> None:
        enabled = not self.settings.mirror_vertical
        self._transform_change(f"Mirror vertical: {'On' if enabled else 'Off'}", mirror_vertical=enabled)

    @Slot(str, float)
    def setMirrorAxis(self, mode: str, value: float) -> None:
        value = max(0.0, min(1.0, float(value)))
        percent = round(value * 100)
        if mode == "horizontal":
            self._transform_change(f"Mirror horizontal axis: {percent}%", mirror_horizontal_axis=value)
        else:
            self._transform_change(f"Mirror vertical axis: {percent}%", mirror_vertical_axis=value)

    @Slot(int)
    def rotateImage(self, degrees: int) -> None:
        rotation = (self.settings.rotation + int(degrees)) % 360
        self._transform_change(f"Rotation: {rotation}°", rotation=rotation)

    @Slot()
    def resetImageTransform(self) -> None:
        defaults = ProcessingSettings()
        data = self.settings.to_dict()
        for key in (
            "rotation", "flip_horizontal", "flip_vertical", "mirror_horizontal", "mirror_vertical",
            "mirror_horizontal_axis", "mirror_vertical_axis", "crop_left", "crop_top", "crop_right",
            "crop_bottom", "position_x", "position_y",
        ):
            data[key] = getattr(defaults, key)
        self._replace_settings(ProcessingSettings.from_dict(data), action="Reset image transform")

    @Slot()
    def resetSettings(self) -> None:
        settings = ProcessingSettings()
        settings.effect_stack = default_effect_stack(settings)
        self._preview_mode = "Quick"
        self.app_settings.setValue("previewModeQml", "Quick")
        self._clear_layer_render_cache()
        self._replace_settings(settings, action="Reset settings")

    # ---------- palettes ----------
    @Slot(str)
    def applyPalette(self, name_or_id: str) -> None:
        record = find_palette(str(name_or_id))
        if record:
            colors = list(record.colors)
            name = record.name
            source = record.source
            author = "RasterMint palette library"
        else:
            user = self._find_user_palette(str(name_or_id))
            if user is None:
                return
            colors = list(user.get("colors") or [])
            name = str(user.get("name", "Custom"))
            source = "user library"
            author = "RasterMint user library"
        data = self.settings.to_dict()
        data.update(
            palette=colors,
            palette_locks=[False] * len(colors),
            palette_name=name,
            palette_author=author,
            palette_source=source,
        )
        self._replace_settings(ProcessingSettings.from_dict(data), action=f"Palette: {name}")

    @Slot(str, str)
    def savePaletteToLibrary(self, name: str, category: str) -> None:
        palette_name = str(name).strip()
        palette_category = str(category).strip() or "Custom"
        colors = [str(color).strip().upper() for color in list(self.settings.palette) if str(color).strip()]
        if not palette_name:
            self.errorOccurred.emit("Could not save palette", "Palette name cannot be empty.")
            return
        if not colors:
            self.errorOccurred.emit("Could not save palette", "The current palette has no colours.")
            return

        existing = next(
            (item for item in self._user_palettes if str(item.get("name", "")).casefold() == palette_name.casefold()),
            None,
        )
        if existing is not None:
            existing.update(
                category=palette_category,
                colors=colors[:256],
                description=f"Saved RasterMint palette · {len(colors[:256])} colors",
            )
        else:
            used_ids = {str(item.get("id", "")) for item in self._user_palettes}
            base_id = f"user-palette-{self._palette_slug(palette_name)}"
            palette_id = base_id
            suffix = 2
            while palette_id in used_ids:
                palette_id = f"{base_id}-{suffix}"
                suffix += 1
            self._user_palettes.append({
                "id": palette_id,
                "name": palette_name,
                "category": palette_category,
                "description": f"Saved RasterMint palette · {len(colors[:256])} colors",
                "colors": colors[:256],
                "user": True,
            })

        self._save_user_palettes()
        self.paletteLibraryChanged.emit()
        self._set_status(f"Saved palette to library: {palette_name}")

    def _current_palette_category(self) -> str:
        current_name = str(getattr(self.settings, "palette_name", "") or "")
        record = find_palette(current_name)
        if record is not None:
            return str(record.category or "Custom")
        user = self._find_user_palette(current_name)
        return str(user.get("category", "Custom")) if user is not None else "Custom"

    @Slot(str)
    def importPalette(self, value: str) -> None:
        try:
            path = Path(_local_path(value))
            colors = read_palette_file(path)
            data = self.settings.to_dict()
            data.update(palette=colors, palette_locks=[False] * len(colors), palette_name=path.stem, palette_author="", palette_source=str(path))
            self._replace_settings(ProcessingSettings.from_dict(data), action=f"Imported palette: {path.stem}")
        except Exception as exc:
            self.errorOccurred.emit("Could not import palette", str(exc))

    @Slot(str)
    def exportPalette(self, value: str) -> None:
        try:
            path = Path(_local_path(value))
            if not path.suffix:
                path = path.with_suffix(".hex")
            write_hex_palette(path, self.settings.palette)
            self._set_status(f"Saved palette {path.name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not export palette", str(exc))

    @Slot(str)
    def exportPaletteJson(self, value: str) -> None:
        try:
            path = Path(_local_path(value))
            if not path.suffix:
                path = path.with_suffix(".json")
            payload = {
                "format": "RasterMint Palette",
                "version": 1,
                "name": str(getattr(self.settings, "palette_name", "") or "Custom Palette"),
                "category": self._current_palette_category(),
                "author": str(getattr(self.settings, "palette_author", "") or ""),
                "source": str(getattr(self.settings, "palette_source", "") or ""),
                "colors": list(self.settings.palette),
                "locks": list(getattr(self.settings, "palette_locks", []) or []),
            }
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            self._set_status(f"Saved palette JSON {path.name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not export palette JSON", str(exc))

    @Slot(int, str)
    def optimizePalette(self, count: int, method: str) -> None:
        source = self._active_source()
        if source is None:
            return
        try:
            colors = extract_palette(source, max(2, min(256, int(count))), str(method))
            data = self.settings.to_dict()
            data.update(palette=colors, palette_locks=[False] * len(colors), palette_name=f"Optimized {len(colors)}", palette_author="RasterMint", palette_source="source image")
            self._replace_settings(ProcessingSettings.from_dict(data), action=f"Optimized palette: {len(colors)} colors · {method}")
        except Exception as exc:
            self.errorOccurred.emit("Could not optimize palette", str(exc))

    @Slot(str, str, int, str)
    def generatePalette(self, start: str, end: str, count: int, space: str) -> None:
        try:
            colors = interpolate_palette(start, end, count, space)
            data = self.settings.to_dict()
            data.update(palette=colors, palette_locks=[False] * len(colors), palette_name=f"{space} Gradient {count}", palette_author="RasterMint", palette_source="generated")
            self._replace_settings(ProcessingSettings.from_dict(data), action=f"Generated palette: {space} · {len(colors)} colors")
        except Exception as exc:
            self.errorOccurred.emit("Could not generate palette", str(exc))

    @Slot("QVariantList", int, str)
    def generatePaletteFromStops(self, stops: list[Any], count: int, space: str) -> None:
        try:
            colors = interpolate_palette_stops([str(stop) for stop in stops], count, space)
            data = self.settings.to_dict()
            stop_count = len([str(stop) for stop in stops if str(stop).strip()])
            data.update(
                palette=colors,
                palette_locks=[False] * len(colors),
                palette_name=f"{space} Gradient {count}",
                palette_author="RasterMint",
                palette_source=f"generated from {stop_count} anchor colors",
            )
            self._replace_settings(ProcessingSettings.from_dict(data), action=f"Generated palette: {space} · {len(colors)} colors · {stop_count} anchors")
        except Exception as exc:
            self.errorOccurred.emit("Could not generate palette", str(exc))

    @Slot("QVariantList", "QVariantList", int, str)
    def generatePaletteFromPositionedStops(
        self, stops: list[Any], positions: list[Any], count: int, space: str
    ) -> None:
        try:
            cleaned_stops = [str(stop) for stop in stops]
            cleaned_positions = [float(value) for value in positions]
            colors = interpolate_palette_stops(cleaned_stops, count, space, cleaned_positions)
            data = self.settings.to_dict()
            stop_count = len([stop for stop in cleaned_stops if stop.strip()])
            data.update(
                palette=colors,
                palette_locks=[False] * len(colors),
                palette_name=f"{space} Gradient {count}",
                palette_author="RasterMint",
                palette_source=f"generated from {stop_count} positioned anchor colors",
            )
            self._replace_settings(
                ProcessingSettings.from_dict(data),
                action=f"Generated palette: {space} · {len(colors)} colors · {stop_count} anchors",
            )
        except Exception as exc:
            self.errorOccurred.emit("Could not generate palette", str(exc))

    @Slot(str)
    def fetchLospec(self, value: str) -> None:
        try:
            palette = fetch_lospec_palette(value)
            data = self.settings.to_dict()
            data.update(
                palette=palette.colors,
                palette_locks=[False] * len(palette.colors),
                palette_name=palette.name,
                palette_author=palette.author,
                palette_source=palette.source_url,
            )
            self._replace_settings(ProcessingSettings.from_dict(data), action=f"Lospec palette: {palette.name}")
            self.infoOccurred.emit("Lospec palette", f"Imported {palette.name} by {palette.author} ({len(palette.colors)} colors).")
        except Exception as exc:
            self.errorOccurred.emit("Could not fetch Lospec palette", str(exc))

    @Slot(int, str)
    def setPaletteColor(self, index: int, color: str) -> None:
        index = int(index)
        chosen = QColor(str(color))
        if not chosen.isValid() or not (0 <= index < len(self.settings.palette)):
            return
        colors = list(self.settings.palette)
        normalized = chosen.name(QColor.NameFormat.HexRgb).upper()
        colors[index] = normalized
        data = self.settings.to_dict()
        data["palette"] = colors
        data["palette_name"] = "Custom"
        self._replace_settings(ProcessingSettings.from_dict(data), action=f"Palette color {index + 1}: {normalized}")

    @Slot(int, bool)
    def setPaletteLock(self, index: int, locked: bool) -> None:
        index = int(index)
        if not (0 <= index < len(self.settings.palette)):
            return
        locks = list(self.settings.palette_locks)
        locks[index] = bool(locked)
        data = self.settings.to_dict()
        data["palette_locks"] = locks
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            schedule=False,
            action=f"Palette color {index + 1}: {'Locked' if locked else 'Unlocked'}",
        )

    @Slot(str)
    def addPaletteColor(self, color: str) -> None:
        if len(self.settings.palette) >= 256:
            return
        chosen = QColor(str(color))
        if not chosen.isValid():
            return
        normalized = chosen.name(QColor.NameFormat.HexRgb).upper()
        colors = list(self.settings.palette) + [normalized]
        locks = list(self.settings.palette_locks) + [False]
        data = self.settings.to_dict()
        data.update(palette=colors, palette_locks=locks, palette_name="Custom")
        self._replace_settings(ProcessingSettings.from_dict(data), action=f"Added palette color: {normalized}")

    @Slot(int)
    def removePaletteColor(self, index: int = -1) -> None:
        if len(self.settings.palette) <= 1:
            return
        colors = list(self.settings.palette)
        locks = list(self.settings.palette_locks)
        candidate = int(index)

        if candidate >= 0:
            # A direct swatch deletion must target exactly the clicked colour.
            # Locked colours are protected rather than silently deleting some
            # other unlocked swatch from the end of the palette.
            if not (0 <= candidate < len(colors)) or locks[candidate]:
                return
        else:
            # The existing minus button keeps its previous behaviour: remove
            # the last unlocked colour when no explicit index is supplied.
            candidate = next((i for i in range(len(colors) - 1, -1, -1) if not locks[i]), -1)
            if candidate < 0:
                return

        removed = colors.pop(candidate)
        locks.pop(candidate)
        data = self.settings.to_dict()
        stack = normalize_effect_stack(self.settings.effect_stack, self.settings)
        for step in stack:
            if step.get("kind") != "Hardware Limits":
                continue
            params = step.setdefault("params", {})
            try:
                groups = json.loads(str(params.get("profile_group_indices_json", "[]") or "[]"))
            except (TypeError, ValueError, json.JSONDecodeError):
                groups = []
            if isinstance(groups, list):
                adjusted: list[list[int]] = []
                for group in groups:
                    if not isinstance(group, list):
                        continue
                    indexes = []
                    for raw in group:
                        if not isinstance(raw, int) or raw == candidate:
                            continue
                        indexes.append(raw - 1 if raw > candidate else raw)
                    if indexes:
                        adjusted.append(indexes)
                params["profile_group_indices_json"] = json.dumps(adjusted)
        data.update(palette=colors, palette_locks=locks, palette_name="Custom", effect_stack=stack)
        self._replace_settings(ProcessingSettings.from_dict(data), action=f"Removed palette color: {removed}")

    @Slot()
    def shufflePaletteUnlocked(self) -> None:
        colors = list(self.settings.palette)
        locks = list(self.settings.palette_locks)
        indexes = [i for i, locked in enumerate(locks) if not locked]
        values = [colors[i] for i in indexes]
        random.shuffle(values)
        for index, value in zip(indexes, values, strict=False):
            colors[index] = value
        data = self.settings.to_dict()
        data.update(palette=colors, palette_name="Custom")
        self._replace_settings(ProcessingSettings.from_dict(data), action="Shuffled unlocked palette colors")

    @Slot()
    def randomizePaletteUnlocked(self) -> None:
        colors = list(self.settings.palette)
        locks = list(self.settings.palette_locks)
        for index, locked in enumerate(locks):
            if locked:
                continue
            r, g, b = colorsys.hsv_to_rgb(random.random(), random.uniform(0.45, 1.0), random.uniform(0.35, 1.0))
            colors[index] = f"#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"
        data = self.settings.to_dict()
        data.update(palette=colors, palette_name="Custom")
        self._replace_settings(ProcessingSettings.from_dict(data), action="Randomized unlocked palette colors")

    # ---------- hardware ----------
    @Slot(str, str, "QVariantMap")
    def applyHardware(self, profile_id: str, mode: str, options: dict[str, Any] | None = None) -> None:
        profile = next((p for p in self._hardware_profiles if p.id == profile_id), None)
        if not profile:
            return
        opts = dict(options or {})
        try:
            updated = apply_profile_to_settings(
                self.settings,
                profile,
                mode=str(mode).lower(),
                apply_resolution=bool(opts.get("raster", True)),
                apply_palette=bool(opts.get("palette", True)),
                apply_pixel_aspect=bool(opts.get("pixelAspect", True)),
                apply_constraints=bool(opts.get("limits", True)),
                apply_display=bool(opts.get("display", True)),
            )
            self._replace_settings(updated, action=f"Hardware profile: {profile.name} · {str(mode).title()}")
        except Exception as exc:
            self.errorOccurred.emit("Could not apply hardware profile", str(exc))

    @Slot(str)
    def loadHardwareProfile(self, value: str) -> None:
        try:
            profile = load_profile_file(_local_path(value))
            self._hardware_profiles = [p for p in self._hardware_profiles if p.id != profile.id] + [profile]
            self._hardware_profiles.sort(key=lambda p: (p.category.lower(), p.name.lower()))
            self.hardwareProfilesChanged.emit()
            self._set_status(f"Loaded hardware profile: {profile.name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not load hardware profile", str(exc))

    # ---------- presets ----------
    @Slot(str)
    def applyBuiltinPreset(self, preset_id: str) -> None:
        try:
            preset = next((p for p in BUILTIN_PRESETS if p.id == preset_id), None)
            label = preset.name if preset else str(preset_id)
            settings = build_builtin_preset(preset_id, self.settings)

            if preset_id == "accurate-1to1":
                source = self._active_source()
                if source is not None:
                    colors = extract_palette(source, 12, "Median Cut")
                    data = settings.to_dict()
                    data.update(
                        palette=colors,
                        palette_locks=[False] * len(colors),
                        palette_name=f"Optimized {len(colors)}",
                        palette_author="RasterMint",
                        palette_source="source image",
                    )
                    settings = ProcessingSettings.from_dict(data)

            self._replace_settings(settings, action=f"Applied preset: {label}")
        except Exception as exc:
            self.errorOccurred.emit("Could not apply preset", str(exc))

    @Slot(str)
    def savePreset(self, value: str) -> None:
        try:
            path = Path(_local_path(value))
            if not path.suffix:
                path = path.with_suffix(".json")
            save_preset(path, self.settings)
            self._set_status(f"Saved preset {path.name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not save preset", str(exc))

    @Slot(str)
    def loadPreset(self, value: str) -> None:
        try:
            path = Path(_local_path(value))
            self._replace_settings(load_preset(path), action=f"Loaded preset: {path.name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not load preset", str(exc))

    @Slot(str)
    def applyAnimationPreset(self, preset_id: str) -> None:
        try:
            preset = next((p for p in ANIMATION_PRESETS if p.id == preset_id), None)
            label = preset.name if preset else str(preset_id)
            self._replace_settings(apply_animation_preset(self.settings, preset_id), action=f"Motion preset: {label}")
            self.playbackChanged.emit()
        except Exception as exc:
            self.errorOccurred.emit("Could not apply motion preset", str(exc))

    # ---------- randomize ----------
    @Slot()
    def randomizeUnlocked(self) -> None:
        current = ProcessingSettings.from_dict(self.settings.to_dict())
        if self._random_index < 0:
            self._record_random(current)
        locks = current.random_locks
        randomized = ProcessingSettings.from_dict(current.to_dict())
        if not locks.get("palette", False):
            for i, locked in enumerate(randomized.palette_locks):
                if not locked:
                    randomized.palette[i] = f"#{random.randint(0, 0xFFFFFF):06X}"
            randomized.palette_name = "Random"
        stack = normalize_effect_stack(randomized.effect_stack, randomized)
        if not locks.get("dither", False):
            dither = next((x for x in stack if x.get("kind") == "Dither"), None)
            if dither:
                dither["enabled"] = True
                dither["params"]["algorithm"] = random.choice(ALGORITHMS)
                dither["params"]["strength"] = round(random.uniform(0.55, 1.35), 2)
        if not locks.get("effects", False):
            creative = ["Local Contrast", "Hue Rotate", "Gaussian Blur", "Glow", "Bloom", "RGB Split", "Posterize", "Scanlines", "Noise", "Pixel Sort", "Screen Melt", "Pixel Scatter", "Data Shift", "Channel Swap", "Pixel Material"]
            stack = [s for s in stack if s.get("kind") in {"Adjustments", "Pixelate", "Dither"}]
            for kind in random.sample(creative, k=random.randint(1, 3)):
                stack.insert(max(1, len(stack) - 1), new_effect(kind))
        if not locks.get("parameters", False):
            for step in stack:
                definition = EFFECT_DEFINITIONS.get(str(step.get("kind")), {})
                for key, spec in definition.get("params", {}).items():
                    if key == "seed":
                        continue
                    typ = spec.get("type")
                    if typ in {"int", "float"}:
                        lo, hi = float(spec.get("min", 0)), float(spec.get("max", 1))
                        value = random.uniform(lo + (hi-lo)*0.1, lo + (hi-lo)*0.9)
                        step["params"][key] = int(round(value)) if typ == "int" else round(value, int(spec.get("decimals", 2)))
                    elif typ == "choice" and spec.get("options"):
                        step["params"][key] = random.choice(list(spec["options"]))
        randomized.effect_stack = stack
        if not locks.get("resolution", True):
            randomized.target_enabled = True
            randomized.target_width, randomized.target_height = random.choice([(160,144),(240,160),(256,224),(256,240),(320,200),(320,240),(640,480)])
        self._replace_settings(randomized, action="Randomized unlocked settings")
        self._record_random(self.settings)

    def _record_random(self, settings: ProcessingSettings) -> None:
        snapshot = settings.to_dict()
        if self._random_index < len(self._random_history) - 1:
            self._random_history = self._random_history[: self._random_index + 1]
        self._random_history.append(snapshot)
        self._random_history = self._random_history[-50:]
        self._random_index = len(self._random_history) - 1

    @Slot(int)
    def randomHistory(self, delta: int) -> None:
        if not self._random_history:
            return
        idx = max(0, min(len(self._random_history)-1, self._random_index + int(delta)))
        if idx != self._random_index:
            self._random_index = idx
            direction = "previous" if int(delta) < 0 else "next"
            self._replace_settings(ProcessingSettings.from_dict(self._random_history[idx]), action=f"Random history: {direction}")

    @Slot(bool)
    def setPreserveAudio(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled != self._preserve_audio:
            action = f"Preserve source audio: {'On' if enabled else 'Off'}"
            self._history.record(self._history_state(), action)
            self._preserve_audio = enabled
            self.audioExportChanged.emit()
            self.historyChanged.emit()
            self._set_status(action)

    _ANIMATION_CLIP_SETTINGS_KEY = "animationClipLibraryV1"

    def _load_animation_clip_library(self) -> list[dict[str, Any]]:
        raw = self.app_settings.value(self._ANIMATION_CLIP_SETTINGS_KEY, "[]")
        try:
            payload = json.loads(str(raw or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = []
        result: list[dict[str, Any]] = []
        for item in payload if isinstance(payload, list) else []:
            if isinstance(item, dict) and str(item.get("name", "")).strip() and isinstance(item.get("track"), dict):
                normalized = normalize_tracks([item["track"]])
                if normalized:
                    result.append({"name": str(item["name"]).strip(), "track": normalized[0]})
        return result

    def _save_animation_clip_library(self) -> None:
        self.app_settings.setValue(self._ANIMATION_CLIP_SETTINGS_KEY, json.dumps(self._animation_clip_library, ensure_ascii=False))
        self.app_settings.sync()

    @Property("QVariantList", notify=settingsChanged)
    def animationClipLibrary(self) -> list[dict[str, Any]]:
        return [{"name": str(item.get("name", ""))} for item in self._animation_clip_library]

    @Property(bool, notify=settingsChanged)
    def keyframeClipboardAvailable(self) -> bool:
        return self._keyframe_clipboard is not None

    @Slot(int, float, float, str)
    def addAnimationKeyframe(self, track_index: int, time_seconds: float, value: float, easing: str = "Linear") -> None:
        tracks = normalize_tracks(self.settings.animation_tracks)
        index = int(track_index)
        if not (0 <= index < len(tracks)):
            return
        keyframes = [dict(item) for item in tracks[index].get("keyframes", [])]
        keyframes.append({
            "time": max(0.0, min(self.timelineDuration, float(time_seconds))),
            "value": float(value),
            "easing": str(easing) if str(easing) in EASINGS else "Linear",
            "bezier": [0.25, 0.1, 0.25, 1.0],
        })
        tracks[index]["keyframes"] = keyframes
        self._replace_tracks(tracks, "Added animation keyframe")

    @Slot(int, int, float, float, str, "QVariantList")
    def updateAnimationKeyframe(self, track_index: int, key_index: int, time_seconds: float, value: float, easing: str, bezier: list[Any]) -> None:
        tracks = normalize_tracks(self.settings.animation_tracks)
        ti, ki = int(track_index), int(key_index)
        if not (0 <= ti < len(tracks)):
            return
        keys = [dict(item) for item in tracks[ti].get("keyframes", [])]
        if not (0 <= ki < len(keys)):
            return
        control = list(bezier or [0.25, 0.1, 0.25, 1.0])[:4]
        while len(control) < 4:
            control.append([0.25, 0.1, 0.25, 1.0][len(control)])
        keys[ki] = {
            "time": max(0.0, min(self.timelineDuration, float(time_seconds))),
            "value": float(value),
            "easing": str(easing) if str(easing) in EASINGS else "Linear",
            "bezier": [float(v) for v in control],
        }
        tracks[ti]["keyframes"] = keys
        self._replace_tracks(tracks, "Updated animation keyframe")

    @Slot(int, int)
    def removeAnimationKeyframe(self, track_index: int, key_index: int) -> None:
        tracks = normalize_tracks(self.settings.animation_tracks)
        ti, ki = int(track_index), int(key_index)
        if not (0 <= ti < len(tracks)):
            return
        keys = [dict(item) for item in tracks[ti].get("keyframes", [])]
        if not (0 <= ki < len(keys)) or len(keys) <= 2:
            return
        del keys[ki]
        tracks[ti]["keyframes"] = keys
        self._replace_tracks(tracks, "Removed animation keyframe")

    @Slot(int, int)
    def copyAnimationKeyframe(self, track_index: int, key_index: int) -> None:
        tracks = normalize_tracks(self.settings.animation_tracks)
        ti, ki = int(track_index), int(key_index)
        if 0 <= ti < len(tracks):
            keys = tracks[ti].get("keyframes", [])
            if 0 <= ki < len(keys):
                self._keyframe_clipboard = deepcopy(keys[ki])
                self.settingsChanged.emit()
                self._set_status("Copied animation keyframe")

    @Slot(int, float)
    def pasteAnimationKeyframe(self, track_index: int, time_seconds: float) -> None:
        if self._keyframe_clipboard is None:
            return
        tracks = normalize_tracks(self.settings.animation_tracks)
        ti = int(track_index)
        if not (0 <= ti < len(tracks)):
            return
        key = deepcopy(self._keyframe_clipboard)
        key["time"] = max(0.0, min(self.timelineDuration, float(time_seconds)))
        tracks[ti].setdefault("keyframes", []).append(key)
        self._replace_tracks(tracks, "Pasted animation keyframe")

    @Slot(int, str, float, float, float, float, int)
    def setAnimationModulator(self, track_index: int, kind: str, amount: float, frequency: float, phase: float, bpm: float, seed: int) -> None:
        tracks = normalize_tracks(self.settings.animation_tracks)
        index = int(track_index)
        if not (0 <= index < len(tracks)):
            return
        tracks[index]["modulator"] = {
            "type": str(kind) if str(kind) in MODULATORS else "None",
            "amount": float(amount),
            "frequency": max(0.0, float(frequency)),
            "phase": float(phase),
            "bpm": max(1.0, float(bpm)),
            "seed": int(seed),
        }
        self._replace_tracks(tracks, f"Animation modulator: {kind}")

    @Slot(int, str)
    def saveAnimationClip(self, track_index: int, name: str) -> None:
        tracks = normalize_tracks(self.settings.animation_tracks)
        index = int(track_index)
        clean = str(name or "").strip()
        if not clean or not (0 <= index < len(tracks)):
            return
        record = next((item for item in self._animation_clip_library if str(item.get("name", "")).casefold() == clean.casefold()), None)
        payload = {"name": clean, "track": deepcopy(tracks[index])}
        if record is None:
            self._animation_clip_library.append(payload)
        else:
            record.update(payload)
        self._save_animation_clip_library()
        self.settingsChanged.emit()
        self._set_status(f"Saved animation clip: {clean}")

    @Slot(str, str)
    def applyAnimationClip(self, name: str, target: str) -> None:
        record = next((item for item in self._animation_clip_library if str(item.get("name", "")) == str(name)), None)
        if record is None or not any(item["id"] == str(target) for item in self.animationTargets):
            return
        track = deepcopy(record["track"])
        track["target"] = str(target)
        tracks = normalize_tracks(self.settings.animation_tracks)
        tracks.append(track)
        self._replace_tracks(tracks, f"Animation clip: {name}")

    def _replace_tracks(self, tracks: list[dict[str, Any]], action: str) -> None:
        data = self.settings.to_dict()
        data["animation_tracks"] = normalize_tracks(tracks)
        self._replace_settings(ProcessingSettings.from_dict(data), action=action)

    @Slot(str, float, float, float, float, str)
    def addAnimationTrack(self, target: str, start_value: float, end_value: float, start_time: float, end_time: float, easing: str) -> None:
        if not any(item["id"] == str(target) for item in self.animationTargets):
            return
        tracks = normalize_tracks(self.settings.animation_tracks)
        start_time = max(0.0, float(start_time))
        end_time = max(start_time, float(end_time))
        ease = str(easing) if str(easing) in EASINGS else "Linear"
        tracks.append({
            "target": str(target), "enabled": True,
            "keyframes": [
                {"time": start_time, "value": float(start_value), "easing": ease, "bezier": [0.25, 0.1, 0.25, 1.0]},
                {"time": end_time, "value": float(end_value), "easing": "Linear", "bezier": [0.25, 0.1, 0.25, 1.0]},
            ],
            "modulator": {"type": "None", "amount": 0.0, "frequency": 1.0, "phase": 0.0, "bpm": 120.0, "seed": 1},
        })
        self._replace_tracks(tracks, f"Added animation track: {target}")

    @Slot(int, str, float, float, float, float, str)
    def updateAnimationTrack(self, index: int, target: str, start_value: float, end_value: float, start_time: float, end_time: float, easing: str) -> None:
        tracks = normalize_tracks(self.settings.animation_tracks)
        index = int(index)
        if not (0 <= index < len(tracks)) or not any(item["id"] == str(target) for item in self.animationTargets):
            return
        start_time = max(0.0, float(start_time))
        end_time = max(start_time, float(end_time))
        ease = str(easing) if str(easing) in EASINGS else "Linear"
        tracks[index].update({
            "target": str(target),
            "keyframes": [
                {"time": start_time, "value": float(start_value), "easing": ease, "bezier": [0.25, 0.1, 0.25, 1.0]},
                {"time": end_time, "value": float(end_value), "easing": "Linear", "bezier": [0.25, 0.1, 0.25, 1.0]},
            ],
        })
        self._replace_tracks(tracks, f"Updated animation track: {target}")

    @Slot(int)
    def duplicateAnimationTrack(self, index: int) -> None:
        tracks = normalize_tracks(self.settings.animation_tracks)
        index = int(index)
        if not (0 <= index < len(tracks)):
            return
        tracks.insert(index + 1, deepcopy(tracks[index]))
        self._replace_tracks(tracks, "Duplicated animation track")

    @Slot(int)
    def removeAnimationTrack(self, index: int) -> None:
        tracks = normalize_tracks(self.settings.animation_tracks)
        index = int(index)
        if not (0 <= index < len(tracks)):
            return
        label = str(tracks[index].get("target", "track"))
        del tracks[index]
        self._replace_tracks(tracks, f"Removed animation track: {label}")

    @Slot(int, bool)
    def setAnimationTrackEnabled(self, index: int, enabled: bool) -> None:
        tracks = normalize_tracks(self.settings.animation_tracks)
        index = int(index)
        if not (0 <= index < len(tracks)):
            return
        tracks[index]["enabled"] = bool(enabled)
        self._replace_tracks(tracks, f"Animation track: {'Enabled' if enabled else 'Disabled'}")

    @Slot(int)
    def stepFrame(self, delta: int) -> None:
        fps = self._video_info.fps if self._video_info and self._video_info.fps > 0 else max(1.0, float(self.settings.animation_fps))
        self.setCurrentTime(self._current_time + int(delta) / fps)

    @Slot()
    def seekStart(self) -> None:
        self.setCurrentTime(0.0)

    @Slot()
    def seekEnd(self) -> None:
        self.setCurrentTime(self.timelineDuration)

    # ---------- timeline/media ----------
    @Slot(float)
    def setCurrentTime(self, seconds: float) -> None:
        self._reset_preview_temporal_state()
        self._current_time = max(0.0, min(self.timelineDuration, float(seconds)))
        self._set_status(f"Timeline: {self._current_time:.2f} s")
        if self._video_path:
            job = self._next_job()
            worker = VideoFrameWorker(job, str(self._video_path), self._current_time)
            self._connect_worker(worker)
            self.thread_pool.start(worker)
        else:
            self.schedulePreview(force=True)
        self.playbackChanged.emit()

    @Slot()
    def togglePlay(self) -> None:
        self._playing = not self._playing
        if self._playing:
            self._play_timer.start()
        else:
            self._play_timer.stop()
        self.playbackChanged.emit()
        self._set_status("Playback: Play" if self._playing else "Playback: Pause")

    @Slot(str)
    def setPlaybackMode(self, mode: str) -> None:
        label = "Rendered" if str(mode).lower().startswith("render") else "Quick"
        if label != self._playback_mode:
            self._playback_mode = label
            self.playbackChanged.emit()
            self._set_status(f"Playback mode: {label}")

    @Slot(float)
    def setPlaybackSpeed(self, speed: float) -> None:
        self._playback_speed = max(0.25, min(4.0, float(speed)))
        self.playbackChanged.emit()
        self._set_status(f"Playback speed: {self._playback_speed:g}×")

    @Slot()
    def renderPreviewCache(self) -> None:
        if not self.hasSource:
            return
        job = self._next_job()
        worker = RenderedPreviewWorker(
            job,
            self.settings,
            image=self._source_image if self._video_path is None else None,
            video_path=str(self._video_path) if self._video_path else None,
            start_time=self._current_time if self._video_path else 0.0,
            duration=min(5.0, self.timelineDuration),
            max_side=PREVIEW_MAX_SIDE,
            context={"source_revision": self._source_revision, "settings_revision": self._settings_revision},
        )
        self._connect_worker(worker)
        self.thread_pool.start(worker)
        self._set_status("Rendering preview cache…")

    def _play_tick(self) -> None:
        duration = self.timelineDuration
        if duration <= 0:
            return
        step = 0.033 * self._playback_speed
        value = self._current_time + step
        if value >= duration:
            if self.settings.animation_loop:
                value %= duration
            else:
                value = duration
                self._playing = False
                self._play_timer.stop()
        self._current_time = value
        if self._playback_mode == "Rendered" and self._rendered_frames:
            idx = min(len(self._rendered_frames)-1, max(0, round(value * max(1.0, self._rendered_fps))))
            self._publish_preview(self._rendered_frames[idx])
        elif self._video_path:
            job = self._next_job()
            worker = VideoFrameWorker(job, str(self._video_path), value)
            self._connect_worker(worker)
            self.thread_pool.start(worker)
        else:
            self.schedulePreview(force=True)
        self.playbackChanged.emit()

    @Property(str, notify=benchmarkChanged)
    def benchmarkSummary(self) -> str:
        return self._benchmark_summary

    @Slot()
    def benchmarkCurrentStack(self) -> None:
        source = self._active_source()
        if source is None:
            return
        # Keep diagnostics interactive even for giant source files. Geometry and
        # pixel-scaled parameters are still represented accurately at preview size.
        settings = settings_at_time(self.settings, self._current_time)
        final_size = target_raster_size(source.size, settings)
        preview_source = make_preview_source(source, max_side=PREVIEW_MAX_SIDE, settings=settings)
        preview_settings = make_preview_settings(settings, final_size, preview_source.size)
        self._benchmark_summary = _tr("Benchmarking current stack…")
        self.benchmarkChanged.emit()
        job = self._next_job()
        worker = BenchmarkWorker(job, preview_source, preview_settings)
        self._connect_worker(worker)
        self.thread_pool.start(worker)

    def _preview_layer_cache(self):
        if not bool(getattr(self, "layerCacheEnabled", True)):
            return None
        budget = int(getattr(self, "layerCacheMegabytes", 192) or 192)
        if self._layer_render_cache is None:
            from rastermint.core.render_cache import LayerRenderCache
            self._layer_render_cache = LayerRenderCache(budget)
        else:
            try:
                self._layer_render_cache.set_budget(budget)
            except Exception:
                self._layer_render_cache = None
                return None
        return self._layer_render_cache

    def _clear_layer_render_cache(self) -> None:
        cache = self._layer_render_cache
        if cache is not None:
            try:
                cache.clear()
            except Exception:
                pass

    def _preview_estimate_key(self, max_side: int, settings: ProcessingSettings) -> str:
        enabled_layers = sum(
            1 for step in (settings.effect_stack or [])
            if isinstance(step, dict) and bool(step.get("enabled", True))
        )
        side_bucket = max(64, int(round(max(1, int(max_side)) / 64.0) * 64))
        return f"{self._preview_mode}:{side_bucket}:{enabled_layers}"

    def _begin_preview_render(self, job_id: int, max_side: int, settings: ProcessingSettings) -> None:
        key = self._preview_estimate_key(max_side, settings)
        self._render_job_id = int(job_id)
        self._render_estimate_key = key
        self._render_started_at = time.perf_counter()
        self._render_busy = True
        self._render_progress = 0.0
        prior_estimate = self._render_estimates.get(key)
        self._render_eta_seconds = float(prior_estimate if prior_estimate is not None else -1.0)
        # Do not flash progress UI for normal fast previews. Once a render is
        # known to be long, keep the panel visible through completion instead
        # of hiding it when the remaining ETA drops below five seconds.
        self._render_progress_visible = bool(prior_estimate is not None and float(prior_estimate) >= 5.0)
        self._render_stage = _tr("Preparing preview")
        self.renderProgressChanged.emit()

    def _update_preview_render(self, job_id: int, current: int, total: int, label: str) -> None:
        if int(job_id) != self._render_job_id or not self._render_busy:
            return
        fraction = max(0.0, min(1.0, float(current) / max(1.0, float(total))))
        self._render_progress = fraction
        if label:
            self._render_stage = _tr(str(label))

        elapsed = max(0.0, time.perf_counter() - self._render_started_at)
        live_eta = -1.0
        if fraction >= 0.03 and fraction < 0.999 and elapsed > 0.02:
            live_eta = max(0.0, elapsed * (1.0 - fraction) / fraction)
        prior_total = self._render_estimates.get(self._render_estimate_key)
        prior_eta = -1.0
        if prior_total is not None:
            prior_eta = max(0.0, float(prior_total) - elapsed)

        if live_eta >= 0.0 and prior_eta >= 0.0:
            # Early in the render the previous empirical duration is steadier;
            # as real progress accumulates, favor the live measurement.
            live_weight = max(0.25, min(0.9, fraction))
            self._render_eta_seconds = live_eta * live_weight + prior_eta * (1.0 - live_weight)
        elif live_eta >= 0.0:
            self._render_eta_seconds = live_eta
        elif prior_eta >= 0.0:
            self._render_eta_seconds = prior_eta
        else:
            self._render_eta_seconds = -1.0

        if not self._render_progress_visible:
            estimated_total = -1.0
            if self._render_eta_seconds >= 0.0:
                estimated_total = elapsed + self._render_eta_seconds
            elif prior_total is not None:
                estimated_total = float(prior_total)
            # The elapsed-time check is a final guarantee for jobs whose early
            # progress callbacks are too irregular to yield a stable ETA.
            if estimated_total >= 5.0 or elapsed >= 5.0:
                self._render_progress_visible = True
        self.renderProgressChanged.emit()

    def _finish_preview_render(self, job_id: int, *, keep_busy: bool = False) -> None:
        if int(job_id) != self._render_job_id:
            return
        elapsed = max(0.0, time.perf_counter() - self._render_started_at)
        key = self._render_estimate_key
        if key and elapsed > 0.0:
            previous = self._render_estimates.get(key)
            self._render_estimates[key] = elapsed if previous is None else (0.65 * float(previous) + 0.35 * elapsed)
        self._render_progress = 1.0
        self._render_eta_seconds = 0.0
        self._render_stage = _tr("Complete")
        self._render_busy = bool(keep_busy)
        if not keep_busy:
            self._render_job_id = 0
            self._render_progress_visible = False
        self.renderProgressChanged.emit()

    # ---------- preview pipeline ----------
    @Slot()
    def schedulePreview(self, force: bool = False) -> None:
        if not self.hasSource:
            return
        self._quick_timer.stop(); self._stable_timer.stop()
        if self._preview_mode == "Quick":
            self._quick_timer.start(0 if force else 55)
            self._stable_timer.start(330)
        elif self._preview_mode == "Stable":
            self._stable_timer.start(0 if force else 180)
        else:
            self._request_preview(self._safe_full_side())

    def _quick_side(self) -> int:
        return adaptive_preview_max_side(self.settings, FAST_PREVIEW_MAX_SIDE)

    def _request_refined_preview(self) -> None:
        self._request_preview(adaptive_preview_max_side(self.settings, PREVIEW_MAX_SIDE))

    def _safe_full_side(self) -> int:
        source = self._active_source()
        if source is None:
            return PREVIEW_MAX_SIDE
        width, height = processed_raster_size(source.size, self.settings)
        pixels = max(1, width * height)
        if pixels <= MAX_FULL_PREVIEW_PIXELS:
            return max(width, height)
        scale = math.sqrt(MAX_FULL_PREVIEW_PIXELS / pixels)
        return max(64, round(max(width, height) * scale))

    def _request_preview(self, max_side: int) -> None:
        source = self._active_source()
        if source is None:
            return
        if self._preview_running:
            self._pending_preview_side = int(max_side)
            return
        self._preview_running = True
        self._pending_preview_side = 0
        settings = settings_at_time(self.settings, self._current_time)
        final_size = target_raster_size(source.size, settings)
        preview_source = make_preview_source(source, max_side=int(max_side), settings=settings)
        preview_settings = make_preview_settings(settings, final_size, preview_source.size)
        job = self._next_job()
        self._latest_preview_job = job
        self._begin_preview_render(job, int(max_side), preview_settings)
        context = {
            "source_revision": self._source_revision,
            "settings_revision": self._settings_revision,
            "time": self._current_time,
        }
        temporal_state = None
        if self._playing and self._playback_mode != "Rendered":
            if self._preview_temporal_state is None:
                from rastermint.core.temporal import TemporalEffectState
                self._preview_temporal_state = TemporalEffectState()
            temporal_state = self._preview_temporal_state
        worker = ProcessingWorker(
            job,
            "preview",
            preview_source,
            preview_settings,
            context,
            frame_time=self._current_time,
            frame_index=max(0, round(self._current_time * (self._video_info.fps if self._video_info else settings.animation_fps))),
            display_mode=settings.display_mode,
            include_grid=False,
            temporal_state=temporal_state,
            render_cache=self._preview_layer_cache(),
            tiled_processing=bool(getattr(self, "tiledProcessingEnabled", True)),
            tile_size=int(getattr(self, "processingTileSize", 1024) or 1024),
        )
        self._connect_worker(worker)
        self.thread_pool.start(worker)

    def _connect_worker(self, worker: Any) -> None:
        worker.signals.finished.connect(self._worker_finished)
        worker.signals.failed.connect(self._worker_failed)
        worker.signals.progress.connect(self._worker_progress)

    @Slot(int, str, object, object)
    def _worker_finished(self, job_id: int, purpose: str, result: object, context: object) -> None:
        if purpose == "benchmark" and isinstance(result, dict):
            total = float(result.get("total_ms", 0.0) or 0.0)
            layers = list(result.get("layers") or [])
            slow = layers[:3]
            details = ", ".join(
                f"{row.get('kind', 'Layer')} {float(row.get('milliseconds', 0.0)):.1f} ms"
                for row in slow
                if isinstance(row, dict)
            )
            self._benchmark_summary = (
                f"{int(result.get('width', 0))}×{int(result.get('height', 0))} · {total:.1f} ms"
                + (f" · {details}" if details else "")
            )
            self.benchmarkChanged.emit()
            self._set_status(f"Benchmark: {total:.1f} ms")
            return
        if purpose == "preview":
            self._preview_running = False
            valid = isinstance(context, dict) and context.get("source_revision") == self._source_revision and context.get("settings_revision") == self._settings_revision
            if valid and _is_pil_image(result):
                self._publish_preview(result)
            pending = self._pending_preview_side
            self._pending_preview_side = 0
            self._finish_preview_render(job_id, keep_busy=bool(pending))
            if pending:
                self._request_preview(pending)
            return
        if purpose == "video-frame" and _is_pil_image(result):
            # Ignore stale decode responses that are far away from current time.
            if abs(float(context) - self._current_time) < 0.15:
                self._current_frame = result
                self.sourceChanged.emit()
                self.schedulePreview(force=True)
            return
        if purpose == "preset-thumbnail" and _is_pil_image(result) and isinstance(context, dict):
            if context.get("source_revision") == self._source_revision:
                key = f"preset/{context.get('preset_id')}"
                self.provider.set_image(key, _pil_to_qimage(result))
                self._preview_revision += 1
                self.previewChanged.emit()
            return
        if purpose == "export-image" and _is_pil_image(result) and isinstance(context, dict):
            self._export_jobs.discard(job_id)
            path = Path(str(context.get("path", "output.png")))
            try:
                if path.suffix.lower() == ".svg":
                    save_svg(result, path)
                else:
                    save_image = result.convert("RGB") if path.suffix.lower() in {".jpg", ".jpeg"} else result
                    save_image.save(path)
                self._set_status(f"Exported {path.name}")
            except Exception as exc:
                self.errorOccurred.emit("Could not export image", str(exc))
            return
        if purpose == "audio-envelope" and isinstance(result, dict):
            data = self.settings.to_dict()
            data["audio_envelope"] = list(result.get("envelope") or [])
            data["audio_envelope_rate"] = float(result.get("rate", 30.0) or 30.0)
            self._replace_settings(ProcessingSettings.from_dict(data), action="Analysed audio amplitude")
            self._set_status(f"Audio envelope: {len(data['audio_envelope'])} samples")
            return

        if purpose == "rendered-preview" and isinstance(result, dict):
            frames = result.get("frames") or []
            context_map = context if isinstance(context, dict) else {}
            if context_map.get("source_revision") == self._source_revision and context_map.get("settings_revision") == self._settings_revision:
                self._rendered_frames = [frame for frame in frames if _is_pil_image(frame)]
                self._rendered_times = [float(v) for v in (result.get("times") or [])]
                self._rendered_fps = float(result.get("fps") or 0.0)
                self.renderedPreviewChanged.emit()
                self._set_status(f"Rendered {len(self._rendered_frames)} preview frames")
            return
        if purpose in {"media-export", "png-sequence", "batch"}:
            self._export_jobs.discard(job_id)
            self._set_status("Export complete")

    @Slot(int, str, str, object)
    def _worker_failed(self, job_id: int, purpose: str, trace: str, context: object) -> None:
        if purpose == "preview":
            self._preview_running = False
            pending = self._pending_preview_side
            self._pending_preview_side = 0
            self._finish_preview_render(job_id, keep_busy=bool(pending))
            if pending:
                self._request_preview(pending)
        self._export_jobs.discard(job_id)
        last = trace.strip().splitlines()[-1] if trace.strip() else "Unknown error"
        self.errorOccurred.emit("RasterMint error", last)

    @Slot(int, str, int, int, str)
    def _worker_progress(self, job_id: int, purpose: str, current: int, total: int, label: str) -> None:
        if purpose == "preview":
            self._update_preview_render(job_id, current, total, label)
            return
        if total > 0:
            self._set_status(f"{purpose.replace('-', ' ').title()}: {current}/{total} {label}")

    def _publish_preview(self, image: Any) -> None:
        qimage = _pil_to_qimage(image)
        self.provider.set_image("preview", qimage)
        self._preview_width = max(1, image.width)
        self._preview_height = max(1, image.height)
        self._preview_revision += 1
        self.previewChanged.emit()

    @Slot()
    def refreshPresetThumbnails(self) -> None:
        source = self._active_source()
        if source is None:
            return
        source_revision = self._source_revision
        base = ProcessingSettings.from_dict(self.settings.to_dict())
        for preset in BUILTIN_PRESETS:
            settings = build_builtin_preset(preset.id, base)
            final_size = target_raster_size(source.size, settings)
            preview_source = make_preview_source(source, max_side=128, settings=settings)
            preview_settings = make_preview_settings(settings, final_size, preview_source.size)
            job = self._next_job()
            worker = ProcessingWorker(
                job,
                "preset-thumbnail",
                preview_source,
                preview_settings,
                {"preset_id": preset.id, "source_revision": source_revision},
                display_mode="display",
                include_grid=False,
            )
            self._connect_worker(worker)
            self.thread_pool.start(worker, -1)

    @Slot()
    def shutdown(self) -> None:
        self._close_screen_eyedropper()
        self._quick_timer.stop(); self._stable_timer.stop(); self._play_timer.stop()
        self.thread_pool.clear()
        self.thread_pool.waitForDone(1500)
