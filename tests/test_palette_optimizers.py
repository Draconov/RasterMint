from __future__ import annotations

import numpy as np
from PIL import Image

from rastermint.core.palette import PALETTE_OPTIMIZERS, extract_palette


def sample_image() -> Image.Image:
    y, x = np.mgrid[0:64, 0:96]
    arr = np.stack([(x * 3) % 256, (y * 5) % 256, ((x + y) * 2) % 256], axis=2).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def test_all_palette_optimizers_return_valid_requested_bound():
    image = sample_image()
    for method in PALETTE_OPTIMIZERS:
        colors = extract_palette(image, 8, method)
        assert 2 <= len(colors) <= 8
        assert all(c.startswith("#") and len(c) == 7 for c in colors)


def test_kmeans_and_wu_are_deterministic():
    image = sample_image()
    for method in ("K-Means", "Wu Quantization"):
        assert extract_palette(image, 6, method) == extract_palette(image, 6, method)
