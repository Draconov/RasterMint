# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import numpy as np
from PIL import Image

from rastermint.core.processor import (
    FAST_PREVIEW_MAX_SIDE,
    PREVIEW_MAX_SIDE,
    make_preview_settings,
    make_preview_source,
    process_image,
    scaled_output_size,
)
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


def test_fast_and_refined_preview_budgets():
    img = Image.new("RGB", (2400, 1200), "white")
    draft = make_preview_source(img, max_side=FAST_PREVIEW_MAX_SIDE)
    refined = make_preview_source(img, max_side=PREVIEW_MAX_SIDE)
    assert draft.size == (320, 160)
    assert refined.size == (640, 320)


def test_filters_are_part_of_the_full_processing_pipeline():
    img = Image.new("RGB", (4, 4), (10, 20, 30))
    settings = ProcessingSettings(
        algorithm="Nearest Palette",
        invert=True,
        palette=["#000000", "#FFFFFF"],
    )
    out = process_image(img, settings)
    # Inverted (245,235,225) is closer to white than black.
    assert {tuple(pixel) for pixel in np.asarray(out).reshape(-1, 3)} == {(255, 255, 255)}


def test_preview_settings_scale_pixel_based_effects():
    settings = ProcessingSettings(pixel_size=6, blur_radius=3.0, sharpen=1.7)
    preview = make_preview_settings(settings, (1920, 1080), (640, 360))
    assert preview.output_divisor == 1
    assert preview.pixel_size == 2
    assert preview.blur_radius == 1.0
    assert preview.sharpen == 1.7
    # The original settings object must stay untouched.
    assert settings.pixel_size == 6
    assert settings.blur_radius == 3.0


def test_adaptive_preview_budget_reduces_only_expensive_interactive_algorithms():
    from rastermint.core.effect_stack import default_effect_stack
    from rastermint.core.processor import adaptive_preview_max_side

    settings = ProcessingSettings()
    settings.effect_stack = default_effect_stack(settings)
    dither = next(step for step in settings.effect_stack if step["kind"] == "Dither")
    dither["params"]["algorithm"] = "Riemersma"
    assert adaptive_preview_max_side(settings, FAST_PREVIEW_MAX_SIDE) == 180
    assert adaptive_preview_max_side(settings, PREVIEW_MAX_SIDE) == 360
    # Full-resolution preview mode is an explicit user request and is not capped.
    assert adaptive_preview_max_side(settings, 1200) == 1200
