from __future__ import annotations

import numpy as np
from PIL import Image

from rastermint.core.effect_stack import (
    _ascii_mapping_chars,
    _GLYPH_SETS,
    apply_effect_stack,
    ascii_available_chars,
    ascii_depth_max,
    new_effect,
)


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


def test_ascii_depth_counts_visible_symbols_not_hidden_space():
    assert ascii_depth_max("Decimal", "", "Mono", 9) == 10
    assert ascii_depth_max("Diamonds", "", "Mono", 9) == 4


def test_ascii_mapping_keeps_empty_space_without_consuming_depth_slot():
    chars = _ascii_mapping_chars(
        "Diamonds", "", 4, 0, True, "Mono", 9,
    )
    assert " " in chars
    assert len([char for char in chars if not char.isspace()]) == 4


def test_builtin_glyph_sets_keep_all_visible_symbols_with_font_fallbacks():
    for name, raw in _GLYPH_SETS.items():
        available = ascii_available_chars(name, "", "Mono", 9)
        raw_visible = [char for char in raw if not char.isspace()]
        available_visible = [char for char in available if not char.isspace()]
        assert available_visible == raw_visible, name


def test_ascii_glyph_scale_changes_rendered_glyph_size():
    source = Image.new("RGB", (80, 48), (255, 255, 255))
    small = _ascii_effect("Solid Colour")
    small["params"].update(cell_size=16, character_set="Minimal ASCII", depth=6, font_scale=0.4, background="#000000")
    large = _ascii_effect("Solid Colour")
    large["params"].update(cell_size=16, character_set="Minimal ASCII", depth=6, font_scale=1.5, background="#000000")

    small_img = np.asarray(apply_effect_stack(source, [small], ["#000000", "#FFFFFF"]).convert("RGB"))
    large_img = np.asarray(apply_effect_stack(source, [large], ["#000000", "#FFFFFF"]).convert("RGB"))
    small_lit = int(np.count_nonzero(np.any(small_img > 0, axis=2)))
    large_lit = int(np.count_nonzero(np.any(large_img > 0, axis=2)))
    assert large_lit > small_lit
