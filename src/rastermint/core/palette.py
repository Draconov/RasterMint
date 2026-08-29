# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

import numpy as np
from PIL import Image
from .gpu_accel import try_quantize_nearest

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
    """Nearest RGB palette mapping with optional OpenCL acceleration.

    GPU execution is opportunistic and lazy.  If no suitable OpenCL GPU/runtime
    is available (or a GPU operation fails), the original bounded-memory NumPy
    path is used unchanged.
    """
    source = np.asarray(image, dtype=np.float32)
    pal = np.asarray(palette, dtype=np.float32)
    accelerated = try_quantize_nearest(source, pal)
    if accelerated is not None:
        return accelerated
    h, w, _ = source.shape
    pixels = source.reshape(-1, 3)
    pal_sq = np.sum(pal * pal, axis=1)
    out = np.empty_like(pixels)
    for start in range(0, len(pixels), max(1024, int(chunk_pixels))):
        end = min(len(pixels), start + max(1024, int(chunk_pixels)))
        chunk = pixels[start:end]
        chunk_sq = np.sum(chunk * chunk, axis=1, keepdims=True)
        distances = chunk_sq + pal_sq[None, :] - 2.0 * (chunk @ pal.T)
        out[start:end] = pal[np.argmin(distances, axis=1)]
    return out.reshape(h, w, 3)

PALETTE_OPTIMIZERS = ["Median Cut", "K-Means", "Octree", "Wu Quantization"]


def _thumbnail_rgb(image: Image.Image) -> Image.Image:
    img = image.convert("RGB")
    thumb = img.copy()
    thumb.thumbnail((512, 512), Image.Resampling.LANCZOS)
    return thumb

def _palette_from_quantized(q: Image.Image, colors: int) -> list[str]:
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
    return result[:colors]

def _kmeans_palette(image: Image.Image, colors: int) -> list[str]:
    arr = np.asarray(_thumbnail_rgb(image), dtype=np.float32).reshape(-1, 3)
    if len(arr) > 100_000:
        rng = np.random.default_rng(0x524D)  # deterministic "RM"
        arr = arr[rng.choice(len(arr), 100_000, replace=False)]
    unique = np.unique(arr.astype(np.uint8), axis=0).astype(np.float32)
    if len(unique) <= colors:
        return [rgb_to_hex(c) for c in unique]
    # Deterministic farthest-point initialization gives much more stable
    # creative results than picking random centers.
    lum = unique @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    centers = [unique[int(np.argmin(lum))], unique[int(np.argmax(lum))]]
    while len(centers) < colors:
        c = np.asarray(centers, dtype=np.float32)
        d = np.min(np.sum((unique[:, None, :] - c[None, :, :]) ** 2, axis=2), axis=1)
        centers.append(unique[int(np.argmax(d))])
    centers_np = np.asarray(centers[:colors], dtype=np.float32)
    for _ in range(16):
        distances = np.sum((arr[:, None, :] - centers_np[None, :, :]) ** 2, axis=2)
        labels = np.argmin(distances, axis=1)
        updated = centers_np.copy()
        for i in range(colors):
            members = arr[labels == i]
            if len(members):
                updated[i] = np.mean(members, axis=0)
        if np.max(np.abs(updated - centers_np)) < 0.5:
            centers_np = updated
            break
        centers_np = updated
    return [rgb_to_hex(np.rint(c)) for c in centers_np]

def _wu_volume(moment: np.ndarray, box: tuple[int, int, int, int, int, int]) -> float:
    r0, r1, g0, g1, b0, b1 = box
    return float(
        moment[r1, g1, b1] - moment[r1, g1, b0] - moment[r1, g0, b1] + moment[r1, g0, b0]
        - moment[r0, g1, b1] + moment[r0, g1, b0] + moment[r0, g0, b1] - moment[r0, g0, b0]
    )

def _wu_variance(moments: tuple[np.ndarray, ...], box: tuple[int, int, int, int, int, int]) -> float:
    wt, mr, mg, mb, m2 = moments
    weight = _wu_volume(wt, box)
    if weight <= 0.0:
        return 0.0
    r = _wu_volume(mr, box); g = _wu_volume(mg, box); b = _wu_volume(mb, box)
    return max(0.0, _wu_volume(m2, box) - (r * r + g * g + b * b) / weight)

def _wu_best_split(moments: tuple[np.ndarray, ...], box: tuple[int, int, int, int, int, int]):
    r0, r1, g0, g1, b0, b1 = box
    best = None
    best_score = float("inf")
    axes = [(0, r0, r1), (1, g0, g1), (2, b0, b1)]
    for axis, lo, hi in axes:
        for cut in range(lo + 1, hi):
            if axis == 0:
                a = (r0, cut, g0, g1, b0, b1); c = (cut, r1, g0, g1, b0, b1)
            elif axis == 1:
                a = (r0, r1, g0, cut, b0, b1); c = (r0, r1, cut, g1, b0, b1)
            else:
                a = (r0, r1, g0, g1, b0, cut); c = (r0, r1, g0, g1, cut, b1)
            if _wu_volume(moments[0], a) <= 0 or _wu_volume(moments[0], c) <= 0:
                continue
            score = _wu_variance(moments, a) + _wu_variance(moments, c)
            if score < best_score:
                best_score = score
                best = (a, c)
    return best

def _wu_palette(image: Image.Image, colors: int) -> list[str]:
    arr = np.asarray(_thumbnail_rgb(image), dtype=np.uint8).reshape(-1, 3)
    # Wu's classic quantizer uses a 5-bit-per-channel histogram plus a zero
    # boundary plane, hence 33 bins on each axis.
    shape = (33, 33, 33)
    wt = np.zeros(shape, dtype=np.float64)
    mr = np.zeros(shape, dtype=np.float64)
    mg = np.zeros(shape, dtype=np.float64)
    mb = np.zeros(shape, dtype=np.float64)
    m2 = np.zeros(shape, dtype=np.float64)
    r = (arr[:, 0] >> 3).astype(np.intp) + 1
    g = (arr[:, 1] >> 3).astype(np.intp) + 1
    b = (arr[:, 2] >> 3).astype(np.intp) + 1
    np.add.at(wt, (r, g, b), 1.0)
    np.add.at(mr, (r, g, b), arr[:, 0])
    np.add.at(mg, (r, g, b), arr[:, 1])
    np.add.at(mb, (r, g, b), arr[:, 2])
    sq = np.sum(arr.astype(np.float64) ** 2, axis=1)
    np.add.at(m2, (r, g, b), sq)
    moments = tuple(np.cumsum(np.cumsum(np.cumsum(m, axis=0), axis=1), axis=2) for m in (wt, mr, mg, mb, m2))
    boxes: list[tuple[int, int, int, int, int, int]] = [(0, 32, 0, 32, 0, 32)]
    while len(boxes) < colors:
        candidate_index = max(range(len(boxes)), key=lambda i: _wu_variance(moments, boxes[i]))
        split = _wu_best_split(moments, boxes[candidate_index])
        if split is None:
            break
        boxes[candidate_index] = split[0]
        boxes.append(split[1])
    result: list[str] = []
    for box in boxes:
        weight = _wu_volume(moments[0], box)
        if weight <= 0:
            continue
        rgb = [round(_wu_volume(moments[i], box) / weight) for i in (1, 2, 3)]
        value = rgb_to_hex(rgb)
        if value not in result:
            result.append(value)
    return result[:colors]

def extract_palette(image: Image.Image, colors: int = 8, method: str = "Median Cut") -> list[str]:
    colors = max(2, min(256, int(colors)))
    method = str(method or "Median Cut")
    if method == "K-Means":
        result = _kmeans_palette(image, colors)
    elif method == "Octree":
        q = _thumbnail_rgb(image).quantize(colors=colors, method=Image.Quantize.FASTOCTREE)
        result = _palette_from_quantized(q, colors)
    elif method == "Wu Quantization":
        result = _wu_palette(image, colors)
    else:
        q = _thumbnail_rgb(image).quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
        result = _palette_from_quantized(q, colors)
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
