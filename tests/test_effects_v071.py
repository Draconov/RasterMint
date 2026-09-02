from __future__ import annotations

import numpy as np
from PIL import Image

from rastermint.core.effect_schema import EFFECT_DEFINITIONS, EFFECT_DESCRIPTIONS, effect_categories, new_effect
from rastermint.core.effect_stack import apply_effect_stack


def test_vignette_is_a_visible_layer_effect_with_expected_controls():
    assert "Vignette" in EFFECT_DEFINITIONS
    params = EFFECT_DEFINITIONS["Vignette"]["params"]
    assert list(params) == ["strength", "size", "softness", "roundness", "center_x", "center_y", "color"]
    assert params["strength"]["default"] > 0
    assert params["color"]["type"] == "color"
    assert EFFECT_DESCRIPTIONS["Vignette"].strip()
    assert any("Vignette" in category["effects"] for category in effect_categories())


def test_vignette_darkens_edges_more_than_center_and_keeps_size():
    source = Image.new("RGB", (65, 49), (240, 240, 240))
    effect = new_effect("Vignette")
    effect["params"].update(
        strength=1.0,
        size=0.45,
        softness=0.45,
        roundness=1.0,
        center_x=0.0,
        center_y=0.0,
        color="#000000",
    )

    result = apply_effect_stack(source, [effect], ["#000000", "#FFFFFF"])

    assert result.size == source.size
    center = result.getpixel((source.width // 2, source.height // 2))[0]
    corner = result.getpixel((0, 0))[0]
    assert center >= 235
    assert corner < center - 80


def test_noise_chroma_toggle_preserves_monochrome_noise_and_can_split_channels():
    source = Image.new("RGB", (48, 48), (128, 128, 128))
    mono = new_effect("Noise")
    mono["params"].update(amount=24.0, seed=77, temporal=False, chroma=False)
    chroma = new_effect("Noise")
    chroma["params"].update(amount=24.0, seed=77, temporal=False, chroma=True)

    mono_arr = np.asarray(apply_effect_stack(source, [mono], ["#000000", "#FFFFFF"]))
    chroma_a = np.asarray(apply_effect_stack(source, [chroma], ["#000000", "#FFFFFF"]))
    chroma_b = np.asarray(apply_effect_stack(source, [chroma], ["#000000", "#FFFFFF"]))

    assert np.array_equal(mono_arr[:, :, 0], mono_arr[:, :, 1])
    assert np.array_equal(mono_arr[:, :, 1], mono_arr[:, :, 2])
    assert np.any(chroma_a[:, :, 0] != chroma_a[:, :, 1])
    assert np.any(chroma_a[:, :, 1] != chroma_a[:, :, 2])
    assert np.array_equal(chroma_a, chroma_b)
