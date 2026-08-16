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
hiddenimports = collect_submodules("PIL") + collect_submodules("imageio_ffmpeg")
metadata = copy_metadata("rastermint") + copy_metadata("imageio-ffmpeg")
package_data = collect_data_files("rastermint", includes=["data/hardware_profiles/*.json", "data/icons/*", "data/themes/*.json", "qml/*.qml", "qml/components/*.qml", "qml/pages/*.qml"])
ICON_DIR = ROOT / "src" / "rastermint" / "data" / "icons"

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
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
