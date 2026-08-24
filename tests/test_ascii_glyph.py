from __future__ import annotations

import numpy as np
from PIL import Image

from rastermint.core.effect_stack import (
    _ascii_grid_data,
    _ascii_mapping_chars,
    _GLYPH_SETS,
    apply_effect_stack,
    ascii_available_chars,
    ascii_depth_max,
    ascii_text_grid,
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


def test_braille_blank_survives_even_when_font_probe_has_no_ink(monkeypatch):
    import rastermint.core.effect_stack as effect_stack

    original = effect_stack._glyph_font_ref

    def simulated_linux_probe(font_name, font_size, char):
        if char == "\u2800":
            return None
        return original(font_name, font_size, char)

    monkeypatch.setattr(effect_stack, "_glyph_font_ref", simulated_linux_probe)
    effect_stack.ascii_available_chars.cache_clear()
    try:
        available = effect_stack.ascii_available_chars("Braille Cells", "", "Mono", 9)
        assert "\u2800" in available
        assert [char for char in available if not char.isspace()] == [
            char for char in effect_stack._GLYPH_SETS["Braille Cells"] if not char.isspace()
        ]
    finally:
        effect_stack.ascii_available_chars.cache_clear()


def test_ascii_injected_characters_extend_builtin_set_and_depth():
    available = ascii_available_chars("Minimal ASCII", "", "Mono", 9, "XYZX")
    assert available.count("X") == 1
    assert "Y" in available and "Z" in available
    assert ascii_depth_max("Minimal ASCII", "", "Mono", 9, "XYZX") == 9


def test_structure_match_distinguishes_vertical_and_horizontal_edges():
    vertical = np.zeros((16, 16, 3), dtype=np.uint8)
    vertical[:, 7:9] = 255
    horizontal = np.zeros((16, 16, 3), dtype=np.uint8)
    horizontal[7:9, :] = 255

    common = dict(
        character_set="Custom",
        custom_chars="|-",
        inject_chars="",
        mapping="Structure Match",
        cell_size=16,
        spacing_x=0,
        spacing_y=0,
        depth=2,
        offset=0,
        invert=False,
        auto_density=False,
        structure=100.0,
        density_influence=0.0,
        local_detail=0.0,
        auto_cell_aspect=False,
        supersampling="4×",
        color_sampling="Glyph Weighted",
        font_name="Mono",
        font_scale=0.9,
    )
    vertical_grid = ascii_text_grid(Image.fromarray(vertical, "RGB"), **common).strip()
    horizontal_grid = ascii_text_grid(Image.fromarray(horizontal, "RGB"), **common).strip()
    assert vertical_grid == "|"
    assert horizontal_grid == "-"


def test_structure_match_auto_cell_aspect_packs_more_columns():
    source = Image.new("RGB", (80, 20), (255, 255, 255))
    common = dict(
        character_set="Custom",
        custom_chars="I#",
        cell_size=20,
        spacing_x=0,
        spacing_y=0,
        depth=2,
        offset=0,
        invert=False,
        auto_density=False,
        font_name="Mono",
        font_scale=0.9,
        inject_chars="",
        mapping="Structure Match",
        structure=75.0,
        density_influence=25.0,
        local_detail=35.0,
        supersampling="4×",
        color_sampling="Glyph Weighted",
    )
    square_lines, _square_colors, square_layout = _ascii_grid_data(
        source, auto_cell_aspect=False, **common
    )
    auto_lines, _auto_colors, auto_layout = _ascii_grid_data(
        source, auto_cell_aspect=True, **common
    )
    assert int(auto_layout["cell_width"]) < int(square_layout["cell_width"])
    assert len(auto_lines[0]) > len(square_lines[0])


def test_structure_match_glyph_weighted_colour_samples_under_glyph():
    arr = np.zeros((20, 20, 3), dtype=np.uint8)
    arr[:, 8:12, 0] = 255
    source = Image.fromarray(arr, "RGB")
    common = dict(
        character_set="Custom",
        custom_chars="|-",
        cell_size=20,
        spacing_x=0,
        spacing_y=0,
        depth=2,
        offset=0,
        invert=False,
        auto_density=False,
        font_name="Mono",
        font_scale=0.9,
        inject_chars="",
        mapping="Structure Match",
        structure=100.0,
        density_influence=0.0,
        local_detail=0.0,
        auto_cell_aspect=False,
        supersampling="4×",
    )
    average_lines, average_colors, _layout = _ascii_grid_data(
        source, color_sampling="Cell Average", **common
    )
    weighted_lines, weighted_colors, _layout = _ascii_grid_data(
        source, color_sampling="Glyph Weighted", **common
    )
    assert average_lines[0] == weighted_lines[0] == "|"
    assert float(weighted_colors[0][0][0]) > float(average_colors[0][0][0]) * 2.0


def test_density_mapping_remains_classic_square_cell_path():
    source = Image.new("RGB", (40, 20), (200, 200, 200))
    _lines, _colors, layout = _ascii_grid_data(
        source,
        "Classic ASCII",
        "",
        10,
        0,
        0,
        9,
        0,
        False,
        True,
        "Mono",
        0.9,
        mapping="Density",
        auto_cell_aspect=True,
        supersampling="4×",
        color_sampling="Glyph Weighted",
    )
    assert int(layout["cell_width"]) == 10
    assert int(layout["supersampling"]) == 1
    assert layout["high_detail"] is False
