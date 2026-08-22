# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import numpy as np
from PIL import Image

from rastermint.core.effect_stack import EFFECT_DEFINITIONS, apply_effect_stack, effect_categories, new_effect, normalize_effect_stack, scale_stack_for_preview


def test_effect_stack_executes_in_order():
    image = Image.new("RGB", (1, 1), (20, 30, 40))
    invert = new_effect("Invert")
    gray = new_effect("Grayscale")
    out = apply_effect_stack(image, [invert, gray], ["#000000", "#FFFFFF"])
    pixel = out.getpixel((0, 0))
    assert pixel[0] == pixel[1] == pixel[2]
    assert pixel[0] > 200


def test_disabled_effect_is_bypassed():
    image = Image.new("RGB", (1, 1), (20, 30, 40))
    invert = new_effect("Invert", enabled=False)
    out = apply_effect_stack(image, [invert], ["#000000", "#FFFFFF"])
    assert out.getpixel((0, 0)) == (20, 30, 40)


def test_preview_scaling_only_changes_pixel_scaled_parameters():
    blur = new_effect("Gaussian Blur")
    blur["params"]["radius"] = 9.0
    adjust = new_effect("Adjustments")
    adjust["params"]["brightness"] = 25
    stack = scale_stack_for_preview([blur, adjust], 1 / 3)
    assert stack[0]["params"]["radius"] == 3.0
    assert stack[1]["params"]["brightness"] == 25


def test_jpeg_compression_preserves_shape():
    rng = np.random.default_rng(1)
    image = Image.fromarray(rng.integers(0, 256, (16, 17, 3), dtype=np.uint8), "RGB")
    effect = new_effect("JPEG Compression")
    effect["params"]["quality"] = 20
    out = apply_effect_stack(image, [effect], ["#000000", "#FFFFFF"])
    assert out.size == image.size
    assert out.mode == "RGB"


def test_normalize_effect_stack_repairs_duplicate_ids():
    a = new_effect("Invert", effect_id="same")
    b = new_effect("Grayscale", effect_id="same")
    stack = normalize_effect_stack([a, b])
    assert len({step["id"] for step in stack}) == 2


def test_pixel_aspect_ratio_layer_changes_image_width_in_stack():
    image = Image.new("RGB", (8, 6), (40, 120, 80))
    layer = new_effect("Pixel Aspect Ratio")
    layer["params"]["x"] = 2.0
    layer["params"]["y"] = 1.0
    layer["params"]["resample"] = "Nearest"
    out = apply_effect_stack(image, [layer], ["#000000", "#FFFFFF"])
    assert out.size == (16, 6)


def test_every_effect_is_present_once_in_add_layer_categories():
    categories = effect_categories()
    flattened = [kind for category in categories for kind in category["effects"]]
    assert set(flattened) == set(EFFECT_DEFINITIONS)
    assert len(flattened) == len(set(flattened))
    assert all(category["effects"] for category in categories)
