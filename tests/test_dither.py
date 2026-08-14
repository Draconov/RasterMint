# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import numpy as np

from rastermint.core.dither import ALGORITHMS, ERROR_DIFFUSION_KERNELS, apply_dither, error_diffusion
from rastermint.core.palette import nearest_palette_index, palette_array


def make_gradient() -> np.ndarray:
    x = np.linspace(0, 255, 12, dtype=np.float32)
    row = np.stack([x, np.roll(x, 3), np.roll(x, 6)], axis=1)
    return np.tile(row[None, :, :], (10, 1, 1))


def test_all_algorithms_only_emit_palette_colors():
    image = make_gradient()
    palette = palette_array(["#000000", "#FF0000", "#FFFFFF"])
    palette_set = {tuple(map(int, c)) for c in palette}

    for algorithm in ALGORITHMS:
        out = apply_dither(image, palette, algorithm, strength=1.0, serpentine=True)
        assert out.shape == image.shape
        emitted = {tuple(map(int, c)) for c in out.reshape(-1, 3)}
        assert emitted <= palette_set, algorithm


def test_dither_is_deterministic_including_random_mode():
    image = make_gradient()
    palette = palette_array(["#000000", "#FFFFFF"])
    for algorithm in ALGORITHMS:
        a = apply_dither(image, palette, algorithm)
        b = apply_dither(image, palette, algorithm)
        assert np.array_equal(a, b), algorithm


def _reference_error_diffusion(image, palette, kernel, divisor, strength=1.0, serpentine=True):
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


def test_optimized_error_diffusion_matches_reference():
    image = np.random.default_rng(44).uniform(0, 255, (8, 11, 3)).astype(np.float32)
    palette = palette_array(["#101217", "#4A4F59", "#A9AFB9", "#F4F6F8"])
    for name, (kernel, divisor) in ERROR_DIFFUSION_KERNELS.items():
        for serpentine in (False, True):
            expected = _reference_error_diffusion(image, palette, kernel, divisor, 0.85, serpentine)
            actual = error_diffusion(image, palette, kernel, divisor, 0.85, serpentine)
            assert np.array_equal(actual, expected), (name, serpentine)
