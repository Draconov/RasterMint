# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import numpy as np
from PIL import Image, ImageDraw

from rastermint.core.animation import settings_at_time
from rastermint.core.effect_stack import EFFECT_DEFINITIONS, _load_text_font, _render_text_block, apply_effect_stack, effect_categories, new_effect, normalize_effect_stack, scale_stack_for_preview
from rastermint.core.settings import ProcessingSettings


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


def test_every_user_addable_effect_is_present_once_in_categories():
    categories = effect_categories()
    flattened = [kind for category in categories for kind in category["effects"]]
    # Text Overlay is intentionally legacy-only: Pixel Text supersedes it in
    # the UI, while the definition remains available to old saved stacks.
    assert set(flattened) == set(EFFECT_DEFINITIONS) - {"Text Overlay"}
    assert len(flattened) == len(set(flattened))
    assert all(category["effects"] for category in categories)

def test_large_pixel_text_layer_keeps_full_glyph_bounds():
    text = "PIXEL TEXT"
    size = 192
    font = _load_text_font("Pixel", size)

    reference = Image.new("RGBA", (2600, 700), (0, 0, 0, 0))
    reference_draw = ImageDraw.Draw(reference)
    bbox = reference_draw.textbbox((0, 0), text, font=font)
    reference_draw.text(
        (-bbox[0] + 40, -bbox[1] + 40),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )
    expected_pixels = np.count_nonzero(np.asarray(reference.getchannel("A")))

    layer = _render_text_block(
        text,
        size=size,
        color="#FFFFFF",
        font_name="Pixel",
        max_width=2400,
    )
    rendered_pixels = np.count_nonzero(np.asarray(layer.getchannel("A")))

    assert rendered_pixels == expected_pixels


def test_rotated_text_pattern_covers_all_canvas_corners():
    source = Image.new("RGB", (256, 192), (0, 0, 0))
    effect = new_effect("Text Pattern")
    effect["params"].update(
        text="MMMMMMMMMMMMMMMM",
        size=14,
        color="#FFFFFF",
        font="Sans",
        spacing_x=14,
        spacing_y=14,
        offset_x=0,
        rotation=45.0,
        opacity=1.0,
    )

    out = np.asarray(apply_effect_stack(source, [effect], ["#000000", "#FFFFFF"]))
    regions = (
        out[:40, :40],
        out[:40, -40:],
        out[-40:, :40],
        out[-40:, -40:],
    )

    assert all(np.any(region != 0) for region in regions)


def test_text_glitch_temporal_mode_changes_between_frames_but_static_mode_is_stable():
    source = Image.new("RGB", (320, 180), (10, 10, 10))
    effect = new_effect("Text Glitch")
    effect["params"].update(
        text="GLITCH TEST",
        size=48,
        temporal=True,
        slice_shift=12,
        vertical_jitter=4,
        dropout=0.2,
        seed=7,
    )

    frame_0 = np.asarray(apply_effect_stack(source, [effect], ["#000000", "#FFFFFF"], frame_time=0.0, frame_index=0))
    frame_1 = np.asarray(apply_effect_stack(source, [effect], ["#000000", "#FFFFFF"], frame_time=1 / 30, frame_index=1))
    assert not np.array_equal(frame_0, frame_1)

    effect["params"]["temporal"] = False
    static_0 = np.asarray(apply_effect_stack(source, [effect], ["#000000", "#FFFFFF"], frame_time=0.0, frame_index=0))
    static_1 = np.asarray(apply_effect_stack(source, [effect], ["#000000", "#FFFFFF"], frame_time=1.0, frame_index=30))
    assert np.array_equal(static_0, static_1)


def test_typewriter_reveal_track_and_cursor_blink_are_frame_aware():
    source = Image.new("RGB", (320, 180), (10, 10, 10))
    palette = ["#000000", "#FFFFFF"]
    effect = new_effect("Typewriter Text", effect_id="typewriter")
    effect["params"].update(text="TYPE SOMETHING...", size=48, cursor=False)

    settings = ProcessingSettings()
    settings.effect_stack = [effect]
    settings.animation_tracks = [{
        "target": "effect:typewriter:progress",
        "from": 0.0,
        "to": 100.0,
        "start": 0.0,
        "end": 1.0,
        "easing": "Linear",
        "enabled": True,
    }]

    start = settings_at_time(settings, 0.0)
    middle = settings_at_time(settings, 0.5)
    end = settings_at_time(settings, 1.0)
    assert start.effect_stack[0]["params"]["progress"] == 0.0
    assert middle.effect_stack[0]["params"]["progress"] == 50.0
    assert end.effect_stack[0]["params"]["progress"] == 100.0

    start_frame = np.asarray(apply_effect_stack(source, start.effect_stack, palette, frame_time=0.0, frame_index=0))
    end_frame = np.asarray(apply_effect_stack(source, end.effect_stack, palette, frame_time=1.0, frame_index=30))
    assert not np.array_equal(start_frame, end_frame)

    blink = new_effect("Typewriter Text")
    blink["params"].update(text="HELLO", size=48, progress=40.0, cursor=True, cursor_blink=True, cursor_blink_speed=2.0)
    cursor_on = np.asarray(apply_effect_stack(source, [blink], palette, frame_time=0.0, frame_index=0))
    cursor_off = np.asarray(apply_effect_stack(source, [blink], palette, frame_time=0.3, frame_index=9))
    assert not np.array_equal(cursor_on, cursor_off)


# ---- merged from test_effects_v071.py ----

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


# ---- merged from test_animation.py ----

from rastermint.core.animation import ease_value, settings_at_time
from rastermint.core.effect_stack import default_effect_stack
from rastermint.core.settings import ProcessingSettings


def test_animation_interpolates_effect_parameter_without_mutating_source():
    settings = ProcessingSettings()
    settings.effect_stack = default_effect_stack(settings)
    adjustments = next(step for step in settings.effect_stack if step["kind"] == "Adjustments")
    target = f"effect:{adjustments['id']}:brightness"
    settings.animation_tracks = [{
        "target": target,
        "from": -20,
        "to": 80,
        "start": 1.0,
        "end": 3.0,
        "easing": "Linear",
        "enabled": True,
    }]

    animated = settings_at_time(settings, 2.0)
    animated_adjustments = next(step for step in animated.effect_stack if step["id"] == adjustments["id"])
    assert animated_adjustments["params"]["brightness"] == 30
    assert adjustments["params"]["brightness"] == 0


def test_easings_are_clamped():
    assert ease_value(-1, "Linear") == 0
    assert ease_value(2, "Linear") == 1
    assert 0 < ease_value(0.5, "Ease In") < 0.5
    assert 0.5 < ease_value(0.5, "Ease Out") < 1
