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

