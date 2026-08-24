# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import numpy as np

from rastermint.core.builtin_presets import build_builtin_preset
from rastermint.core.dither import apply_dither
from rastermint.core.effect_stack import apply_effect_stack
from rastermint.core.palette import palette_array
from rastermint.core.settings import ProcessingSettings


def test_1to1_checker_mixes_mid_gray_evenly_with_bw_palette():
    image = np.full((8, 8, 3), 127.5, dtype=np.float32)
    palette = palette_array(["#000000", "#FFFFFF"])
    out = apply_dither(
        image, palette, "1:1 Colour Mix",
        color_mix_pattern="Checker", color_mix_distance="RGB",
    )
    colors, counts = np.unique(out.reshape(-1, 3).astype(np.uint8), axis=0, return_counts=True)
    observed = {tuple(color): int(count) for color, count in zip(colors, counts, strict=True)}
    assert observed == {(0, 0, 0): 32, (255, 255, 255): 32}


def test_1to1_phase_swaps_pair_placement_without_changing_palette():
    image = np.full((4, 4, 3), 127.5, dtype=np.float32)
    palette = palette_array(["#000000", "#FFFFFF"])
    a = apply_dither(image, palette, "1:1 Colour Mix", color_mix_distance="RGB", color_mix_phase=0)
    b = apply_dither(image, palette, "1:1 Colour Mix", color_mix_distance="RGB", color_mix_phase=1)
    assert np.array_equal(a, 255.0 - b)


def test_1to1_exact_palette_colour_is_not_needlessly_mixed():
    palette = palette_array(["#102030", "#708090", "#F0E0D0"])
    image = np.tile(palette[1][None, None, :], (3, 5, 1))
    out = apply_dither(image, palette, "1:1 Colour Mix", color_mix_distance="OKLab")
    assert np.array_equal(out, image)


def test_1to1_large_palette_stays_inside_active_palette():
    colors = [f"#{i:02X}{(255-i):02X}{((i*37) % 256):02X}" for i in range(256)]
    palette = palette_array(colors)
    image = np.random.default_rng(0x524D).uniform(0, 255, (12, 13, 3)).astype(np.float32)
    out = apply_dither(image, palette, "1:1 Colour Mix")
    palette_set = {tuple(map(int, color)) for color in palette}
    assert {tuple(map(int, color)) for color in out.reshape(-1, 3)} <= palette_set


def test_accurate_1to1_preset_preserves_current_palette_and_applies_through_stack():
    base = ProcessingSettings(
        palette=["#000000", "#FFFFFF"],
        palette_name="My Palette",
        palette_author="User",
        palette_source="custom",
        palette_locks=[True, False],
    )
    settings = build_builtin_preset("accurate-1to1", base)
    assert settings.palette == base.palette
    assert settings.palette_name == "My Palette"
    assert settings.palette_locks == [True, False]

    dither = next(step for step in settings.effect_stack if step["kind"] == "Dither")
    assert dither["params"]["algorithm"] == "1:1 Colour Mix"
    assert dither["params"]["color_mix_pattern"] == "Checker"
    assert dither["params"]["color_mix_distance"] == "OKLab"

    from PIL import Image
    source = Image.new("RGB", (8, 8), (128, 128, 128))
    rendered = apply_effect_stack(source, settings.effect_stack, settings.palette)
    emitted = {tuple(color) for color in np.asarray(rendered.convert("RGB")).reshape(-1, 3)}
    assert emitted <= {(0, 0, 0), (255, 255, 255)}
