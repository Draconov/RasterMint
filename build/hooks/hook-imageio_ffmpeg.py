# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""Keep imageio-ffmpeg's executable selection under RasterMint's spec control.

The upstream PyInstaller contrib hook collects ``imageio_ffmpeg/binaries`` as
package data. That would make optimized Windows builds contain both the large
wheel FFmpeg and RasterMint's lean validated FFmpeg. ``build/rastermint.spec``
already bundles exactly one executable with the right binary semantics, so this
hook only preserves the resource package import needed by imageio-ffmpeg 0.5+.
"""

from PyInstaller.utils.hooks import is_module_satisfies


datas = []
binaries = []
hiddenimports = []
if is_module_satisfies("imageio_ffmpeg >= 0.5.0"):
    hiddenimports = ["imageio_ffmpeg.binaries"]
