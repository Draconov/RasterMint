# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np
from PIL import Image


def _opacity_text(alpha: int) -> str:
    value = max(0.0, min(1.0, int(alpha) / 255.0))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def image_to_svg(image: Image.Image) -> str:
    """Vectorize a raster image as horizontal same-RGBA rectangle runs."""
    arr = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    height, width, _ = arr.shape
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" shape-rendering="crispEdges">'
    ]
    for y in range(height):
        row = arr[y]
        start = 0
        color = row[0]
        for x in range(1, width + 1):
            changed = x == width or not np.array_equal(row[x], color)
            if changed:
                alpha = int(color[3])
                if alpha > 0:
                    hex_color = f"#{int(color[0]):02X}{int(color[1]):02X}{int(color[2]):02X}"
                    opacity = "" if alpha == 255 else f' fill-opacity="{_opacity_text(alpha)}"'
                    parts.append(
                        f'<rect x="{start}" y="{y}" width="{x - start}" height="1" '
                        f'fill="{escape(hex_color)}"{opacity}/>'
                    )
                if x < width:
                    start = x
                    color = row[x]
    parts.append("</svg>")
    return "\n".join(parts)


def save_svg(image: Image.Image, path: str | Path) -> None:
    Path(path).write_text(image_to_svg(image), encoding="utf-8")
