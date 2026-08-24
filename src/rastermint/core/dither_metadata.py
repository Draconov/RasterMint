# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

Kernel = list[tuple[int, int, float]]

ERROR_DIFFUSION_KERNELS: dict[str, tuple[Kernel, float]] = {
    "Floyd-Steinberg": ([(1, 0, 7), (-1, 1, 3), (0, 1, 5), (1, 1, 1)], 16),
    "False Floyd-Steinberg": ([(1, 0, 3), (-1, 1, 2), (0, 1, 3)], 8),
    "Jarvis-Judice-Ninke": ([(1, 0, 7), (2, 0, 5), (-2, 1, 3), (-1, 1, 5), (0, 1, 7), (1, 1, 5), (2, 1, 3), (-2, 2, 1), (-1, 2, 3), (0, 2, 5), (1, 2, 3), (2, 2, 1)], 48),
    "Stucki": ([(1, 0, 8), (2, 0, 4), (-2, 1, 2), (-1, 1, 4), (0, 1, 8), (1, 1, 4), (2, 1, 2), (-2, 2, 1), (-1, 2, 2), (0, 2, 4), (1, 2, 2), (2, 2, 1)], 42),
    "Atkinson": ([(1, 0, 1), (2, 0, 1), (-1, 1, 1), (0, 1, 1), (1, 1, 1), (0, 2, 1)], 8),
    "Burkes": ([(1, 0, 8), (2, 0, 4), (-2, 1, 2), (-1, 1, 4), (0, 1, 8), (1, 1, 4), (2, 1, 2)], 32),
    "Sierra": ([(1, 0, 5), (2, 0, 3), (-2, 1, 2), (-1, 1, 4), (0, 1, 5), (1, 1, 4), (2, 1, 2), (-1, 2, 2), (0, 2, 3), (1, 2, 2)], 32),
    "Sierra Two-Row": ([(1, 0, 4), (2, 0, 3), (-2, 1, 1), (-1, 1, 2), (0, 1, 3), (1, 1, 2), (2, 1, 1)], 16),
    "Sierra Lite": ([(1, 0, 2), (-1, 1, 1), (0, 1, 1)], 4),
    "Stevenson-Arce": ([(2, 0, 32), (-3, 1, 12), (-1, 1, 26), (1, 1, 30), (3, 1, 16), (-2, 2, 12), (0, 2, 26), (2, 2, 12), (-3, 3, 5), (-1, 3, 12), (1, 3, 12), (3, 3, 5)], 200),
    "Shiau-Fan": ([(1, 0, 4), (-1, 1, 1), (0, 1, 1), (1, 1, 2)], 8),
}

ALGORITHM_GROUPS: dict[str, list[str]] = {
    "Quantization": ["Nearest Palette", "Threshold", "Random", "Interleaved Gradient Noise", "Blue Noise"],
    "Ordered": ["Bayer 2x2", "Bayer 4x4", "Bayer 8x8", "Bayer 16x16", "Bayer 32x32", "Clustered Dot 4x4", "Clustered Dot 8x8", "Random Ordered", "Halftone"],
    "Pattern": ["Bit Tone", "Pattern", "Dot Pattern", "Modulation"],
    "Error Diffusion": list(ERROR_DIFFUSION_KERNELS),
    "Advanced": ["Dot Diffusion", "Riemersma"],
}

ALGORITHMS = [name for group in ALGORITHM_GROUPS.values() for name in group]
