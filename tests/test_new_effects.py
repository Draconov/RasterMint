from __future__ import annotations

from PIL import Image

from rastermint.core.effect_schema import effect_categories
from rastermint.core.effect_stack import EFFECT_DEFINITIONS, _resolve_text_font_path, apply_effect_stack, new_effect


NEW_EFFECTS = [
    "Local Contrast", "RGB Split", "Interlace", "Pixel Sort", "Screen Melt",
    "Block Shuffle", "Pixel Scatter", "Data Shift", "Row Shift", "Column Shift",
    "Cellular Automata", "Databend", "Channel Swap", "Pixel Material", "Text Overlay",
]


def test_requested_effects_are_registered():
    assert set(NEW_EFFECTS) <= set(EFFECT_DEFINITIONS)


def test_requested_effects_render_rgb_same_canvas():
    source = Image.new("RGB", (32, 24), (120, 80, 180))
    palette = ["#000000", "#FFFFFF", "#7F4FBF"]
    for kind in NEW_EFFECTS:
        step = new_effect(kind)
        # Keep material tiles small enough for this tiny test canvas.
        if kind == "Pixel Material":
            step["params"]["cell_size"] = 4
        result = apply_effect_stack(source, [step], palette, frame_time=0.3, frame_index=3)
        assert result.mode == "RGB", kind
        assert result.size == source.size, kind


def test_all_pixel_material_styles_render():
    source = Image.new("RGB", (24, 16), (80, 160, 220))
    styles = EFFECT_DEFINITIONS["Pixel Material"]["params"]["style"]["options"]
    for style in styles:
        step = new_effect("Pixel Material")
        step["params"].update(style=style, cell_size=4, gap=1)
        # Custom Sprite intentionally falls back to Flat when no sprite path is supplied.
        result = apply_effect_stack(source, [step], ["#000000", "#FFFFFF"])
        assert result.size == source.size
        assert result.mode == "RGB"


def test_text_overlay_is_legacy_only_and_pixel_text_is_the_primary_text_overlay():
    categories = {entry["name"]: entry["effects"] for entry in effect_categories()}
    text_effects = categories["Text & Overlay"]

    assert "Pixel Text" in text_effects
    assert "Text Overlay" not in text_effects
    # Keep legacy saved stacks valid even though users no longer see the
    # redundant older effect in the Add Effect menu.
    assert "Text Overlay" in EFFECT_DEFINITIONS


def test_text_font_choices_resolve_to_distinct_native_fonts():
    resolved = [_resolve_text_font_path(name) for name in ("Mono", "Sans", "Serif")]

    assert all(resolved), resolved
    assert len({str(path).casefold() for path in resolved}) == 3
