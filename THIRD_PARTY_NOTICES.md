# Third-Party Notices

RasterMint's own source is licensed separately. Dependencies and bundled third-party binaries keep their own licenses.

## Qt / PySide6

RasterMint uses Qt for Python (PySide6). Qt/PySide6 distribution can involve LGPL/GPL or commercial Qt licensing depending on the components and distribution choice. Anyone distributing RasterMint binaries, especially commercially, must review the applicable Qt licensing obligations for the exact build.

Official licensing information:

- https://doc.qt.io/qtforpython-6/licenses.html
- https://www.qt.io/licensing

## NumPy

NumPy is distributed under its own BSD-style license.

- https://numpy.org/

## Pillow

Pillow is distributed under the HPND License.

- https://python-pillow.github.io/

## imageio-ffmpeg

RasterMint uses `imageio-ffmpeg`, whose Python wrapper project is BSD-2-Clause licensed.

- https://github.com/imageio/imageio-ffmpeg

Its PyPI wheels can include a platform-specific **FFmpeg executable**. FFmpeg is a separate project and the exact license obligations of a binary depend on how that FFmpeg executable was configured and which optional components were enabled. RasterMint's PyInstaller spec currently bundles the executable provided by the installed `imageio-ffmpeg` package when one is present.

Before redistributing a RasterMint binary commercially, inspect the bundled FFmpeg build (`ffmpeg -version`) and comply with FFmpeg and enabled-component license/source requirements. If necessary, replace the bundled executable with a deliberately built/licensed FFmpeg configuration or depend on an external system FFmpeg.

- https://ffmpeg.org/legal.html
- https://ffmpeg.org/doxygen/trunk/md_LICENSE.html

## PyInstaller

PyInstaller is used only to build release artifacts and has its own licensing terms.

- https://pyinstaller.org/

## Lospec

RasterMint connects to Lospec's documented palette API. Lospec is an external service and is not bundled with RasterMint.

- https://lospec.com/palettes/api
- https://lospec.com/palette-list
