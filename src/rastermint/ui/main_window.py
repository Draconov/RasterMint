# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSettings, Qt, QThreadPool, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QImage, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from rastermint import __app_name__, __version__
from rastermint.core.animation import settings_at_time
from rastermint.core.effect_stack import default_effect_stack, normalize_effect_stack
from rastermint.core.lospec import LospecPalette
from rastermint.core.media import SUPPORTED_VIDEO_SUFFIXES, VideoInfo, probe_video, video_support_available
from rastermint.core.palette import (
    BUILTIN_PALETTES,
    extract_palette,
    read_palette_file,
    write_hex_palette,
)
from rastermint.core.presets import load_preset, save_preset
from rastermint.core.processor import (
    FAST_PREVIEW_MAX_SIDE,
    PREVIEW_MAX_SIDE,
    adaptive_preview_max_side,
    make_preview_settings,
    make_preview_source,
    scaled_output_size,
)
from rastermint.core.settings import ProcessingSettings
from rastermint.core.svg_export import save_svg
from rastermint.ui.animation_panel import AnimationPanel
from rastermint.ui.effect_stack_widget import EffectStackWidget
from rastermint.ui.image_view import ImageView, SUPPORTED_IMAGE_SUFFIXES
from rastermint.ui.lospec_dialog import LospecPaletteDialog
from rastermint.ui.palette_editor import PaletteEditor
from rastermint.ui.worker import BatchWorker, MediaExportWorker, ProcessingWorker, VideoFrameWorker

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff);;All files (*.*)"
VIDEO_FILTER = "Videos (*.mp4 *.mov *.mkv *.webm *.avi *.m4v);;All files (*.*)"
EXPORT_FILTER = "PNG (*.png);;JPEG (*.jpg *.jpeg);;WebP (*.webp);;BMP (*.bmp);;TIFF (*.tif *.tiff);;SVG (*.svg)"
ANIMATION_FILTER = "MP4 video (*.mp4);;Animated GIF (*.gif)"
PALETTE_FILTER = "Palette files (*.hex *.txt *.gpl *.pal);;All files (*.*)"
PRESET_FILTER = "RasterMint preset (*.rmpreset);;JSON (*.json)"


def pil_to_pixmap(image: Image.Image) -> QPixmap:
    rgb = image if image.mode == "RGB" else image.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    qimg = QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(qimg)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{__app_name__} {__version__}")
        self.resize(1440, 900)
        self.setMinimumSize(1000, 650)
        self.setAcceptDrops(True)

        self.original_image: Image.Image | None = None
        self.preview_result: Image.Image | None = None
        self.current_file: Path | None = None
        self.video_path: Path | None = None
        self.video_info: VideoInfo | None = None
        self.video_time = 0.0
        self._video_playing = False
        self._video_frame_running = False
        self._pending_video_time: float | None = None
        self._latest_video_job = 0

        self.settings = ProcessingSettings()
        self.settings.effect_stack = default_effect_stack(self.settings)
        self._palette_name = "Ink"
        self._palette_author = ""
        self._palette_source = ""

        self._preview_source_cache: dict[tuple[int, int], Image.Image] = {}
        self._job_counter = 0
        self._latest_preview_job = 0
        self._export_jobs: set[int] = set()
        self._loading_controls = False
        self._preview_running = False
        self._preview_pending_max_side = 0
        self._source_revision = 0
        self._settings_revision = 0

        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(max(2, min(4, QThreadPool.globalInstance().maxThreadCount())))

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(55)
        self.preview_timer.timeout.connect(lambda: self._request_preview(FAST_PREVIEW_MAX_SIDE))
        self.preview_refine_timer = QTimer(self)
        self.preview_refine_timer.setSingleShot(True)
        self.preview_refine_timer.setInterval(330)
        self.preview_refine_timer.timeout.connect(self._request_refined_preview)

        self.video_play_timer = QTimer(self)
        self.video_play_timer.timeout.connect(self._video_play_tick)

        self.app_settings = QSettings("RasterMint", "RasterMint")

        self._build_actions()
        self._build_toolbar()
        self._build_ui()
        self._restore_geometry()
        self._apply_settings_to_controls(self.settings)
        self.statusBar().showMessage("Open or drop an image/video to begin")

    # ---------- UI ----------
    def _build_actions(self) -> None:
        self.open_action = QAction("Open Image…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_image_dialog)

        self.open_video_action = QAction("Open Video…", self)
        self.open_video_action.setShortcut("Ctrl+Shift+O")
        self.open_video_action.triggered.connect(self.open_video_dialog)

        self.export_action = QAction("Export Current Frame…", self)
        self.export_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.export_action.triggered.connect(self.export_image_dialog)
        self.export_action.setEnabled(False)

        self.export_media_action = QAction("Export Animation / Video…", self)
        self.export_media_action.setShortcut("Ctrl+Alt+S")
        self.export_media_action.triggered.connect(self.export_media_dialog)
        self.export_media_action.setEnabled(False)

        self.batch_action = QAction("Batch Export Images…", self)
        self.batch_action.triggered.connect(self.batch_export_dialog)

        self.load_preset_action = QAction("Load Preset…", self)
        self.load_preset_action.setShortcut("Ctrl+L")
        self.load_preset_action.triggered.connect(self.load_preset_dialog)
        self.save_preset_action = QAction("Save Preset…", self)
        self.save_preset_action.setShortcut("Ctrl+Shift+S")
        self.save_preset_action.triggered.connect(self.save_preset_dialog)

        self.fit_action = QAction("Fit Preview", self)
        self.fit_action.setShortcut("F")
        self.fit_action.triggered.connect(self.fit_views)
        self.reset_action = QAction("Reset Settings", self)
        self.reset_action.triggered.connect(self.reset_settings)
        self.quit_action = QAction("Quit", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.close)

        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.open_video_action)
        file_menu.addSeparator()
        file_menu.addAction(self.export_action)
        file_menu.addAction(self.export_media_action)
        file_menu.addAction(self.batch_action)
        file_menu.addSeparator()
        file_menu.addAction(self.load_preset_action)
        file_menu.addAction(self.save_preset_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)
        self.menuBar().addMenu("Edit").addAction(self.reset_action)
        self.menuBar().addMenu("View").addAction(self.fit_action)

    def _build_toolbar(self) -> None:
        bar = QToolBar("Main", self)
        bar.setMovable(False)
        bar.addAction(self.open_action)
        bar.addAction(self.open_video_action)
        bar.addSeparator()
        bar.addAction(self.export_action)
        bar.addAction(self.export_media_action)
        bar.addSeparator()
        bar.addAction(self.fit_action)
        self.addToolBar(bar)

    def _build_ui(self) -> None:
        root = QSplitter(Qt.Orientation.Horizontal)
        root.setChildrenCollapsible(False)
        self.setCentralWidget(root)
        root.addWidget(self._make_view_panel())
        root.addWidget(self._make_controls())
        root.setStretchFactor(0, 1)
        root.setStretchFactor(1, 0)
        root.setSizes([1050, 390])

    def _make_view_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        title = QLabel("Live Processed Preview")
        title.setObjectName("viewTitle")
        layout.addWidget(title)
        self.processed_view = ImageView()
        self.processed_view.file_dropped.connect(self._load_dropped_path)
        layout.addWidget(self.processed_view, 1)
        return panel

    def _make_controls(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(345)
        scroll.setMaximumWidth(450)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(12, 12, 12, 20)
        layout.setSpacing(12)

        preview_box = QGroupBox("Preview")
        pv = QVBoxLayout(preview_box)
        self.live_preview_check = QCheckBox("Live preview")
        self.live_preview_check.setChecked(True)
        self.live_preview_check.toggled.connect(self._live_preview_toggled)
        pv.addWidget(self.live_preview_check)
        self.preview_mode_combo = QComboBox()
        self.preview_mode_combo.addItem("Live · fast draft + refine", "live")
        self.preview_mode_combo.addItem("Still · refine after pause", "still")
        self.preview_mode_combo.addItem("Full · output resolution", "full")
        self.preview_mode_combo.currentIndexChanged.connect(self._preview_mode_changed)
        pv.addWidget(self.preview_mode_combo)
        self.preview_hint = QLabel("Live mode: fast 320px draft → refined 640px preview")
        self.preview_hint.setWordWrap(True)
        pv.addWidget(self.preview_hint)
        refresh = QPushButton("Refresh preview now")
        refresh.clicked.connect(self._request_refined_preview)
        pv.addWidget(refresh)
        layout.addWidget(preview_box)

        effects_box = QGroupBox("Effect Stack")
        effects_layout = QVBoxLayout(effects_box)
        self.effect_stack = EffectStackWidget(self.settings.effect_stack)
        self.effect_stack.stack_changed.connect(self._effect_stack_changed)
        effects_layout.addWidget(self.effect_stack)
        layout.addWidget(effects_box)

        palette_box = QGroupBox("Palette")
        pal = QVBoxLayout(palette_box)
        self.palette_combo = QComboBox()
        self.palette_combo.addItems(list(BUILTIN_PALETTES.keys()) + ["Custom"])
        self.palette_combo.currentTextChanged.connect(self._palette_preset_changed)
        pal.addWidget(self.palette_combo)
        self.palette_editor = PaletteEditor(self.settings.palette)
        self.palette_editor.palette_changed.connect(self._palette_edited)
        self.palette_editor.locks_changed.connect(self._palette_locks_changed)
        pal.addWidget(self.palette_editor)
        self.palette_source_label = QLabel("Built-in palette")
        self.palette_source_label.setWordWrap(True)
        pal.addWidget(self.palette_source_label)

        palette_buttons1 = QHBoxLayout()
        lospec = QPushButton("Lospec…")
        lospec.clicked.connect(self.open_lospec_dialog)
        import_pal = QPushButton("Import file…")
        import_pal.clicked.connect(self.import_palette_file)
        export_pal = QPushButton("Save HEX…")
        export_pal.clicked.connect(self.export_palette_hex)
        palette_buttons1.addWidget(lospec)
        palette_buttons1.addWidget(import_pal)
        palette_buttons1.addWidget(export_pal)
        pal.addLayout(palette_buttons1)

        palette_buttons2 = QHBoxLayout()
        shuffle = QPushButton("Shuffle unlocked")
        shuffle.clicked.connect(self.palette_editor.shuffle_unlocked)
        randomize = QPushButton("Randomize unlocked")
        randomize.clicked.connect(self.palette_editor.randomize_unlocked)
        palette_buttons2.addWidget(shuffle)
        palette_buttons2.addWidget(randomize)
        pal.addLayout(palette_buttons2)

        extract_row = QHBoxLayout()
        self.extract_count = QSpinBox()
        self.extract_count.setRange(2, 256)
        self.extract_count.setValue(8)
        self.extract_button = QPushButton("Extract from image")
        self.extract_button.clicked.connect(self.extract_palette_from_image)
        self.extract_button.setEnabled(False)
        extract_row.addWidget(QLabel("Colors"))
        extract_row.addWidget(self.extract_count)
        extract_row.addWidget(self.extract_button, 1)
        pal.addLayout(extract_row)
        layout.addWidget(palette_box)

        animation_box = QGroupBox("Animation")
        animation_layout = QVBoxLayout(animation_box)
        self.animation_panel = AnimationPanel()
        self.animation_panel.set_targets(self.effect_stack.animatable_targets())
        self.animation_panel.animation_changed.connect(self._animation_changed)
        self.animation_panel.time_changed.connect(self._animation_time_changed)
        self.animation_panel.playback_changed.connect(self._animation_playback_changed)
        self.effect_stack.targets_changed.connect(self.animation_panel.set_targets)
        animation_layout.addWidget(self.animation_panel)
        layout.addWidget(animation_box)

        source_box = QGroupBox("Source")
        source_layout = QVBoxLayout(source_box)
        self.source_type_label = QLabel("No media loaded")
        source_layout.addWidget(self.source_type_label)
        self.video_controls = QWidget()
        vr = QHBoxLayout(self.video_controls)
        vr.setContentsMargins(0, 0, 0, 0)
        self.video_play_button = QPushButton("▶")
        self.video_play_button.setCheckable(True)
        self.video_play_button.toggled.connect(self._toggle_video_playback)
        self.video_slider = QSlider(Qt.Orientation.Horizontal)
        self.video_slider.setRange(0, 1000)
        self.video_slider.valueChanged.connect(self._video_slider_changed)
        self.video_time_label = QLabel("0.00 s")
        vr.addWidget(self.video_play_button)
        vr.addWidget(self.video_slider, 1)
        vr.addWidget(self.video_time_label)
        self.video_controls.setVisible(False)
        source_layout.addWidget(self.video_controls)
        layout.addWidget(source_box)

        output_box = QGroupBox("Output")
        output_form = QFormLayout(output_box)
        self.output_scale_combo = QComboBox()
        self.output_scale_combo.addItem("Original (1:1)", 1)
        for divisor in range(2, 17):
            self.output_scale_combo.addItem(f"Smaller ÷{divisor}", divisor)
        self.output_scale_combo.currentIndexChanged.connect(self._controls_changed)
        output_form.addRow("Size", self.output_scale_combo)
        self.output_size_label = QLabel("—")
        output_form.addRow("Result", self.output_size_label)
        layout.addWidget(output_box)

        info_box = QGroupBox("Media")
        info = QFormLayout(info_box)
        self.file_label = QLabel("—")
        self.file_label.setWordWrap(True)
        self.input_size_label = QLabel("—")
        info.addRow("File", self.file_label)
        info.addRow("Input", self.input_size_label)
        layout.addWidget(info_box)
        layout.addStretch(1)
        scroll.setWidget(body)
        return scroll

    # ---------- settings ----------
    def _settings_from_controls(self) -> ProcessingSettings:
        return ProcessingSettings(
            output_divisor=int(self.output_scale_combo.currentData() or 1),
            palette=self.palette_editor.colors(),
            palette_locks=self.palette_editor.locks(),
            palette_name=self._palette_name,
            palette_author=self._palette_author,
            palette_source=self._palette_source,
            effect_stack=self.effect_stack.stack(),
            animation_duration=self.animation_panel.duration(),
            animation_fps=self.animation_panel.fps(),
            animation_tracks=self.animation_panel.tracks(),
        )

    def _apply_settings_to_controls(self, settings: ProcessingSettings) -> None:
        self._loading_controls = True
        try:
            settings.effect_stack = normalize_effect_stack(settings.effect_stack, settings)
            self.effect_stack.set_stack(settings.effect_stack)
            scale_index = self.output_scale_combo.findData(settings.output_divisor)
            self.output_scale_combo.setCurrentIndex(max(0, scale_index))
            self.palette_editor.set_colors(settings.palette, settings.palette_locks, emit=False)
            self._palette_name = settings.palette_name or "Custom"
            self._palette_author = settings.palette_author
            self._palette_source = settings.palette_source
            match = next((name for name, colors in BUILTIN_PALETTES.items() if colors == settings.palette), None)
            self.palette_combo.setCurrentText(match or "Custom")
            self.animation_panel.set_targets(self.effect_stack.animatable_targets())
            self.animation_panel.set_animation(settings.animation_duration, settings.animation_fps, settings.animation_tracks)
            self.effect_stack.set_animated_targets(self.animation_panel.animated_target_ids())
            self._refresh_palette_source_label()
        finally:
            self._loading_controls = False
        self.settings = self._settings_from_controls()
        self._settings_revision += 1
        self._update_output_size_label()
        if self.original_image is not None:
            self.schedule_preview()

    def _controls_changed(self, *_args) -> None:
        if self._loading_controls:
            return
        self.settings = self._settings_from_controls()
        self._settings_revision += 1
        self._update_output_size_label()
        self.schedule_preview()

    def _effect_stack_changed(self, _stack: list) -> None:
        self.effect_stack.set_animated_targets(self.animation_panel.animated_target_ids())
        self._controls_changed()

    def _animation_changed(self) -> None:
        self.effect_stack.set_animated_targets(self.animation_panel.animated_target_ids())
        self._controls_changed()

    def _animation_time_changed(self, _seconds: float) -> None:
        if self._loading_controls or self.original_image is None:
            return
        self._settings_revision += 1
        self.schedule_preview(immediate=True, refined=not self.animation_panel.is_playing())

    def _animation_playback_changed(self, playing: bool) -> None:
        if not playing and self.original_image is not None:
            self.schedule_preview(force=True, refined=True)

    def _preview_mode(self) -> str:
        return str(self.preview_mode_combo.currentData() or "live")

    def _preview_mode_changed(self, *_args) -> None:
        mode = self._preview_mode()
        hints = {
            "live": "Live mode: fast 320px draft → refined 640px preview",
            "still": "Still mode: render a refined 640px preview after changes settle",
            "full": "Full mode: render at the selected output resolution (can be slow)",
        }
        self.preview_hint.setText(hints.get(mode, hints["live"]))
        if self.original_image is not None:
            self.schedule_preview(immediate=True, force=True)

    def _live_preview_toggled(self, enabled: bool) -> None:
        if not enabled:
            self.preview_timer.stop()
            self.preview_refine_timer.stop()
            self.statusBar().showMessage("Live preview paused · use Refresh preview now", 3500)
        elif self.original_image is not None:
            self.schedule_preview(immediate=True, force=True)

    # ---------- palette ----------
    def _palette_preset_changed(self, name: str) -> None:
        if self._loading_controls or name == "Custom":
            return
        colors = BUILTIN_PALETTES.get(name)
        if colors:
            self._loading_controls = True
            self.palette_editor.set_colors(colors.copy(), emit=False)
            self._palette_name = name
            self._palette_author = "RasterMint built-in"
            self._palette_source = ""
            self._loading_controls = False
            self._refresh_palette_source_label()
            self._controls_changed()

    def _palette_edited(self, _colors: list[str]) -> None:
        if self._loading_controls:
            return
        self._loading_controls = True
        self.palette_combo.setCurrentText("Custom")
        self._palette_name = "Custom"
        self._palette_author = ""
        self._palette_source = ""
        self._loading_controls = False
        self._refresh_palette_source_label()
        self._controls_changed()

    def _palette_locks_changed(self, _locks: list[bool]) -> None:
        if not self._loading_controls:
            self._controls_changed()

    def _refresh_palette_source_label(self) -> None:
        if self._palette_source:
            author = f" · {self._palette_author}" if self._palette_author else ""
            self.palette_source_label.setText(f"{self._palette_name}{author}\n{self._palette_source}")
        elif self._palette_author:
            self.palette_source_label.setText(f"{self._palette_name} · {self._palette_author}")
        else:
            self.palette_source_label.setText(self._palette_name)

    def open_lospec_dialog(self) -> None:
        dialog = LospecPaletteDialog(self)
        dialog.palette_selected.connect(self._import_lospec_palette)
        dialog.exec()

    def _import_lospec_palette(self, palette: LospecPalette) -> None:
        self._loading_controls = True
        self.palette_editor.set_colors(palette.colors, emit=False)
        self.palette_combo.setCurrentText("Custom")
        self._palette_name = palette.name
        self._palette_author = palette.author
        self._palette_source = palette.source_url
        self._loading_controls = False
        self._refresh_palette_source_label()
        self._controls_changed()
        self.statusBar().showMessage(f"Imported Lospec palette: {palette.name}", 4000)

    def import_palette_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import palette", str(Path.home()), PALETTE_FILTER)
        if not path:
            return
        try:
            colors = read_palette_file(path)
            self._loading_controls = True
            self.palette_editor.set_colors(colors, emit=False)
            self.palette_combo.setCurrentText("Custom")
            self._palette_name = Path(path).stem
            self._palette_author = ""
            self._palette_source = str(Path(path).resolve())
            self._loading_controls = False
            self._refresh_palette_source_label()
            self._controls_changed()
        except Exception as exc:
            QMessageBox.critical(self, "Palette import failed", str(exc))

    def export_palette_hex(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save palette", str(Path.home() / "palette.hex"), "HEX palette (*.hex)")
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".hex")
        try:
            write_hex_palette(target, self.palette_editor.colors())
            self.statusBar().showMessage(f"Saved {target.name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Palette export failed", str(exc))

    def extract_palette_from_image(self) -> None:
        if self.original_image is None:
            return
        try:
            colors = extract_palette(self.original_image, self.extract_count.value())
            self.palette_editor.set_colors(colors)
            self.statusBar().showMessage(f"Extracted {len(colors)} colors", 2500)
        except Exception as exc:
            QMessageBox.critical(self, "Palette extraction failed", str(exc))

    # ---------- loading ----------
    def open_image_dialog(self) -> None:
        start_dir = self.app_settings.value("lastOpenDir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(self, "Open image", start_dir, IMAGE_FILTER)
        if path:
            self.load_image(path)

    def open_video_dialog(self) -> None:
        start_dir = self.app_settings.value("lastOpenDir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(self, "Open video", start_dir, VIDEO_FILTER)
        if path:
            self.load_video(path)

    def _load_dropped_path(self, path: str) -> None:
        suffix = Path(path).suffix.lower()
        if suffix in SUPPORTED_VIDEO_SUFFIXES:
            self.load_video(path)
        else:
            self.load_image(path)

    def load_image(self, path: str | os.PathLike[str]) -> None:
        self._latest_video_job = -1
        self._pending_video_time = None
        self.video_play_timer.stop()
        self._video_playing = False
        if hasattr(self, "video_play_button"):
            self.video_play_button.blockSignals(True)
            self.video_play_button.setChecked(False)
            self.video_play_button.setText("▶")
            self.video_play_button.blockSignals(False)
        try:
            with Image.open(path) as img:
                img.load()
                image = img.convert("RGB")
            self._set_image_source(image, Path(path), is_video=False)
        except Exception as exc:
            QMessageBox.critical(self, "Could not open image", str(exc))

    def load_video(self, path: str | os.PathLike[str]) -> None:
        self._latest_video_job = -1
        self._pending_video_time = None
        self.video_play_timer.stop()
        self._video_playing = False
        if hasattr(self, "video_play_button"):
            self.video_play_button.blockSignals(True)
            self.video_play_button.setChecked(False)
            self.video_play_button.setText("▶")
            self.video_play_button.blockSignals(False)
        if not video_support_available():
            QMessageBox.critical(self, "Video support unavailable", "FFmpeg support could not be initialized.")
            return
        try:
            info = probe_video(path)
            self.video_path = Path(path)
            self.video_info = info
            self.video_time = 0.0
            self.current_file = self.video_path
            # Do not leave a previously loaded still/frame visible while the
            # first frame of the new video is decoding.
            self.original_image = None
            self.preview_result = None
            self._preview_source_cache.clear()
            self._source_revision += 1
            self.processed_view.clear_image()
            self.file_label.setText(self.video_path.name)
            self.input_size_label.setText(f"{info.width} × {info.height} · {info.fps:.2f} fps · {info.duration:.2f} s")
            self.source_type_label.setText("Video source")
            self.video_controls.setVisible(True)
            self.export_action.setEnabled(False)
            self.export_media_action.setEnabled(True)
            self.extract_button.setEnabled(False)
            self.video_slider.blockSignals(True)
            self.video_slider.setValue(0)
            self.video_slider.blockSignals(False)
            self.video_time_label.setText("0.00 s")
            self._update_output_size_label()
            self.app_settings.setValue("lastOpenDir", str(self.video_path.parent))
            self._request_video_frame(0.0)
            self.statusBar().showMessage(f"Loaded video {self.video_path.name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Could not open video", str(exc))

    def _set_image_source(self, image: Image.Image, path: Path | None, *, is_video: bool) -> None:
        self.original_image = image
        if not is_video:
            self.video_path = None
            self.video_info = None
            self.video_time = 0.0
            self.current_file = path
            self.video_controls.setVisible(False)
            self.source_type_label.setText("Image source")
            if path:
                self.file_label.setText(path.name)
                self.app_settings.setValue("lastOpenDir", str(path.parent))
        self.preview_result = None
        self._preview_source_cache.clear()
        self._source_revision += 1
        self.processed_view.clear_image()
        self.input_size_label.setText(f"{image.width} × {image.height}" if not is_video else self.input_size_label.text())
        self._update_output_size_label()
        self.export_action.setEnabled(True)
        self.export_media_action.setEnabled(True)
        self.extract_button.setEnabled(True)
        self.schedule_preview(immediate=True, force=True)

    def dragEnterEvent(self, event) -> None:
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        supported = SUPPORTED_IMAGE_SUFFIXES | SUPPORTED_VIDEO_SUFFIXES
        if any(url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in supported for url in urls):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        supported = SUPPORTED_IMAGE_SUFFIXES | SUPPORTED_VIDEO_SUFFIXES
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in supported:
                self._load_dropped_path(url.toLocalFile())
                event.acceptProposedAction()
                return
        event.ignore()

    # ---------- video preview ----------
    def _video_slider_changed(self, value: int) -> None:
        if self.video_info is None:
            return
        self.video_time = self.video_info.duration * value / 1000.0
        self.video_time_label.setText(f"{self.video_time:.2f} s")
        self._request_video_frame(self.video_time)

    def _toggle_video_playback(self, playing: bool) -> None:
        self._video_playing = playing
        self.video_play_button.setText("❚❚" if playing else "▶")
        if playing and self.video_info:
            preview_fps = max(1.0, min(15.0, self.video_info.fps))
            self.video_play_timer.start(max(25, round(1000 / preview_fps)))
        else:
            self.video_play_timer.stop()
            if self.original_image is not None:
                self.schedule_preview(force=True, refined=True)

    def _video_play_tick(self) -> None:
        if not self.video_info:
            return
        preview_fps = max(1.0, min(15.0, self.video_info.fps))
        new_time = self.video_time + 1.0 / preview_fps
        if new_time >= self.video_info.duration:
            new_time = 0.0
        self.video_time = new_time
        self.video_slider.blockSignals(True)
        self.video_slider.setValue(round(1000 * new_time / max(0.001, self.video_info.duration)))
        self.video_slider.blockSignals(False)
        self.video_time_label.setText(f"{new_time:.2f} s")
        self._request_video_frame(new_time)

    def _request_video_frame(self, time_seconds: float) -> None:
        if self.video_path is None:
            return
        if self._video_frame_running:
            self._pending_video_time = time_seconds
            return
        job_id = self._next_job_id()
        self._latest_video_job = job_id
        self._video_frame_running = True
        worker = VideoFrameWorker(job_id, str(self.video_path), time_seconds)
        worker.signals.finished.connect(self._worker_finished)
        worker.signals.failed.connect(self._worker_failed)
        self.thread_pool.start(worker)

    def _start_pending_video_frame(self) -> None:
        pending = self._pending_video_time
        self._pending_video_time = None
        if pending is not None:
            QTimer.singleShot(0, lambda t=pending: self._request_video_frame(t))

    # ---------- rendering ----------
    def _request_refined_preview(self) -> None:
        if self.original_image is None:
            return
        mode = self._preview_mode()
        if mode == "full":
            divisor = int(self.output_scale_combo.currentData() or 1)
            full_size = scaled_output_size(self.original_image.size, divisor)
            side = max(full_size)
        else:
            side = PREVIEW_MAX_SIDE
        self._request_preview(side)

    def schedule_preview(self, immediate: bool = False, force: bool = False, refined: bool = True) -> None:
        if self.original_image is None:
            return
        if not force and not self.live_preview_check.isChecked():
            return

        playing = self.animation_panel.is_playing() or self._video_playing
        mode = self._preview_mode()
        self.preview_timer.stop()

        # Playback always uses the fast draft budget so animation/video controls
        # remain responsive even when Full preview is selected.
        if playing:
            if immediate:
                self._request_preview(FAST_PREVIEW_MAX_SIDE)
            else:
                self.preview_timer.start()
            self.preview_refine_timer.stop()
            return

        if mode == "live":
            if immediate:
                self._request_preview(FAST_PREVIEW_MAX_SIDE)
            else:
                self.preview_timer.start()
        elif immediate and force:
            # Explicit source changes/manual mode changes should not leave the
            # viewport blank while waiting for the idle timer.
            self._request_refined_preview()

        if refined:
            self.preview_refine_timer.start()
        else:
            self.preview_refine_timer.stop()

    def _next_job_id(self) -> int:
        self._job_counter += 1
        return self._job_counter

    def _request_preview(self, max_side: int) -> None:
        if self.original_image is None:
            return
        base_settings = self._settings_from_controls()
        animation_time = self.animation_panel.current_time()
        # On still images, animation follows the animation timeline. On video,
        # tracks follow source time so playback and final video export use the
        # same parameter values for a given frame.
        render_time = self.video_time if self.video_path else animation_time
        settings = settings_at_time(base_settings, render_time)
        max_side = max(64, int(max_side))
        max_side = adaptive_preview_max_side(settings, max_side)

        if self._preview_running:
            self._preview_pending_max_side = max(self._preview_pending_max_side, max_side)
            return

        divisor = settings.output_divisor
        cache_key = (divisor, max_side)
        preview_source = self._preview_source_cache.get(cache_key)
        if preview_source is None:
            preview_source = make_preview_source(self.original_image, max_side=max_side, output_divisor=divisor)
            self._preview_source_cache[cache_key] = preview_source
        final_size = scaled_output_size(self.original_image.size, divisor)
        preview_settings = make_preview_settings(settings, final_size, preview_source.size)

        job_id = self._next_job_id()
        self._latest_preview_job = job_id
        self._preview_running = True
        self._preview_pending_max_side = 0
        quality = "draft" if max_side <= FAST_PREVIEW_MAX_SIDE else ("full" if self._preview_mode() == "full" and max_side > PREVIEW_MAX_SIDE else "refined")
        context = {
            "source_revision": self._source_revision,
            "settings_revision": self._settings_revision,
            "quality": quality,
            "max_side": max_side,
        }
        self.statusBar().showMessage(f"Rendering {quality} preview…")
        frame_index = max(0, round(render_time * max(1, base_settings.animation_fps)))
        worker = ProcessingWorker(
            job_id,
            "preview",
            preview_source,
            preview_settings,
            context,
            frame_time=render_time,
            frame_index=frame_index,
        )
        worker.signals.finished.connect(self._worker_finished)
        worker.signals.failed.connect(self._worker_failed)
        self.thread_pool.start(worker)

    def _start_pending_preview(self) -> None:
        side = self._preview_pending_max_side
        self._preview_pending_max_side = 0
        if side:
            QTimer.singleShot(0, lambda s=side: self._request_preview(s))

    def _worker_finished(self, job_id: int, purpose: str, result: object, context: object) -> None:
        if purpose == "preview":
            self._preview_running = False
            ctx = context if isinstance(context, dict) else {}
            if (
                job_id == self._latest_preview_job
                and int(ctx.get("source_revision", -1)) == self._source_revision
                and int(ctx.get("settings_revision", -1)) == self._settings_revision
                and isinstance(result, Image.Image)
            ):
                self.preview_result = result
                self.processed_view.set_pixmap(pil_to_pixmap(result))
                self.statusBar().showMessage(
                    f"{str(ctx.get('quality', 'preview')).title()} · {result.width} × {result.height}", 1800
                )
            self._start_pending_preview()
            return

        if purpose == "video-frame":
            self._video_frame_running = False
            if job_id == self._latest_video_job and isinstance(result, Image.Image):
                self.original_image = result
                self._preview_source_cache.clear()
                self._source_revision += 1
                self._update_output_size_label()
                self.export_action.setEnabled(True)
                self.extract_button.setEnabled(True)
                self.schedule_preview(immediate=True, force=True, refined=not self._video_playing)
            self._start_pending_video_frame()
            return

        if purpose == "export":
            self._export_jobs.discard(job_id)
            path = Path(str(context))
            try:
                if not isinstance(result, Image.Image):
                    raise TypeError("Renderer returned an invalid image")
                if path.suffix.lower() == ".svg":
                    save_svg(result, path)
                else:
                    kwargs = {"quality": 95, "subsampling": 0} if path.suffix.lower() in {".jpg", ".jpeg"} else {}
                    result.save(path, **kwargs)
                self.statusBar().showMessage(f"Exported {path.name}", 5000)
            except Exception as exc:
                QMessageBox.critical(self, "Export failed", str(exc))
            return

        if purpose == "media-export":
            self._export_jobs.discard(job_id)
            self.statusBar().showMessage(f"Exported {Path(str(result)).name}", 6000)
            return

        if purpose == "batch":
            self._export_jobs.discard(job_id)
            count = len(result) if isinstance(result, list) else 0
            self.statusBar().showMessage(f"Batch export complete: {count} files", 6000)

    def _worker_failed(self, job_id: int, purpose: str, trace: str, context: object) -> None:
        if purpose == "preview":
            self._preview_running = False
            self._start_pending_preview()
        elif purpose == "video-frame":
            self._video_frame_running = False
            self._start_pending_video_frame()
        self._export_jobs.discard(job_id)
        short = trace.strip().splitlines()[-1] if trace.strip() else "Unknown processing error"
        self.statusBar().showMessage(short, 6000)
        if purpose != "preview" or job_id == self._latest_preview_job:
            QMessageBox.critical(self, "Processing error", trace)

    def _worker_progress(self, _job_id: int, purpose: str, current: int, total: int, label: str) -> None:
        total_text = str(total) if total > 0 else "?"
        self.statusBar().showMessage(f"{purpose}: {current}/{total_text} · {label}")

    # ---------- exports ----------
    def export_image_dialog(self) -> None:
        if self.original_image is None:
            return
        base_dir = Path(self.app_settings.value("lastExportDir", str(self.current_file.parent if self.current_file else Path.home())))
        stem = self.current_file.stem if self.current_file else "image"
        path, selected_filter = QFileDialog.getSaveFileName(self, "Export current processed frame", str(base_dir / f"{stem}-rastermint.png"), EXPORT_FILTER)
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            suffix = ".svg" if selected_filter.startswith("SVG") else ".jpg" if selected_filter.startswith("JPEG") else ".webp" if selected_filter.startswith("WebP") else ".bmp" if selected_filter.startswith("BMP") else ".tiff" if selected_filter.startswith("TIFF") else ".png"
            target = target.with_suffix(suffix)

        base_settings = self._settings_from_controls()
        parameter_time = self.video_time if self.video_path else self.animation_panel.current_time()
        settings = settings_at_time(base_settings, parameter_time)
        job_id = self._next_job_id()
        self._export_jobs.add(job_id)
        worker = ProcessingWorker(
            job_id,
            "export",
            self.original_image,
            settings,
            str(target),
            frame_time=self.video_time if self.video_path else self.animation_panel.current_time(),
            frame_index=round(self.animation_panel.current_time() * base_settings.animation_fps),
        )
        worker.signals.finished.connect(self._worker_finished)
        worker.signals.failed.connect(self._worker_failed)
        self.thread_pool.start(worker)
        self.app_settings.setValue("lastExportDir", str(target.parent))
        self.statusBar().showMessage(f"Rendering {target.name}…")

    def export_media_dialog(self) -> None:
        if self.original_image is None and self.video_path is None:
            return
        base_dir = Path(self.app_settings.value("lastExportDir", str(Path.home())))
        stem = self.current_file.stem if self.current_file else "animation"
        if self.video_path:
            path, _ = QFileDialog.getSaveFileName(self, "Export processed video", str(base_dir / f"{stem}-rastermint.mp4"), "MP4 video (*.mp4)")
        else:
            path, selected = QFileDialog.getSaveFileName(self, "Export animation", str(base_dir / f"{stem}-rastermint.mp4"), ANIMATION_FILTER)
            if path and not Path(path).suffix:
                path += ".gif" if selected.startswith("Animated GIF") else ".mp4"
        if not path:
            return
        settings = self._settings_from_controls()
        job_id = self._next_job_id()
        self._export_jobs.add(job_id)
        worker = MediaExportWorker(
            job_id,
            settings,
            path,
            image=self.original_image if self.video_path is None else None,
            video_path=str(self.video_path) if self.video_path else None,
            include_audio=True,
        )
        worker.signals.finished.connect(self._worker_finished)
        worker.signals.failed.connect(self._worker_failed)
        worker.signals.progress.connect(self._worker_progress)
        self.thread_pool.start(worker)
        self.app_settings.setValue("lastExportDir", str(Path(path).parent))
        self.statusBar().showMessage(f"Exporting {Path(path).name}…")

    def batch_export_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select images for batch processing", str(Path.home()), IMAGE_FILTER)
        if not paths:
            return
        output_dir = QFileDialog.getExistingDirectory(self, "Choose batch output folder", str(Path.home()))
        if not output_dir:
            return
        settings = self._settings_from_controls()
        job_id = self._next_job_id()
        self._export_jobs.add(job_id)
        worker = BatchWorker(job_id, paths, output_dir, settings)
        worker.signals.finished.connect(self._worker_finished)
        worker.signals.failed.connect(self._worker_failed)
        worker.signals.progress.connect(self._worker_progress)
        self.thread_pool.start(worker)

    # ---------- presets ----------
    def save_preset_dialog(self) -> None:
        start_dir = self.app_settings.value("lastPresetDir", str(Path.home()))
        path, _ = QFileDialog.getSaveFileName(self, "Save preset", start_dir, PRESET_FILTER)
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".rmpreset")
        try:
            save_preset(target, self._settings_from_controls())
            self.app_settings.setValue("lastPresetDir", str(target.parent))
            self.statusBar().showMessage(f"Saved preset {target.name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Could not save preset", str(exc))

    def load_preset_dialog(self) -> None:
        start_dir = self.app_settings.value("lastPresetDir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(self, "Load preset", start_dir, PRESET_FILTER)
        if not path:
            return
        try:
            settings = load_preset(path)
            self._apply_settings_to_controls(settings)
            self.app_settings.setValue("lastPresetDir", str(Path(path).parent))
            self.statusBar().showMessage(f"Loaded preset {Path(path).name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Could not load preset", str(exc))

    def reset_settings(self) -> None:
        settings = ProcessingSettings()
        settings.effect_stack = default_effect_stack(settings)
        self._apply_settings_to_controls(settings)

    # ---------- misc ----------
    def _update_output_size_label(self) -> None:
        if self.original_image is None:
            self.output_size_label.setText("—")
            return
        divisor = int(self.output_scale_combo.currentData() or 1)
        width, height = scaled_output_size(self.original_image.size, divisor)
        self.output_size_label.setText(f"{width} × {height}" + ("" if divisor == 1 else f" (÷{divisor})"))

    def fit_views(self) -> None:
        self.processed_view.fit_image()

    def _restore_geometry(self) -> None:
        geometry = self.app_settings.value("windowGeometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.app_settings.setValue("windowGeometry", self.saveGeometry())
        super().closeEvent(event)
