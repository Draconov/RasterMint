# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import numpy as np
from PIL import Image

from rastermint.core.processor import make_preview_source, process_image, scaled_output_size
from rastermint.core.settings import ProcessingSettings


def test_processor_preserves_output_size_with_pixelation():
    img = Image.new("RGB", (31, 19), (120, 150, 200))
    settings = ProcessingSettings(pixel_size=4, algorithm="Atkinson")
    out = process_image(img, settings)
    assert out.size == img.size
    assert out.mode == "RGB"


def test_output_divisor_changes_final_dimensions():
    img = Image.new("RGB", (101, 59), (120, 150, 200))
    settings = ProcessingSettings(output_divisor=3, algorithm="Nearest Palette")
    out = process_image(img, settings)
    assert out.size == (33, 19)
    assert scaled_output_size(img.size, 3) == out.size


def test_processor_only_emits_palette_colors():
    data = np.random.default_rng(3).integers(0, 256, (40, 60, 3), dtype=np.uint8)
    img = Image.fromarray(data, mode="RGB")
    palette = ["#102030", "#8090A0", "#F0E0D0"]
    settings = ProcessingSettings(
        algorithm="Floyd-Steinberg",
        serpentine=True,
        dither_strength=1.0,
        palette=palette,
    )
    out = process_image(img, settings)
    emitted = {tuple(pixel) for pixel in np.asarray(out).reshape(-1, 3)}
    expected = {(16, 32, 48), (128, 144, 160), (240, 224, 208)}
    assert emitted <= expected


def test_preview_is_bounded():
    img = Image.new("RGB", (2000, 1000), "white")
    preview = make_preview_source(img, max_side=500)
    assert max(preview.size) <= 500
    assert preview.size == (500, 250)


def test_preview_respects_output_divisor_before_preview_cap():
    img = Image.new("RGB", (1920, 1080), "white")

    # Final ÷4 output is 480×270, which is already below the 640 preview cap.
    preview = make_preview_source(img, output_divisor=4)
    assert preview.size == (480, 270)

    # ÷2 would be 960×540, so only the preview cap reduces it further.
    preview = make_preview_source(img, output_divisor=2)
    assert preview.size == (640, 360)
