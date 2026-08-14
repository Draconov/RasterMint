# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .palette import nearest_palette_index, quantize_nearest

Kernel = list[tuple[int, int, float]]


ERROR_DIFFUSION_KERNELS: dict[str, tuple[Kernel, float]] = {
    "Floyd-Steinberg": (
        [(1, 0, 7), (-1, 1, 3), (0, 1, 5), (1, 1, 1)],
        16,
    ),
    "False Floyd-Steinberg": (
        [(1, 0, 3), (-1, 1, 2), (0, 1, 3)],
        8,
    ),
    "Jarvis-Judice-Ninke": (
        [
            (1, 0, 7), (2, 0, 5),
            (-2, 1, 3), (-1, 1, 5), (0, 1, 7), (1, 1, 5), (2, 1, 3),
            (-2, 2, 1), (-1, 2, 3), (0, 2, 5), (1, 2, 3), (2, 2, 1),
        ],
        48,
    ),
    "Stucki": (
        [
            (1, 0, 8), (2, 0, 4),
            (-2, 1, 2), (-1, 1, 4), (0, 1, 8), (1, 1, 4), (2, 1, 2),
            (-2, 2, 1), (-1, 2, 2), (0, 2, 4), (1, 2, 2), (2, 2, 1),
        ],
        42,
    ),
    "Atkinson": (
        [(1, 0, 1), (2, 0, 1), (-1, 1, 1), (0, 1, 1), (1, 1, 1), (0, 2, 1)],
        8,
    ),
    "Burkes": (
        [(1, 0, 8), (2, 0, 4), (-2, 1, 2), (-1, 1, 4), (0, 1, 8), (1, 1, 4), (2, 1, 2)],
        32,
    ),
    "Sierra": (
        [
            (1, 0, 5), (2, 0, 3),
            (-2, 1, 2), (-1, 1, 4), (0, 1, 5), (1, 1, 4), (2, 1, 2),
            (-1, 2, 2), (0, 2, 3), (1, 2, 2),
        ],
        32,
    ),
    "Sierra Two-Row": (
        [(1, 0, 4), (2, 0, 3), (-2, 1, 1), (-1, 1, 2), (0, 1, 3), (1, 1, 2), (2, 1, 1)],
        16,
    ),
    "Sierra Lite": (
        [(1, 0, 2), (-1, 1, 1), (0, 1, 1)],
        4,
    ),
    "Stevenson-Arce": (
        [
            (2, 0, 32),
            (-3, 1, 12), (-1, 1, 26), (1, 1, 30), (3, 1, 16),
            (-2, 2, 12), (0, 2, 26), (2, 2, 12),
            (-3, 3, 5), (-1, 3, 12), (1, 3, 12), (3, 3, 5),
        ],
        200,
    ),
}


BAYER_MATRICES: dict[str, np.ndarray] = {
    "Bayer 2x2": np.array([[0, 2], [3, 1]], dtype=np.float32),
    "Bayer 4x4": np.array(
        [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]],
        dtype=np.float32,
    ),
}


def _make_bayer_8() -> np.ndarray:
    base = BAYER_MATRICES["Bayer 4x4"]
    return np.block([[4 * base + 0, 4 * base + 2], [4 * base + 3, 4 * base + 1]]).astype(np.float32)


BAYER_MATRICES["Bayer 8x8"] = _make_bayer_8()

ALGORITHMS = [
    "Nearest Palette",
    "Threshold",
    "Random",
    "Bayer 2x2",
    "Bayer 4x4",
    "Bayer 8x8",
    *ERROR_DIFFUSION_KERNELS.keys(),
]


def ordered_dither(image: np.ndarray, palette: np.ndarray, matrix: np.ndarray, strength: float) -> np.ndarray:
    h, w, _ = image.shape
    n = matrix.shape[0]
    normalized = (matrix + 0.5) / (n * n) - 0.5
    tiled = np.tile(normalized, (int(np.ceil(h / n)), int(np.ceil(w / n))))[:h, :w]
    # Perturb all channels together; this preserves hue better than independent channel thresholds.
    adjusted = np.clip(image + tiled[:, :, None] * (128.0 * strength), 0, 255)
    return quantize_nearest(adjusted, palette)


def random_dither(image: np.ndarray, palette: np.ndarray, strength: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.uniform(-64.0, 64.0, size=image.shape[:2])[:, :, None] * strength
    return quantize_nearest(np.clip(image + noise, 0, 255), palette)


def threshold_dither(image: np.ndarray, palette: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    # Intentionally binary: select darkest/lightest colors in the current palette.
    lum_palette = 0.2126 * palette[:, 0] + 0.7152 * palette[:, 1] + 0.0722 * palette[:, 2]
    dark = palette[int(np.argmin(lum_palette))]
    light = palette[int(np.argmax(lum_palette))]
    lum = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]
    mask = lum >= (255.0 * threshold)
    return np.where(mask[:, :, None], light, dark).astype(np.float32)


def error_diffusion(
    image: np.ndarray,
    palette: np.ndarray,
    kernel: Kernel,
    divisor: float,
    strength: float = 1.0,
    serpentine: bool = True,
) -> np.ndarray:
    work = image.astype(np.float32, copy=True)
    h, w, _ = work.shape

    for y in range(h):
        reverse = serpentine and (y % 2 == 1)
        xs = range(w - 1, -1, -1) if reverse else range(w)
        direction = -1 if reverse else 1

        for x in xs:
            old = np.clip(work[y, x], 0, 255)
            idx = nearest_palette_index(old, palette)
            new = palette[idx]
            work[y, x] = new
            error = (old - new) * strength

            for dx, dy, weight in kernel:
                nx = x + dx * direction
                ny = y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    work[ny, nx] += error * (weight / divisor)

    return np.clip(work, 0, 255)


def apply_dither(
    image: np.ndarray,
    palette: np.ndarray,
    algorithm: str,
    strength: float = 1.0,
    serpentine: bool = True,
) -> np.ndarray:
    if algorithm == "Nearest Palette":
        return quantize_nearest(image, palette)
    if algorithm == "Threshold":
        return threshold_dither(image, palette)
    if algorithm == "Random":
        return random_dither(image, palette, strength)
    if algorithm in BAYER_MATRICES:
        return ordered_dither(image, palette, BAYER_MATRICES[algorithm], strength)
    if algorithm in ERROR_DIFFUSION_KERNELS:
        kernel, divisor = ERROR_DIFFUSION_KERNELS[algorithm]
        return error_diffusion(image, palette, kernel, divisor, strength, serpentine)
    raise ValueError(f"Unknown dithering algorithm: {algorithm}")
