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

Its PyPI wheels can include a platform-specific **FFmpeg executable**. FFmpeg is a separate project and the exact license obligations of a binary depend on how that FFmpeg executable was configured and which optional components were enabled.

RasterMint's Windows release build deliberately creates a smaller static FFmpeg through vcpkg with only the external features RasterMint needs (`x264` and `zlib`, plus FFmpeg's core application/resample/scale libraries). The build is capability-tested for RasterMint's raw-RGB/H.264 MP4 pipeline, AAC audio preservation, common video demuxing/decoding, and GIF palette export before PyInstaller is allowed to bundle it. The `x264` feature enables GPL code, so the resulting Windows FFmpeg executable is subject to the applicable FFmpeg/x264 GPL requirements. Local or non-Windows builds can still fall back to the executable provided by `imageio-ffmpeg`.

Before redistributing a RasterMint binary, inspect the bundled FFmpeg build (`ffmpeg -version`) and comply with FFmpeg and enabled-component license/source requirements.

- https://ffmpeg.org/legal.html
- https://ffmpeg.org/doxygen/trunk/md_LICENSE.html
- https://www.videolan.org/developers/x264.html
- https://vcpkg.io/en/package/ffmpeg

## PyInstaller

PyInstaller is used only to build release artifacts and has its own licensing terms.

- https://pyinstaller.org/

## Lospec

RasterMint connects to Lospec's documented palette API. Lospec is an external service and is not bundled with RasterMint.

- https://lospec.com/palettes/api
- https://lospec.com/palette-list

## Solarized

RasterMint includes Solarized Dark and Solarized Light application themes based on
the Solarized color scheme by Ethan Schoonover. Solarized is distributed under the
MIT License.

Copyright (c) 2011 Ethan Schoonover

- https://ethanschoonover.com/solarized/
- https://github.com/altercation/solarized
