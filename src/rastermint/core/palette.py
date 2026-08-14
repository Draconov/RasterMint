# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from pathlib import Path
import re
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
    "Game Boy": ["#0F380F", "#306230", "#8BAC0F", "#9BBC0F"],
    "PICO-8": [
        "#000000", "#1D2B53", "#7E2553", "#008751", "#AB5236", "#5F574F", "#C2C3C7", "#FFF1E8",
        "#FF004D", "#FFA300", "#FFEC27", "#00E436", "#29ADFF", "#83769C", "#FF77A8", "#FFCCAA",
    ],
}


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6 or not re.fullmatch(r"[0-9A-Fa-f]{6}", value):
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


def quantize_nearest(image: np.ndarray, palette: np.ndarray, chunk_pixels: int = 32768) -> np.ndarray:
    """Nearest RGB palette mapping with bounded memory.

    Uses squared-distance matrix algebra instead of allocating a giant
    [height,width,palette,rgb] temporary array. This matters for 64/128/256
    color Lospec palettes.
    """
    source = np.asarray(image, dtype=np.float32)
    h, w, _ = source.shape
    pixels = source.reshape(-1, 3)
    pal = np.asarray(palette, dtype=np.float32)
    pal_sq = np.sum(pal * pal, axis=1)
    out = np.empty_like(pixels)
    for start in range(0, len(pixels), max(1024, int(chunk_pixels))):
        end = min(len(pixels), start + max(1024, int(chunk_pixels)))
        chunk = pixels[start:end]
        chunk_sq = np.sum(chunk * chunk, axis=1, keepdims=True)
        distances = chunk_sq + pal_sq[None, :] - 2.0 * (chunk @ pal.T)
        out[start:end] = pal[np.argmin(distances, axis=1)]
    return out.reshape(h, w, 3)


def extract_palette(image: Image.Image, colors: int = 8) -> list[str]:
    colors = max(2, min(256, int(colors)))
    img = image.convert("RGB")
    thumb = img.copy()
    thumb.thumbnail((512, 512), Image.Resampling.LANCZOS)
    q = thumb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette() or []
    counts = q.getcolors(maxcolors=max(1024, colors * 4)) or []
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
    def lum(value: str) -> float:
        r, g, b = hex_to_rgb(value)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    return sorted(colors, key=lum)


def read_palette_file(path: str | Path) -> list[str]:
    source = Path(path)
    text = source.read_text(encoding="utf-8", errors="replace")
    suffix = source.suffix.lower()
    colors: list[str] = []

    if suffix == ".gpl":
        for line in text.splitlines():
            match = re.match(r"\s*(\d+)\s+(\d+)\s+(\d+)(?:\s+.*)?$", line)
            if match:
                colors.append(rgb_to_hex(map(int, match.groups())))
    elif suffix == ".pal" and text.lstrip().startswith("JASC-PAL"):
        lines = text.splitlines()[3:]
        for line in lines:
            parts = line.split()
            if len(parts) >= 3 and all(part.isdigit() for part in parts[:3]):
                colors.append(rgb_to_hex(map(int, parts[:3])))
    else:
        for match in re.finditer(r"#?([0-9A-Fa-f]{6})(?![0-9A-Fa-f])", text):
            colors.append(f"#{match.group(1).upper()}")

    deduped: list[str] = []
    for color in colors:
        if color not in deduped:
            deduped.append(color)
    if not deduped:
        raise ValueError(f"No palette colors found in {source.name}")
    return deduped[:256]


def write_hex_palette(path: str | Path, colors: Iterable[str]) -> None:
    clean = [f"{rgb_to_hex(hex_to_rgb(c))[1:]}" for c in colors]
    if not clean:
        raise ValueError("Palette is empty")
    Path(path).write_text("\n".join(clean) + "\n", encoding="utf-8")
