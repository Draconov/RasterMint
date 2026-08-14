# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSettings, Qt, QThreadPool, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QImage, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from rastermint import __app_name__, __version__
from rastermint.core.dither import ALGORITHMS
from rastermint.core.palette import BUILTIN_PALETTES, extract_palette
from rastermint.core.presets import load_preset, save_preset
from rastermint.core.processor import make_preview_source
from rastermint.core.settings import ProcessingSettings
from rastermint.ui.image_view import ImageView
from rastermint.ui.palette_editor import PaletteEditor
from rastermint.ui.worker import ProcessingWorker

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff);;All files (*.*)"
EXPORT_FILTER = "PNG (*.png);;JPEG (*.jpg *.jpeg);;WebP (*.webp);;BMP (*.bmp);;TIFF (*.tif *.tiff)"
PRESET_FILTER = "RasterMint preset (*.rmpreset);;JSON (*.json)"


def pil_to_pixmap(image: Image.Image) -> QPixmap:
    rgba = image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


class LabeledSlider(QWidget):
    value_changed = None

    def __init__(self, minimum: int, maximum: int, value: int, suffix: str = "", parent=None) -> None:
        super().__init__(parent)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.value_label = QLabel()
        self.value_label.setMinimumWidth(45)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.suffix = suffix
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.slider, 1)
        row.addWidget(self.value_label)
        self.slider.valueChanged.connect(self._sync_label)
        self._sync_label(value)

    def _sync_label(self, value: int) -> None:
        self.value_label.setText(f"{value}{self.suffix}")

    def value(self) -> int:
        return self.slider.value()

    def setValue(self, value: int) -> None:
        self.slider.setValue(value)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{__app_name__} {__version__}")
        self.resize(1380, 860)
        self.setMinimumSize(980, 620)
        self.setAcceptDrops(True)

        self.original_image: Image.Image | None = None
        self.preview_source: Image.Image | None = None
        self.preview_result: Image.Image | None = None
        self.current_file: Path | None = None
        self.settings = ProcessingSettings()
        self._job_counter = 0
        self._latest_preview_job = 0
        self._export_jobs: set[int] = set()
        self._loading_controls = False

        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(max(2, min(4, QThreadPool.globalInstance().maxThreadCount())))

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(130)
        self.preview_timer.timeout.connect(self.render_preview)

        self.app_settings = QSettings("RasterMint", "RasterMint")

        self._build_actions()
        self._build_toolbar()
        self._build_ui()
        self._restore_geometry()
        self._apply_settings_to_controls(self.settings)
        self.statusBar().showMessage("Open or drop an image to begin")

    # ---------- UI construction ----------
    def _build_actions(self) -> None:
        self.open_action = QAction("Open Image…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_image_dialog)

        self.export_action = QAction("Export Image…", self)
        self.export_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.export_action.triggered.connect(self.export_image_dialog)
        self.export_action.setEnabled(False)

        self.load_preset_action = QAction("Load Preset…", self)
        self.load_preset_action.setShortcut("Ctrl+L")
        self.load_preset_action.triggered.connect(self.load_preset_dialog)

        self.save_preset_action = QAction("Save Preset…", self)
        self.save_preset_action.setShortcut("Ctrl+Shift+S")
        self.save_preset_action.triggered.connect(self.save_preset_dialog)

        self.fit_action = QAction("Fit Views", self)
        self.fit_action.setShortcut("F")
        self.fit_action.triggered.connect(self.fit_views)

        self.reset_action = QAction("Reset Settings", self)
        self.reset_action.triggered.connect(self.reset_settings)

        self.quit_action = QAction("Quit", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.close)

        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction(self.load_preset_action)
        file_menu.addAction(self.save_preset_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(self.fit_action)

        edit_menu = self.menuBar().addMenu("Edit")
        edit_menu.addAction(self.reset_action)

    def _build_toolbar(self) -> None:
        bar = QToolBar("Main", self)
        bar.setMovable(False)
        bar.addAction(self.open_action)
        bar.addAction(self.export_action)
        bar.addSeparator()
        bar.addAction(self.fit_action)
        bar.addAction(self.reset_action)
        self.addToolBar(bar)

    def _build_ui(self) -> None:
        root_splitter = QSplitter(Qt.Orientation.Horizontal)
        root_splitter.setChildrenCollapsible(False)
        self.setCentralWidget(root_splitter)

        views_splitter = QSplitter(Qt.Orientation.Horizontal)
        views_splitter.setChildrenCollapsible(False)
        views_splitter.addWidget(self._make_view_panel("Original", "original"))
        views_splitter.addWidget(self._make_view_panel("Processed", "processed"))
        views_splitter.setSizes([520, 520])
        root_splitter.addWidget(views_splitter)

        controls = self._make_controls()
        root_splitter.addWidget(controls)
        root_splitter.setStretchFactor(0, 1)
        root_splitter.setStretchFactor(1, 0)
        root_splitter.setSizes([1050, 330])

    def _make_view_panel(self, title: str, kind: str) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        label = QLabel(title)
        label.setObjectName("viewTitle")
        layout.addWidget(label)
        view = ImageView()
        layout.addWidget(view, 1)
        if kind == "original":
            self.original_view = view
        else:
            self.processed_view = view
        return panel

    def _make_controls(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(310)
        scroll.setMaximumWidth(390)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(12, 12, 12, 18)
        layout.setSpacing(12)

        dither_box = QGroupBox("Dithering")
        dither_form = QFormLayout(dither_box)
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(ALGORITHMS)
        self.algorithm_combo.currentTextChanged.connect(self._controls_changed)
        dither_form.addRow("Algorithm", self.algorithm_combo)

        self.strength_spin = QDoubleSpinBox()
        self.strength_spin.setRange(0.0, 2.0)
        self.strength_spin.setDecimals(2)
        self.strength_spin.setSingleStep(0.05)
        self.strength_spin.valueChanged.connect(self._controls_changed)
        dither_form.addRow("Strength", self.strength_spin)

        self.pixel_spin = QSpinBox()
        self.pixel_spin.setRange(1, 32)
        self.pixel_spin.valueChanged.connect(self._controls_changed)
        dither_form.addRow("Pixel size", self.pixel_spin)

        self.serpentine_check = QCheckBox("Alternate scan direction")
        self.serpentine_check.toggled.connect(self._controls_changed)
        dither_form.addRow("", self.serpentine_check)
        layout.addWidget(dither_box)

        adjustments = QGroupBox("Adjustments")
        adj_form = QFormLayout(adjustments)
        self.brightness_slider = LabeledSlider(-100, 100, 0)
        self.contrast_slider = LabeledSlider(-100, 100, 0)
        self.saturation_slider = LabeledSlider(-100, 100, 0)
        for widget in (self.brightness_slider, self.contrast_slider, self.saturation_slider):
            widget.slider.valueChanged.connect(self._controls_changed)
        adj_form.addRow("Brightness", self.brightness_slider)
        adj_form.addRow("Contrast", self.contrast_slider)
        adj_form.addRow("Saturation", self.saturation_slider)

        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(0.1, 4.0)
        self.gamma_spin.setDecimals(2)
        self.gamma_spin.setSingleStep(0.05)
        self.gamma_spin.valueChanged.connect(self._controls_changed)
        adj_form.addRow("Gamma", self.gamma_spin)
        layout.addWidget(adjustments)

        palette_box = QGroupBox("Palette")
        palette_layout = QVBoxLayout(palette_box)
        self.palette_combo = QComboBox()
        self.palette_combo.addItems(list(BUILTIN_PALETTES.keys()) + ["Custom"])
        self.palette_combo.currentTextChanged.connect(self._palette_preset_changed)
        palette_layout.addWidget(self.palette_combo)

        self.palette_editor = PaletteEditor(self.settings.palette)
        self.palette_editor.palette_changed.connect(self._palette_edited)
        palette_layout.addWidget(self.palette_editor)

        extract_row = QHBoxLayout()
        self.extract_count = QSpinBox()
        self.extract_count.setRange(2, 32)
        self.extract_count.setValue(8)
        self.extract_button = QPushButton("Extract from image")
        self.extract_button.clicked.connect(self.extract_palette_from_image)
        self.extract_button.setEnabled(False)
        extract_row.addWidget(QLabel("Colors"))
        extract_row.addWidget(self.extract_count)
        extract_row.addWidget(self.extract_button, 1)
        palette_layout.addLayout(extract_row)
        layout.addWidget(palette_box)

        info_box = QGroupBox("Image")
        info_layout = QFormLayout(info_box)
        self.file_label = QLabel("—")
        self.file_label.setWordWrap(True)
        self.size_label = QLabel("—")
        info_layout.addRow("File", self.file_label)
        info_layout.addRow("Size", self.size_label)
        layout.addWidget(info_box)

        render_button = QPushButton("Render now")
        render_button.clicked.connect(self.render_preview)
        layout.addWidget(render_button)
        layout.addStretch(1)

        scroll.setWidget(body)
        return scroll

    # ---------- state ----------
    def _settings_from_controls(self) -> ProcessingSettings:
        return ProcessingSettings(
            algorithm=self.algorithm_combo.currentText(),
            brightness=self.brightness_slider.value(),
            contrast=self.contrast_slider.value(),
            saturation=self.saturation_slider.value(),
            gamma=self.gamma_spin.value(),
            dither_strength=self.strength_spin.value(),
            pixel_size=self.pixel_spin.value(),
            serpentine=self.serpentine_check.isChecked(),
            palette=self.palette_editor.colors(),
        )

    def _apply_settings_to_controls(self, settings: ProcessingSettings) -> None:
        self._loading_controls = True
        try:
            if settings.algorithm in ALGORITHMS:
                self.algorithm_combo.setCurrentText(settings.algorithm)
            self.brightness_slider.setValue(settings.brightness)
            self.contrast_slider.setValue(settings.contrast)
            self.saturation_slider.setValue(settings.saturation)
            self.gamma_spin.setValue(settings.gamma)
            self.strength_spin.setValue(settings.dither_strength)
            self.pixel_spin.setValue(settings.pixel_size)
            self.serpentine_check.setChecked(settings.serpentine)
            self.palette_editor.set_colors(settings.palette, emit=False)
            match = next((name for name, colors in BUILTIN_PALETTES.items() if colors == settings.palette), None)
            self.palette_combo.setCurrentText(match or "Custom")
        finally:
            self._loading_controls = False
        self.settings = self._settings_from_controls()
        if self.original_image is not None:
            self.schedule_preview()

    def _controls_changed(self, *_args) -> None:
        if self._loading_controls:
            return
        self.settings = self._settings_from_controls()
        self.schedule_preview()

    def _palette_preset_changed(self, name: str) -> None:
        if self._loading_controls or name == "Custom":
            return
        colors = BUILTIN_PALETTES.get(name)
        if colors:
            self._loading_controls = True
            self.palette_editor.set_colors(colors.copy(), emit=False)
            self._loading_controls = False
            self._controls_changed()

    def _palette_edited(self, _colors: list[str]) -> None:
        if self._loading_controls:
            return
        self._loading_controls = True
        self.palette_combo.setCurrentText("Custom")
        self._loading_controls = False
        self._controls_changed()

    # ---------- image loading ----------
    def open_image_dialog(self) -> None:
        start_dir = self.app_settings.value("lastOpenDir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(self, "Open image", start_dir, IMAGE_FILTER)
        if path:
            self.load_image(path)

    def load_image(self, path: str | os.PathLike[str]) -> None:
        try:
            with Image.open(path) as img:
                img.load()
                self.original_image = img.convert("RGB")
            self.current_file = Path(path)
            self.preview_source = make_preview_source(self.original_image)
            self.preview_result = None
            self.original_view.set_pixmap(pil_to_pixmap(self.preview_source))
            self.processed_view.clear_image()
            self.file_label.setText(self.current_file.name)
            self.size_label.setText(f"{self.original_image.width} × {self.original_image.height}")
            self.export_action.setEnabled(True)
            self.extract_button.setEnabled(True)
            self.app_settings.setValue("lastOpenDir", str(self.current_file.parent))
            self.statusBar().showMessage(f"Loaded {self.current_file.name}", 3000)
            self.schedule_preview(immediate=True)
        except Exception as exc:
            QMessageBox.critical(self, "Could not open image", str(exc))

    def dragEnterEvent(self, event) -> None:
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if any(url.isLocalFile() for url in urls):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.load_image(url.toLocalFile())
                event.acceptProposedAction()
                return

    # ---------- rendering ----------
    def schedule_preview(self, immediate: bool = False) -> None:
        if self.preview_source is None:
            return
        if immediate:
            self.preview_timer.stop()
            self.render_preview()
        else:
            self.preview_timer.start()

    def _next_job_id(self) -> int:
        self._job_counter += 1
        return self._job_counter

    def render_preview(self) -> None:
        if self.preview_source is None:
            return
        self.settings = self._settings_from_controls()
        job_id = self._next_job_id()
        self._latest_preview_job = job_id
        self.statusBar().showMessage("Rendering preview…")
        worker = ProcessingWorker(job_id, "preview", self.preview_source, self.settings)
        worker.signals.finished.connect(self._worker_finished)
        worker.signals.failed.connect(self._worker_failed)
        self.thread_pool.start(worker)

    def _worker_finished(self, job_id: int, purpose: str, result: object, context: object) -> None:
        if purpose == "preview":
            if job_id != self._latest_preview_job:
                return
            if isinstance(result, Image.Image):
                self.preview_result = result
                self.processed_view.set_pixmap(pil_to_pixmap(result))
                self.statusBar().showMessage(
                    f"Preview ready · {result.width} × {result.height} · {self.settings.algorithm}",
                    2500,
                )
            return

        if purpose == "export":
            self._export_jobs.discard(job_id)
            path = Path(str(context))
            try:
                if not isinstance(result, Image.Image):
                    raise TypeError("Renderer returned an invalid image")
                save_kwargs = {}
                if path.suffix.lower() in {".jpg", ".jpeg"}:
                    save_kwargs = {"quality": 95, "subsampling": 0}
                result.save(path, **save_kwargs)
                self.app_settings.setValue("lastExportDir", str(path.parent))
                self.statusBar().showMessage(f"Exported {path.name}", 5000)
            except Exception as exc:
                QMessageBox.critical(self, "Export failed", str(exc))

    def _worker_failed(self, job_id: int, purpose: str, trace: str, context: object) -> None:
        if purpose == "preview" and job_id != self._latest_preview_job:
            return
        if purpose == "export":
            self._export_jobs.discard(job_id)
        short = trace.strip().splitlines()[-1] if trace.strip() else "Unknown processing error"
        self.statusBar().showMessage(short, 6000)
        QMessageBox.critical(self, "Processing error", trace)

    # ---------- export ----------
    def export_image_dialog(self) -> None:
        if self.original_image is None:
            return
        base_dir = Path(self.app_settings.value("lastExportDir", str(self.current_file.parent if self.current_file else Path.home())))
        stem = self.current_file.stem if self.current_file else "image"
        suggested = base_dir / f"{stem}-rastermint.png"
        path, selected_filter = QFileDialog.getSaveFileName(self, "Export image", str(suggested), EXPORT_FILTER)
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            if selected_filter.startswith("JPEG"):
                target = target.with_suffix(".jpg")
            elif selected_filter.startswith("WebP"):
                target = target.with_suffix(".webp")
            elif selected_filter.startswith("BMP"):
                target = target.with_suffix(".bmp")
            elif selected_filter.startswith("TIFF"):
                target = target.with_suffix(".tiff")
            else:
                target = target.with_suffix(".png")

        self.settings = self._settings_from_controls()
        job_id = self._next_job_id()
        self._export_jobs.add(job_id)
        self.statusBar().showMessage(f"Rendering full-resolution export: {target.name}…")
        worker = ProcessingWorker(job_id, "export", self.original_image, self.settings, str(target))
        worker.signals.finished.connect(self._worker_finished)
        worker.signals.failed.connect(self._worker_failed)
        self.thread_pool.start(worker)

    # ---------- palette ----------
    def extract_palette_from_image(self) -> None:
        if self.original_image is None:
            return
        try:
            colors = extract_palette(self.original_image, self.extract_count.value())
            self.palette_editor.set_colors(colors)
            self.statusBar().showMessage(f"Extracted {len(colors)} colors", 2500)
        except Exception as exc:
            QMessageBox.critical(self, "Palette extraction failed", str(exc))

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
            self.settings = self._settings_from_controls()
            save_preset(target, self.settings)
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
            if settings.algorithm not in ALGORITHMS:
                raise ValueError(f"Preset uses unsupported algorithm: {settings.algorithm}")
            self._apply_settings_to_controls(settings)
            self.app_settings.setValue("lastPresetDir", str(Path(path).parent))
            self.statusBar().showMessage(f"Loaded preset {Path(path).name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Could not load preset", str(exc))

    def reset_settings(self) -> None:
        self._apply_settings_to_controls(ProcessingSettings())

    # ---------- window ----------
    def fit_views(self) -> None:
        self.original_view.fit_image()
        self.processed_view.fit_image()

    def _restore_geometry(self) -> None:
        geometry = self.app_settings.value("windowGeometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.app_settings.setValue("windowGeometry", self.saveGeometry())
        super().closeEvent(event)
