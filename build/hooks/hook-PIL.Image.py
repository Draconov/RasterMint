# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Lean Pillow image-plugin hook for RasterMint.

PyInstaller's stock PIL.Image hook includes every Pillow ImagePlugin. RasterMint
explicitly supports PNG, JPEG, BMP, WebP, TIFF, and GIF input/output, so bundle
only the plugins for those formats. Pillow's normal static imports still pull in
all helper modules/native extensions required by these selected plugins.
"""

# Keep this list aligned with RasterMint's FileDialog filters and IMAGE_SUFFIXES.
hiddenimports = [
    "PIL.BmpImagePlugin",
    "PIL.GifImagePlugin",
    "PIL.JpegImagePlugin",
    "PIL.PngImagePlugin",
    "PIL.TiffImagePlugin",
    "PIL.WebPImagePlugin",
]
