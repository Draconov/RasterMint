from __future__ import annotations

import math
from typing import Iterable

import numpy as np
from PIL import Image

BUILTIN_PALETTES: dict[str, list[str]] = {
    "Ink": ["#0B1020", "#F3F7FF"],
    "Graphite 4": ["#101217", "#4A4F59", "#A9AFB9", "#F4F6F8"],
    "Forest 4": ["#0D1B16", "#244D3D", "#6B9B64", "#D6E7B0"],
    "Amber 4": ["#1B1209", "#70431D", "#D08A2E", "#FFE0A1"],
    "Ocean 6": ["#08131D", "#12344A", "#1E6070", "#3F8E95", "#88BFB7", "#E2EFE7"],
    "Arcade 8": ["#151515", "#E83B3B", "#FF8C42", "#F4E04D", "#57C84D", "#36A2AE", "#4D63D6", "#E8E8E8"],
}


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"Invalid hex color: {value!r}")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Iterable[int]) -> str:
    r, g, b = (max(0, min(255, int(v))) for v in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def palette_array(colors: Iterable[str]) -> np.ndarray:
    arr = np.asarray([hex_to_rgb(c) for c in colors], dtype=np.float32)
    if arr.size == 0:
        raise ValueError("Palette must contain at least one color")
    return arr


def nearest_palette_index(pixel: np.ndarray, palette: np.ndarray) -> int:
    diff = palette - pixel
    return int(np.argmin(np.einsum("ij,ij->i", diff, diff)))


def quantize_nearest(image: np.ndarray, palette: np.ndarray, chunk_rows: int = 64) -> np.ndarray:
    """Nearest RGB palette mapping with bounded memory usage."""
    h, w, _ = image.shape
    out = np.empty((h, w, 3), dtype=np.float32)
    for y0 in range(0, h, chunk_rows):
        y1 = min(h, y0 + chunk_rows)
        chunk = image[y0:y1]
        # [rows, width, palette, rgb]
        diff = chunk[:, :, None, :] - palette[None, None, :, :]
        dist = np.sum(diff * diff, axis=3)
        idx = np.argmin(dist, axis=2)
        out[y0:y1] = palette[idx]
    return out


def extract_palette(image: Image.Image, colors: int = 8) -> list[str]:
    colors = max(2, min(32, int(colors)))
    img = image.convert("RGB")
    thumb = img.copy()
    thumb.thumbnail((512, 512), Image.Resampling.LANCZOS)
    q = thumb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette() or []
    counts = q.getcolors(maxcolors=colors * 4) or []
    counts.sort(reverse=True)
    result: list[str] = []
    for _, idx in counts:
        base = idx * 3
        if base + 2 < len(pal):
            c = rgb_to_hex(pal[base : base + 3])
            if c not in result:
                result.append(c)
    if len(result) < 2:
        return BUILTIN_PALETTES["Ink"].copy()
    return result[:colors]


def sort_palette_by_luminance(colors: Iterable[str]) -> list[str]:
    def lum(h: str) -> float:
        r, g, b = hex_to_rgb(h)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    return sorted(colors, key=lum)
