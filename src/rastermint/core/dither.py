# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from array import array
from functools import lru_cache
import json
import math
import numpy as np

from .dither_metadata import ALGORITHM_GROUPS, ALGORITHMS, ERROR_DIFFUSION_KERNELS, Kernel
from .palette import quantize_nearest

def expand_bayer(matrix: np.ndarray) -> np.ndarray:
    return np.block(
        [[4 * matrix + 0, 4 * matrix + 2], [4 * matrix + 3, 4 * matrix + 1]]
    ).astype(np.float32)


BAYER_MATRICES: dict[str, np.ndarray] = {
    "Bayer 2x2": np.array([[0, 2], [3, 1]], dtype=np.float32),
    "Bayer 4x4": np.array(
        [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]],
        dtype=np.float32,
    ),
}
BAYER_MATRICES["Bayer 8x8"] = expand_bayer(BAYER_MATRICES["Bayer 4x4"])
BAYER_MATRICES["Bayer 16x16"] = expand_bayer(BAYER_MATRICES["Bayer 8x8"])
BAYER_MATRICES["Bayer 32x32"] = expand_bayer(BAYER_MATRICES["Bayer 16x16"])


def _clustered_matrix(size: int) -> np.ndarray:
    # Rank pixels by distance to repeated cell centers. The rank matrix creates
    # growing dots rather than the dispersed-dot look of Bayer matrices.
    coords: list[tuple[float, int, int]] = []
    center = (size - 1) / 2.0
    for y in range(size):
        for x in range(size):
            # Slight diagonal bias avoids perfectly circular banding.
            distance = (x - center) ** 2 + (y - center) ** 2 + 0.05 * ((x + y) % 2)
            coords.append((distance, y, x))
    coords.sort()
    matrix = np.zeros((size, size), dtype=np.float32)
    for rank, (_, y, x) in enumerate(coords):
        matrix[y, x] = rank
    return matrix


CLUSTERED_MATRICES = {
    "Clustered Dot 4x4": _clustered_matrix(4),
    "Clustered Dot 8x8": _clustered_matrix(8),
}

# Additional deterministic threshold screens. These are intentionally fixed so
# still images and animation frames do not shimmer simply because the algorithm
# was re-evaluated.
def _structured_pattern_matrix(size: int = 8) -> np.ndarray:
    # Rank every cell exactly once while favouring diagonal/cross-hatch groups.
    # A full 0..N²-1 rank range keeps the tone response balanced.
    coords = []
    for y in range(size):
        for x in range(size):
            coords.append((((x + y) % 4), ((x - y) % size), ((x + 2 * y) % size), y, x))
    coords.sort()
    matrix = np.zeros((size, size), dtype=np.float32)
    for rank, (*_, y, x) in enumerate(coords):
        matrix[y, x] = rank
    return matrix


_random_order = np.arange(64, dtype=np.float32)
np.random.default_rng(0x524D2026).shuffle(_random_order)
PATTERN_MATRICES: dict[str, np.ndarray] = {
    "Random Ordered": _random_order.reshape(8, 8),
    "Bit Tone": np.array(
        [[0, 12, 3, 15], [8, 4, 11, 7], [2, 14, 1, 13], [10, 6, 9, 5]],
        dtype=np.float32,
    ),
    "Pattern": _structured_pattern_matrix(8),
    "Dot Pattern": _clustered_matrix(6),
}

def normalize_custom_matrix(value: object) -> np.ndarray:
    """Validate and rank a user threshold matrix into 0..N²-1 values."""
    payload = value
    if isinstance(value, str):
        try:
            payload = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = None
    try:
        matrix = np.asarray(payload, dtype=np.float32)
    except (TypeError, ValueError):
        matrix = BAYER_MATRICES["Bayer 4x4"].copy()
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or not (2 <= matrix.shape[0] <= 16):
        matrix = BAYER_MATRICES["Bayer 4x4"].copy()
    if not np.all(np.isfinite(matrix)):
        matrix = BAYER_MATRICES["Bayer 4x4"].copy()
    order = np.argsort(matrix, axis=None, kind="stable")
    ranked = np.empty(order.size, dtype=np.float32)
    ranked[order] = np.arange(order.size, dtype=np.float32)
    return ranked.reshape(matrix.shape)


def ordered_dither(image: np.ndarray, palette: np.ndarray, matrix: np.ndarray, strength: float) -> np.ndarray:
    h, w, _ = image.shape
    n = matrix.shape[0]
    normalized = (matrix + 0.5) / (n * n) - 0.5
    tiled = np.tile(normalized, (int(np.ceil(h / n)), int(np.ceil(w / n))))[:h, :w]
    adjusted = np.clip(image + tiled[:, :, None] * (128.0 * strength), 0, 255)
    return quantize_nearest(adjusted, palette)


def random_dither(image: np.ndarray, palette: np.ndarray, strength: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.uniform(-64.0, 64.0, size=image.shape[:2])[:, :, None] * strength
    return quantize_nearest(np.clip(image + noise, 0, 255), palette)


def interleaved_gradient_noise(image: np.ndarray, palette: np.ndarray, strength: float) -> np.ndarray:
    h, w = image.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    # Jorge Jimenez-style interleaved gradient hash, used here only as a
    # deterministic high-frequency threshold source.
    noise = np.mod(52.9829189 * np.mod(0.06711056 * xx + 0.00583715 * yy, 1.0), 1.0) - 0.5
    adjusted = np.clip(image + noise[:, :, None] * 128.0 * strength, 0, 255)
    return quantize_nearest(adjusted, palette)


_BLUE_NOISE_64: np.ndarray | None = None


def _blue_noise_mask() -> np.ndarray:
    global _BLUE_NOISE_64
    if _BLUE_NOISE_64 is None:
        rng = np.random.default_rng(0x524D2026)
        base = rng.random((64, 64), dtype=np.float32)
        # Small high-pass filter: subtract local 8-neighbour mean. Rank the
        # result so the final mask has a uniform threshold distribution.
        local = sum(
            np.roll(np.roll(base, dy, axis=0), dx, axis=1)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if dx or dy
        ) / 8.0
        high = base - local
        order = np.argsort(high, axis=None)
        ranked = np.empty_like(order, dtype=np.float32)
        ranked[order] = np.linspace(0.0, 1.0, order.size, endpoint=False, dtype=np.float32)
        _BLUE_NOISE_64 = ranked.reshape(64, 64) - 0.5
    return _BLUE_NOISE_64


def blue_noise_dither(image: np.ndarray, palette: np.ndarray, strength: float) -> np.ndarray:
    h, w = image.shape[:2]
    mask = _blue_noise_mask()
    tiled = np.tile(mask, (math.ceil(h / 64), math.ceil(w / 64)))[:h, :w]
    adjusted = np.clip(image + tiled[:, :, None] * 128.0 * strength, 0, 255)
    return quantize_nearest(adjusted, palette)


def modulation_dither(image: np.ndarray, palette: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Palette-aware sinusoidal screen with luminance-modulated phase.

    The carrier remains position-stable (useful for animation) while the image
    luminance changes the local phase/weight, producing the flowing stripe
    texture associated with modulation-style halftoning.
    """
    h, w = image.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    luminance = (0.2126 * image[..., 0] + 0.7152 * image[..., 1] + 0.0722 * image[..., 2]) / 255.0
    phase = (xx * (2.0 * np.pi / 7.0)) + (yy * (2.0 * np.pi / 19.0)) + luminance * np.pi * 1.5
    carrier = np.sin(phase) * (0.55 + 0.45 * np.cos(yy * (2.0 * np.pi / 13.0)))
    adjusted = np.clip(image + carrier[..., None] * (72.0 * max(0.0, float(strength))), 0, 255)
    return quantize_nearest(adjusted, palette)


def threshold_dither(image: np.ndarray, palette: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    lum_palette = 0.2126 * palette[:, 0] + 0.7152 * palette[:, 1] + 0.0722 * palette[:, 2]
    dark = palette[int(np.argmin(lum_palette))]
    light = palette[int(np.argmax(lum_palette))]
    lum = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]
    mask = lum >= (255.0 * max(0.0, min(1.0, threshold)))
    return np.where(mask[:, :, None], light, dark).astype(np.float32)


def halftone_dither(image: np.ndarray, palette: np.ndarray, cell: int = 8) -> np.ndarray:
    lum_palette = 0.2126 * palette[:, 0] + 0.7152 * palette[:, 1] + 0.0722 * palette[:, 2]
    dark = palette[int(np.argmin(lum_palette))]
    light = palette[int(np.argmax(lum_palette))]
    lum = (0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]) / 255.0
    h, w = lum.shape
    out = np.empty_like(image, dtype=np.float32)
    for y0 in range(0, h, cell):
        for x0 in range(0, w, cell):
            block = lum[y0:min(h, y0 + cell), x0:min(w, x0 + cell)]
            average = float(block.mean())
            darkness = 1.0 - average
            radius = math.sqrt(max(0.0, darkness)) * (cell * 0.70)
            cy = y0 + (block.shape[0] - 1) / 2.0
            cx = x0 + (block.shape[1] - 1) / 2.0
            for y in range(y0, min(h, y0 + cell)):
                for x in range(x0, min(w, x0 + cell)):
                    is_dot = (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius
                    out[y, x] = dark if is_dot else light
    return out



def pop_tone_dither(
    image: np.ndarray,
    palette: np.ndarray,
    scale: int = 8,
    density: float = 0.7,
    variation: float = 0.25,
) -> np.ndarray:
    """Manga/pop-art clustered tone with palette-aware colour retention."""
    h, w = image.shape[:2]
    cell = max(2, min(64, int(scale)))
    density = max(0.0, min(1.0, float(density)))
    variation = max(0.0, min(1.0, float(variation)))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = np.mod(xx + cell * 0.5, cell) / cell - 0.5
    v = np.mod(yy + cell * 0.5, cell) / cell - 0.5
    rank = np.clip(np.pi * (u * u + v * v), 0.0, 1.0)
    lum = (0.2126 * image[..., 0] + 0.7152 * image[..., 1] + 0.0722 * image[..., 2]) / 255.0
    wave = 0.5 + 0.5 * np.sin((xx + yy * 0.63) * (2.0 * np.pi / max(3.0, cell * 2.5)))
    coverage = np.clip((1.0 - lum) * density * 1.25 + (wave - 0.5) * variation * 0.28, 0.0, 1.0)
    # Dots retain local source hue while the paper between dots is pushed
    # toward the brightest palette swatch. This is visibly different from the
    # ordinary two-colour Halftone dither.
    quantized = quantize_nearest(image, palette)
    pl = 0.2126 * palette[:, 0] + 0.7152 * palette[:, 1] + 0.0722 * palette[:, 2]
    paper = palette[int(np.argmax(pl))]
    return np.where((coverage >= rank)[..., None], quantized, paper).astype(np.float32)


def _sample_palette_color(block: np.ndarray, palette: np.ndarray) -> np.ndarray:
    if block.size == 0:
        return palette[0]
    mean = block.reshape(-1, 3).mean(axis=0)
    diff = palette - mean[None, :]
    return palette[int(np.argmin(np.sum(diff * diff, axis=1)))]


def polygon_dither(
    image: np.ndarray,
    palette: np.ndarray,
    variant: str = "Hexa-Poly",
    cell_size: int = 12,
) -> np.ndarray:
    """Rebuild the image from actual polygonal cells rather than an overlay."""
    from PIL import Image as _Image, ImageDraw as _ImageDraw

    arr = np.asarray(image, dtype=np.float32)
    h, w = arr.shape[:2]
    cell = max(3, min(128, int(cell_size)))
    canvas = _Image.new("RGB", (w, h), tuple(int(x) for x in palette[0]))
    draw = _ImageDraw.Draw(canvas)

    def colour_at(cx: float, cy: float, radius: float) -> tuple[int, int, int]:
        x0 = max(0, int(cx - radius)); x1 = min(w, int(cx + radius) + 1)
        y0 = max(0, int(cy - radius)); y1 = min(h, int(cy + radius) + 1)
        c = _sample_palette_color(arr[y0:y1, x0:x1], palette)
        return tuple(int(round(float(v))) for v in c)

    if variant == "Tri-Poly":
        for y in range(0, h + cell, cell):
            for x in range(0, w + cell, cell):
                c1 = colour_at(x + cell / 3, y + cell / 3, cell * 0.55)
                c2 = colour_at(x + cell * 2 / 3, y + cell * 2 / 3, cell * 0.55)
                draw.polygon([(x, y), (x + cell, y), (x, y + cell)], fill=c1)
                draw.polygon([(x + cell, y), (x + cell, y + cell), (x, y + cell)], fill=c2)
    elif variant == "Penta-Poly":
        radius = cell * 0.58
        step_x = cell * 1.12
        step_y = cell * 0.95
        row = 0
        cy = 0.0
        while cy < h + cell:
            offset = (row & 1) * step_x * 0.5
            cx = -cell + offset
            while cx < w + cell:
                pts = []
                for i in range(5):
                    a = -math.pi / 2 + i * 2 * math.pi / 5
                    pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
                draw.polygon(pts, fill=colour_at(cx, cy, radius))
                cx += step_x
            cy += step_y
            row += 1
    elif variant == "Low-Poly":
        # Deterministic jittered triangular mesh: actual flat polygon regions,
        # not a pixelation followed by polygon outlines.
        rng = np.random.default_rng(0x4C4F5750 + cell)
        rows = int(math.ceil(h / cell)) + 2
        cols = int(math.ceil(w / cell)) + 2
        points = np.zeros((rows, cols, 2), dtype=np.float32)
        for gy in range(rows):
            for gx in range(cols):
                px = (gx - 1) * cell
                py = (gy - 1) * cell
                if 0 < gx < cols - 1: px += rng.uniform(-0.28, 0.28) * cell
                if 0 < gy < rows - 1: py += rng.uniform(-0.28, 0.28) * cell
                points[gy, gx] = (px, py)
        for gy in range(rows - 1):
            for gx in range(cols - 1):
                a, b = points[gy, gx], points[gy, gx + 1]
                c, d = points[gy + 1, gx], points[gy + 1, gx + 1]
                tris = ((a, b, d), (a, d, c)) if ((gx + gy) & 1) == 0 else ((a, b, c), (b, d, c))
                for tri in tris:
                    cx = float(sum(p[0] for p in tri) / 3.0); cy = float(sum(p[1] for p in tri) / 3.0)
                    draw.polygon([(float(p[0]), float(p[1])) for p in tri], fill=colour_at(cx, cy, cell * 0.6))
    else:  # Hexa-Poly
        radius = cell * 0.58
        step_x = radius * 1.5
        step_y = math.sqrt(3.0) * radius
        col = 0
        cx = 0.0
        while cx < w + cell:
            offset_y = (col & 1) * step_y * 0.5
            cy = -cell + offset_y
            while cy < h + cell:
                pts = [(cx + radius * math.cos(i * math.pi / 3), cy + radius * math.sin(i * math.pi / 3)) for i in range(6)]
                draw.polygon(pts, fill=colour_at(cx, cy, radius))
                cy += step_y
            cx += step_x
            col += 1
    return np.asarray(canvas, dtype=np.float32)


def beehive_dither(
    image: np.ndarray,
    palette: np.ndarray,
    scale: int = 10,
    luminance_threshold: float = 0.5,
    cell_size: int = 10,
) -> np.ndarray:
    """Honeycomb raster whose hexagonal cells are the rendered image geometry."""
    from PIL import Image as _Image, ImageDraw as _ImageDraw

    arr = np.asarray(image, dtype=np.float32)
    h, w = arr.shape[:2]
    radius = max(2.0, min(96.0, float(cell_size) * max(0.25, float(scale) / 10.0) * 0.58))
    step_x = radius * 1.5
    step_y = math.sqrt(3.0) * radius
    threshold = max(0.0, min(1.0, float(luminance_threshold)))
    pl = 0.2126 * palette[:, 0] + 0.7152 * palette[:, 1] + 0.0722 * palette[:, 2]
    dark = palette[int(np.argmin(pl))]
    canvas = _Image.new("RGB", (w, h), tuple(int(v) for v in palette[int(np.argmax(pl))]))
    draw = _ImageDraw.Draw(canvas)
    col = 0
    cx = 0.0
    while cx < w + radius:
        cy = -radius + (col & 1) * step_y * 0.5
        while cy < h + radius:
            x0=max(0,int(cx-radius)); x1=min(w,int(cx+radius)+1)
            y0=max(0,int(cy-radius)); y1=min(h,int(cy+radius)+1)
            block=arr[y0:y1,x0:x1]
            if block.size:
                mean=block.reshape(-1,3).mean(axis=0)
                lum=float(0.2126*mean[0]+0.7152*mean[1]+0.0722*mean[2])/255.0
                if lum < threshold:
                    color=dark
                else:
                    color=_sample_palette_color(block,palette)
                pts=[(cx+radius*math.cos(i*math.pi/3),cy+radius*math.sin(i*math.pi/3)) for i in range(6)]
                draw.polygon(pts, fill=tuple(int(round(float(v))) for v in color))
            cy += step_y
        cx += step_x
        col += 1
    return np.asarray(canvas, dtype=np.float32)


def error_diffusion(
    image: np.ndarray,
    palette: np.ndarray,
    kernel: Kernel,
    divisor: float,
    strength: float = 1.0,
    serpentine: bool = True,
) -> np.ndarray:
    h, w, _ = image.shape
    if h == 0 or w == 0:
        return image.astype(np.float32, copy=True)

    palette_values = tuple(tuple(float(channel) for channel in color) for color in np.asarray(palette, dtype=np.float32))
    if not palette_values:
        raise ValueError("Palette must contain at least one color")

    normalized_kernel = tuple((dx, dy, float(weight) / divisor) for dx, dy, weight in kernel)
    data = array("f", np.asarray(image, dtype=np.float32).reshape(-1))

    for y in range(h):
        reverse = bool(serpentine and (y & 1))
        xs = range(w - 1, -1, -1) if reverse else range(w)
        direction = -1 if reverse else 1

        for x in xs:
            base = (y * w + x) * 3
            p0, p1, p2 = data[base], data[base + 1], data[base + 2]
            old0 = 0.0 if p0 < 0.0 else 255.0 if p0 > 255.0 else p0
            old1 = 0.0 if p1 < 0.0 else 255.0 if p1 > 255.0 else p1
            old2 = 0.0 if p2 < 0.0 else 255.0 if p2 > 255.0 else p2

            best_index = 0
            best_distance = float("inf")
            for index, (red, green, blue) in enumerate(palette_values):
                dr, dg, db = red - old0, green - old1, blue - old2
                distance = dr * dr + dg * dg + db * db
                if distance < best_distance:
                    best_distance = distance
                    best_index = index

            new0, new1, new2 = palette_values[best_index]
            data[base], data[base + 1], data[base + 2] = new0, new1, new2
            error0 = (old0 - new0) * strength
            error1 = (old1 - new1) * strength
            error2 = (old2 - new2) * strength

            for dx, dy, factor in normalized_kernel:
                nx, ny = x + dx * direction, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    target = (ny * w + nx) * 3
                    data[target] += error0 * factor
                    data[target + 1] += error1 * factor
                    data[target + 2] += error2 * factor

    return np.frombuffer(data, dtype=np.float32).reshape(h, w, 3).copy()


def _palette_tuples(palette: np.ndarray) -> tuple[tuple[float, float, float], ...]:
    return tuple(tuple(float(channel) for channel in color) for color in np.asarray(palette, dtype=np.float32))


def _nearest_color_index_rgb(r: float, g: float, b: float, palette_values: tuple[tuple[float, float, float], ...]) -> int:
    best_index = 0
    best_distance = float("inf")
    for index, (pr, pg, pb) in enumerate(palette_values):
        dr, dg, db = pr - r, pg - g, pb - b
        distance = dr * dr + dg * dg + db * db
        if distance < best_distance:
            best_distance = distance
            best_index = index
    return best_index

_COLOUR_MIX_MAX_PAIR_BASE_COLORS = 48


def _srgb8_to_oklab(values: np.ndarray) -> np.ndarray:
    """Vectorised sRGB (0..255) to OKLab conversion."""
    rgb = np.clip(np.asarray(values, dtype=np.float32), 0.0, 255.0) / 255.0
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    r, g, b = linear[..., 0], linear[..., 1], linear[..., 2]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack((
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    ), axis=-1).astype(np.float32)


def _representative_palette_indices(values: np.ndarray, limit: int) -> np.ndarray:
    """Deterministic farthest-point sampling for very large palettes.

    Full pair enumeration is exact through 48 colours. Above that, all direct
    palette colours remain available, while mixed pairs use a representative
    48-colour subset. This bounds preview/export work for 128/256-colour
    palettes without ever emitting a colour outside the active palette.
    """
    count = len(values)
    if count <= limit:
        return np.arange(count, dtype=np.int32)

    # Start near the dark/low-magnitude corner, then repeatedly take the colour
    # furthest from the selected set. This spreads representatives across gamut.
    selected = [int(np.argmin(np.sum(values * values, axis=1)))]
    min_dist = np.full(count, np.inf, dtype=np.float32)
    while len(selected) < limit:
        latest = values[selected[-1]]
        dist = np.sum((values - latest) ** 2, axis=1)
        min_dist = np.minimum(min_dist, dist)
        min_dist[selected] = -1.0
        selected.append(int(np.argmax(min_dist)))
    return np.asarray(selected, dtype=np.int32)


@lru_cache(maxsize=24)
def _colour_mix_pair_model(
    palette_key: tuple[tuple[int, int, int], ...],
    distance_mode: str,
) -> tuple[np.ndarray, np.ndarray]:
    palette = np.asarray(palette_key, dtype=np.float32)
    mode = str(distance_mode or "OKLab").strip().upper().replace(" ", "")
    match_palette = _srgb8_to_oklab(palette) if mode == "OKLAB" else palette

    representatives = _representative_palette_indices(match_palette, _COLOUR_MIX_MAX_PAIR_BASE_COLORS)
    pairs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()

    # Every same-colour pair is included, so exact active-palette colours can
    # always survive unchanged even when a large palette is sampled for mixes.
    for index in range(len(palette)):
        pair = (index, index)
        pairs.append(pair)
        seen.add(pair)

    reps = [int(index) for index in representatives]
    for offset, first in enumerate(reps):
        for second in reps[offset:]:
            pair = (first, second) if first <= second else (second, first)
            if pair not in seen:
                pairs.append(pair)
                seen.add(pair)

    pair_indices = np.asarray(pairs, dtype=np.int32)
    pair_match_values = (
        match_palette[pair_indices[:, 0]] + match_palette[pair_indices[:, 1]]
    ) * 0.5
    return pair_indices, pair_match_values.astype(np.float32)


def _colour_mix_pattern_mask(height: int, width: int, pattern: str, phase: int) -> np.ndarray:
    yy, xx = np.mgrid[0:height, 0:width]
    phase = int(phase) & 1
    pattern = str(pattern or "Checker")
    if pattern == "Horizontal":
        mask = ((yy + phase) & 1) == 0
    elif pattern == "Vertical":
        mask = ((xx + phase) & 1) == 0
    elif pattern == "Bayer 2x2":
        matrix = np.array([[0, 2], [3, 1]], dtype=np.int8)
        tiled = np.tile(matrix, (math.ceil(height / 2), math.ceil(width / 2)))[:height, :width]
        mask = tiled < 2
        if phase:
            mask = ~mask
    else:
        mask = ((xx + yy + phase) & 1) == 0
    return mask


def colour_mix_dither(
    image: np.ndarray,
    palette: np.ndarray,
    pattern: str = "Checker",
    distance: str = "OKLab",
    phase: int = 0,
) -> np.ndarray:
    """Approximate source colours with a strict 50/50 pair of palette colours.

    Each pixel chooses the palette-colour pair whose midpoint is nearest to the
    source colour, then a deterministic 1:1 spatial pattern chooses which member
    of that pair is emitted at that coordinate. The output therefore contains
    only active-palette colours while creating perceived intermediate colours.
    """
    source = np.asarray(image, dtype=np.float32)
    palette_np = np.asarray(palette, dtype=np.float32)
    if palette_np.ndim != 2 or palette_np.shape[0] == 0 or palette_np.shape[1] != 3:
        raise ValueError("Palette must contain at least one RGB color")
    if source.size == 0:
        return source.copy()

    palette_key = tuple(tuple(int(round(float(channel))) for channel in color) for color in palette_np)
    mode = str(distance or "OKLab").strip().upper().replace(" ", "")
    pair_indices, pair_match_values = _colour_mix_pair_model(palette_key, mode)
    match_source = _srgb8_to_oklab(source) if mode == "OKLAB" else source

    pixels = match_source.reshape(-1, 3)
    pair_sq = np.sum(pair_match_values * pair_match_values, axis=1)
    chosen_pair = np.empty(len(pixels), dtype=np.int32)

    # Keep the temporary distance matrix around ~16 MiB regardless of palette
    # size. This avoids the huge pixel×pair allocation that a naive version
    # would create for 64/128/256-colour palettes.
    pair_count = max(1, len(pair_match_values))
    chunk_pixels = max(512, min(16384, 4_000_000 // pair_count))
    for start in range(0, len(pixels), chunk_pixels):
        end = min(len(pixels), start + chunk_pixels)
        chunk = pixels[start:end]
        chunk_sq = np.sum(chunk * chunk, axis=1, keepdims=True)
        distances = chunk_sq + pair_sq[None, :] - 2.0 * (chunk @ pair_match_values.T)
        chosen_pair[start:end] = np.argmin(distances, axis=1)

    chosen = pair_indices[chosen_pair]
    first = palette_np[chosen[:, 0]].reshape(source.shape)
    second = palette_np[chosen[:, 1]].reshape(source.shape)
    mask = _colour_mix_pattern_mask(source.shape[0], source.shape[1], pattern, phase)
    return np.where(mask[:, :, None], first, second).astype(np.float32)



def dot_diffusion(image: np.ndarray, palette: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Class-ordered dot diffusion using an 8x8 Bayer class matrix."""
    work = np.asarray(image, dtype=np.float32).copy()
    h, w, _ = work.shape
    classes = BAYER_MATRICES["Bayer 8x8"].astype(np.int32)
    out = np.zeros_like(work)
    palette_values = _palette_tuples(palette)
    neighbour_offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    for cls in range(64):
        for y in range(h):
            for x in range(w):
                if int(classes[y % 8, x % 8]) != cls:
                    continue
                old = np.clip(work[y, x], 0, 255)
                idx = _nearest_color_index_rgb(float(old[0]), float(old[1]), float(old[2]), palette_values)
                new = palette[idx]
                out[y, x] = new
                error = (old - new) * strength
                candidates: list[tuple[int, int]] = []
                for dx, dy in neighbour_offsets:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and int(classes[ny % 8, nx % 8]) > cls:
                        candidates.append((nx, ny))
                if candidates:
                    share = error / len(candidates)
                    for nx, ny in candidates:
                        work[ny, nx] += share
    return out


def _hilbert_d2xy(n: int, d: int) -> tuple[int, int]:
    x = y = 0
    t = d
    s = 1
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return x, y


def riemersma_dither(image: np.ndarray, palette: np.ndarray, strength: float = 1.0) -> np.ndarray:
    h, w, _ = image.shape
    n = 1
    while n < max(w, h):
        n <<= 1
    out = np.asarray(image, dtype=np.float32).copy()
    errors = [np.zeros(3, dtype=np.float32) for _ in range(16)]
    palette_values = _palette_tuples(palette)
    weights = np.array([0.5 ** (i + 1) for i in range(16)], dtype=np.float32)
    weights /= weights.sum()

    for d in range(n * n):
        x, y = _hilbert_d2xy(n, d)
        if x >= w or y >= h:
            continue
        carried = np.zeros(3, dtype=np.float32)
        for err, weight in zip(errors, weights, strict=False):
            carried += err * weight
        old = np.clip(out[y, x] + carried * strength, 0, 255)
        idx = _nearest_color_index_rgb(float(old[0]), float(old[1]), float(old[2]), palette_values)
        new = palette[idx]
        out[y, x] = new
        errors = [old - new, *errors[:-1]]
    return out


def apply_dither(
    image: np.ndarray,
    palette: np.ndarray,
    algorithm: str,
    strength: float = 1.0,
    serpentine: bool = True,
    threshold: float = 0.5,
    color_mix_pattern: str = "Checker",
    color_mix_distance: str = "OKLab",
    color_mix_phase: int = 0,
    custom_matrix: object | None = None,
) -> np.ndarray:
    if algorithm == "Nearest Palette":
        return quantize_nearest(image, palette)
    if algorithm == "Threshold":
        return threshold_dither(image, palette, threshold)
    if algorithm == "Random":
        return random_dither(image, palette, strength)
    if algorithm == "Interleaved Gradient Noise":
        return interleaved_gradient_noise(image, palette, strength)
    if algorithm == "Blue Noise":
        return blue_noise_dither(image, palette, strength)
    if algorithm == "1:1 Colour Mix":
        return colour_mix_dither(
            image, palette, pattern=color_mix_pattern,
            distance=color_mix_distance, phase=color_mix_phase,
        )
    if algorithm in BAYER_MATRICES:
        return ordered_dither(image, palette, BAYER_MATRICES[algorithm], strength)
    if algorithm in CLUSTERED_MATRICES:
        return ordered_dither(image, palette, CLUSTERED_MATRICES[algorithm], strength)
    if algorithm in PATTERN_MATRICES:
        return ordered_dither(image, palette, PATTERN_MATRICES[algorithm], strength)
    if algorithm == "Custom Matrix":
        return ordered_dither(image, palette, normalize_custom_matrix(custom_matrix), strength)
    if algorithm == "Modulation":
        return modulation_dither(image, palette, strength)
    if algorithm == "Halftone":
        return halftone_dither(image, palette)
    if algorithm in ERROR_DIFFUSION_KERNELS:
        kernel, divisor = ERROR_DIFFUSION_KERNELS[algorithm]
        return error_diffusion(image, palette, kernel, divisor, strength, serpentine)
    if algorithm == "Dot Diffusion":
        return dot_diffusion(image, palette, strength)
    if algorithm == "Riemersma":
        return riemersma_dither(image, palette, strength)
    raise ValueError(f"Unknown dithering algorithm: {algorithm}")
