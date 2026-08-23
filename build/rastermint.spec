# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# -*- mode: python ; coding: utf-8 -*-

from importlib.metadata import version as distribution_version
from pathlib import Path
import sys

import imageio_ffmpeg

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

ROOT = Path(SPECPATH).parent
APP_VERSION = distribution_version("rastermint")

# imageio-ffmpeg is intentionally kept conservative because video must work fully
# offline. Pillow is handled by our format-aware hook instead of collecting every
# optional PIL module (ImageTk, development helpers, unsupported codecs, etc.).
hiddenimports = collect_submodules("imageio_ffmpeg")
metadata = copy_metadata("rastermint") + copy_metadata("imageio-ffmpeg")
package_data = collect_data_files(
    "rastermint",
    includes=[
        "data/hardware_profiles/*.json",
        "data/icons/*",
        "data/themes/*.json",
        "data/palettes/*.json",
        "data/palettes/base/*.json",
        "data/palettes/extended/*.json",
        "data/presets/*.json",
        "qml/*.qml",
        "qml/components/*.qml",
        "qml/pages/*.qml",
    ],
)

ICON_DIR = ROOT / "src" / "rastermint" / "data" / "icons"
HOOK_DIR = ROOT / "build" / "hooks"
LEAN_QML_HOOK = HOOK_DIR / "hook-PySide6.QtQml.py"
LEAN_PIL_HOOK = HOOK_DIR / "hook-PIL.Image.py"

# Do not silently fall back to PyInstaller's stock QtQml hook. That hook copies
# the complete PySide6 QML tree and makes the release roughly as large as the
# unoptimized build. The custom hook must be tracked in git and present in CI.
for required_hook in (LEAN_QML_HOOK, LEAN_PIL_HOOK):
    if not required_hook.is_file():
        raise RuntimeError(
            f"Required lean packaging hook is missing: {required_hook}. "
            "Check .gitignore and make sure build/hooks is committed."
        )

# These bindings are not used by RasterMint. Keeping them out prevents an
# accidental import or Qt dependency discovered by a hook from pulling large
# optional Qt feature families into the frozen application.
UNUSED_QT_MODULES = [
    # Web / documents / charts.
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebChannel",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtCharts",
    "PySide6.QtGraphs",
    "PySide6.QtGraphsWidgets",
    "PySide6.QtDataVisualization",
    # 3D / spatial / media.
    "PySide6.QtQuick3D",
    "PySide6.QtQuick3DAssetImport",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtSpatialAudio",
    "PySide6.QtVirtualKeyboard",
    # Hardware / protocols / services not used by the desktop app.
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtLocation",
    "PySide6.QtPositioning",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtTextToSpeech",
    "PySide6.QtHttpServer",
    "PySide6.QtNetworkAuth",
    "PySide6.QtCoap",
    "PySide6.QtMqtt",
    "PySide6.QtOpcUa",
    "PySide6.QtProtobuf",
    "PySide6.QtProtobufWidgets",
    "PySide6.QtGrpc",
]

# Ship the platform-specific ffmpeg executable as a binary so one-file builds
# keep its executable permission when PyInstaller extracts it at runtime.
ffmpeg_exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
ffmpeg_binaries = []
if ffmpeg_exe.is_file() and ffmpeg_exe.parent.name == "binaries":
    ffmpeg_binaries.append((str(ffmpeg_exe), "imageio_ffmpeg/binaries"))

a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT / "src")],
    binaries=ffmpeg_binaries,
    datas=metadata + package_data,
    hiddenimports=hiddenimports,
    # The RasterMint hook replaces PyInstaller's default PySide6.QtQml hook,
    # which otherwise packages every Qt QML module shipped in the wheel.
    hookspath=[str(HOOK_DIR)],
    hooksconfig={},
    runtime_hooks=[],
    excludes=UNUSED_QT_MODULES,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

# One-file build: no COLLECT stage. PyInstaller embeds Qt/Python dependencies
# and the platform ffmpeg executable inside the application.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RasterMint",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_DIR / "rastermint.ico") if (ICON_DIR / "rastermint.ico").is_file() else None,
)

# macOS users receive a normal .app bundle. Windows and Linux keep the one-file
# executable produced above.
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="RasterMint.app",
        icon=str(ICON_DIR / "rastermint.icns") if (ICON_DIR / "rastermint.icns").is_file() else None,
        bundle_identifier="io.github.draconov.rastermint",
        version=APP_VERSION,
    )
