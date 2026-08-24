from __future__ import annotations

import numpy as np
from PIL import Image

from rastermint.core.effect_stack import apply_effect_stack, new_effect


def _ascii_effect(background_mode: str):
    effect = new_effect("ASCII / Glyph")
    effect["params"].update(
        background_mode=background_mode,
        character_set="Classic ASCII",
        cell_size=10,
        depth=10,
        font="Mono",
        color_mode="Single Colour",
        foreground="#FFFFFF",
    )
    return effect


def test_ascii_transparent_background_creates_real_alpha():
    source = Image.new("RGB", (60, 40), (128, 128, 128))
    result = apply_effect_stack(source, [_ascii_effect("Transparent")], ["#000000", "#FFFFFF"])

    assert result.mode == "RGBA"
    alpha = np.asarray(result.getchannel("A"), dtype=np.uint8)
    assert int(alpha.min()) == 0
    assert int(alpha.max()) > 0
    assert np.any(alpha == 0)
    assert np.any(alpha > 0)


def test_ascii_solid_background_stays_fully_opaque():
    source = Image.new("RGB", (60, 40), (128, 128, 128))
    result = apply_effect_stack(source, [_ascii_effect("Solid Colour")], ["#000000", "#FFFFFF"])

    alpha = np.asarray(result.convert("RGBA").getchannel("A"), dtype=np.uint8)
    assert np.all(alpha == 255)


def test_ascii_transparency_survives_a_later_dither_layer(tmp_path):
    source = Image.new("RGB", (60, 40), (128, 128, 128))
    ascii_layer = _ascii_effect("Transparent")
    dither = new_effect("Dither")
    dither["params"]["algorithm"] = "Nearest Palette"

    result = apply_effect_stack(source, [ascii_layer, dither], ["#000000", "#FFFFFF"])
    assert result.mode == "RGBA"
    alpha_before = bytes(result.getchannel("A").tobytes())
    assert 0 in alpha_before
    assert max(alpha_before) > 0

    path = tmp_path / "ascii-transparent.png"
    result.save(path, format="PNG")
    with Image.open(path) as reopened:
        assert reopened.mode == "RGBA"
        assert bytes(reopened.getchannel("A").tobytes()) == alpha_before
