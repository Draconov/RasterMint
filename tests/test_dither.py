# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import numpy as np

from rastermint.core.dither import ALGORITHMS, apply_dither
from rastermint.core.palette import palette_array


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
