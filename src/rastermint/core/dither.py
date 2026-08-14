# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from array import array
import math
import numpy as np

from .palette import quantize_nearest

Kernel = list[tuple[int, int, float]]

ERROR_DIFFUSION_KERNELS: dict[str, tuple[Kernel, float]] = {
    "Floyd-Steinberg": ([(1, 0, 7), (-1, 1, 3), (0, 1, 5), (1, 1, 1)], 16),
    "False Floyd-Steinberg": ([(1, 0, 3), (-1, 1, 2), (0, 1, 3)], 8),
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
    "Atkinson": ([(1, 0, 1), (2, 0, 1), (-1, 1, 1), (0, 1, 1), (1, 1, 1), (0, 2, 1)], 8),
    "Burkes": ([(1, 0, 8), (2, 0, 4), (-2, 1, 2), (-1, 1, 4), (0, 1, 8), (1, 1, 4), (2, 1, 2)], 32),
    "Sierra": (
        [
            (1, 0, 5), (2, 0, 3),
            (-2, 1, 2), (-1, 1, 4), (0, 1, 5), (1, 1, 4), (2, 1, 2),
            (-1, 2, 2), (0, 2, 3), (1, 2, 2),
        ],
        32,
    ),
    "Sierra Two-Row": ([(1, 0, 4), (2, 0, 3), (-2, 1, 1), (-1, 1, 2), (0, 1, 3), (1, 1, 2), (2, 1, 1)], 16),
    "Sierra Lite": ([(1, 0, 2), (-1, 1, 1), (0, 1, 1)], 4),
    "Stevenson-Arce": (
        [
            (2, 0, 32),
            (-3, 1, 12), (-1, 1, 26), (1, 1, 30), (3, 1, 16),
            (-2, 2, 12), (0, 2, 26), (2, 2, 12),
            (-3, 3, 5), (-1, 3, 12), (1, 3, 12), (3, 3, 5),
        ],
        200,
    ),
    "Shiau-Fan": ([(1, 0, 4), (-1, 1, 1), (0, 1, 1), (1, 1, 2)], 8),
}


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

ALGORITHM_GROUPS: dict[str, list[str]] = {
    "Quantization": ["Nearest Palette", "Threshold", "Random", "Interleaved Gradient Noise", "Blue Noise"],
    "Ordered": [*BAYER_MATRICES.keys(), *CLUSTERED_MATRICES.keys(), "Halftone"],
    "Error Diffusion": [*ERROR_DIFFUSION_KERNELS.keys()],
    "Advanced": ["Dot Diffusion", "Riemersma"],
}
ALGORITHMS = [name for group in ALGORITHM_GROUPS.values() for name in group]


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
    if algorithm in BAYER_MATRICES:
        return ordered_dither(image, palette, BAYER_MATRICES[algorithm], strength)
    if algorithm in CLUSTERED_MATRICES:
        return ordered_dither(image, palette, CLUSTERED_MATRICES[algorithm], strength)
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
