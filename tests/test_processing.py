# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import numpy as np
from PIL import Image

from rastermint.core.processor import (
    FAST_PREVIEW_MAX_SIDE,
    PREVIEW_MAX_SIDE,
    make_preview_settings,
    linked_target_size,
    make_preview_source,
    process_image,
    scaled_output_size,
    source_raster_size,
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


def test_linked_target_width_updates_height_from_source_aspect():
    settings = ProcessingSettings()
    assert linked_target_size((1920, 1080), settings, width=800) == (800, 450)


def test_linked_target_height_updates_width_from_source_aspect():
    settings = ProcessingSettings()
    assert linked_target_size((1920, 1080), settings, height=720) == (1280, 720)


def test_linked_target_uses_cropped_and_rotated_source_aspect():
    settings = ProcessingSettings(crop_left=0.25, crop_right=0.25, rotation=90)
    # 1200x800 -> crop to 600x800 -> rotate to 800x600 (4:3).
    assert source_raster_size((1200, 800), settings) == (800, 600)
    assert linked_target_size((1200, 800), settings, width=400) == (400, 300)


def test_structure_match_ascii_uses_expensive_interactive_preview_budget():
    from rastermint.core.effect_stack import default_effect_stack, new_effect
    from rastermint.core.processor import adaptive_preview_max_side

    settings = ProcessingSettings()
    settings.effect_stack = default_effect_stack(settings)
    ascii_layer = new_effect("ASCII / Glyph")
    ascii_layer["params"]["mapping"] = "Structure Match"
    settings.effect_stack.append(ascii_layer)

    assert adaptive_preview_max_side(settings, FAST_PREVIEW_MAX_SIDE) == 180
    assert adaptive_preview_max_side(settings, PREVIEW_MAX_SIDE) == 360
    assert adaptive_preview_max_side(settings, 1200) == 1200


# ---- merged from test_target_raster.py ----

from PIL import Image

from rastermint.core.processor import make_preview_source, prepare_raster_source, process_image, target_raster_size
from rastermint.core.settings import ProcessingSettings


def test_exact_target_raster_output():
    source = Image.new("RGB", (640, 360), "white")
    settings = ProcessingSettings(target_enabled=True, target_width=320, target_height=200, fit_mode="fit")
    result = process_image(source, settings)
    assert result.size == (320, 200)


def test_crop_and_rotation_change_implicit_raster_size():
    settings = ProcessingSettings(crop_left=0.1, crop_right=0.1, rotation=90)
    assert target_raster_size((100, 50), settings) == (50, 80)


def test_preview_source_respects_exact_raster_but_caps_budget():
    source = Image.new("RGB", (1920, 1080), "white")
    settings = ProcessingSettings(target_enabled=True, target_width=640, target_height=480)
    preview = make_preview_source(source, max_side=320, settings=settings)
    assert preview.size == (320, 240)


def test_processed_raster_size_accounts_for_pixel_aspect_layer():
    from rastermint.core.effect_stack import new_effect
    from rastermint.core.processor import processed_raster_size

    settings = ProcessingSettings(target_enabled=True, target_width=100, target_height=80)
    layer = new_effect("Pixel Aspect Ratio")
    layer["params"]["x"] = 1.5
    layer["params"]["y"] = 1.0
    settings.effect_stack = [layer]
    assert processed_raster_size((640, 480), settings) == (150, 80)


def test_horizontal_mirror_uses_center_axis_without_changing_size():
    source = Image.new("RGB", (4, 1))
    source.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)])
    settings = ProcessingSettings(mirror_horizontal=True, mirror_horizontal_axis=0.5)
    result = prepare_raster_source(source, settings)
    assert result.size == (4, 1)
    assert list(result.get_flattened_data()) == [(255, 0, 0), (0, 255, 0), (0, 255, 0), (255, 0, 0)]


def test_vertical_mirror_uses_center_axis_without_changing_size():
    source = Image.new("RGB", (1, 4))
    source.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)])
    settings = ProcessingSettings(mirror_vertical=True, mirror_vertical_axis=0.5)
    result = prepare_raster_source(source, settings)
    assert result.size == (1, 4)
    assert list(result.get_flattened_data()) == [(255, 0, 0), (0, 255, 0), (0, 255, 0), (255, 0, 0)]


def test_mirror_settings_roundtrip():
    settings = ProcessingSettings(
        mirror_horizontal=True,
        mirror_vertical=True,
        mirror_horizontal_axis=0.2,
        mirror_vertical_axis=0.8,
    )
    loaded = ProcessingSettings.from_dict(settings.to_dict())
    assert loaded.mirror_horizontal is True
    assert loaded.mirror_vertical is True
    assert loaded.mirror_horizontal_axis == 0.2
    assert loaded.mirror_vertical_axis == 0.8


# ---- merged from test_optimizations.py ----

import numpy as np
from PIL import Image

from rastermint.core import effect_stack as effect_stack_module
from rastermint.core import processor as processor_module
from rastermint.core.hardware import _tile_color_limit
from rastermint.core.palette import _kmeans_palette, _nearest_center_labels
from rastermint.core.settings import ProcessingSettings


def test_process_image_normalizes_effect_stack_only_once(monkeypatch):
    source = Image.new("RGB", (8, 8), (100, 140, 180))
    settings = ProcessingSettings(palette=["#000000", "#FFFFFF"])

    original = processor_module.normalize_effect_stack
    calls = 0

    def counted(stack, owner=None):
        nonlocal calls
        calls += 1
        return original(stack, owner)

    monkeypatch.setattr(processor_module, "normalize_effect_stack", counted)

    def unexpected_second_normalization(*_args, **_kwargs):
        raise AssertionError("normalized processor stack was normalized a second time")

    monkeypatch.setattr(effect_stack_module, "normalize_effect_stack", unexpected_second_normalization)
    processor_module.process_image(source, settings)
    assert calls == 1


def test_settings_clone_is_independent_without_serialization_round_trip():
    settings = ProcessingSettings(
        palette=["#112233", "#AABBCC"],
        palette_locks=[True, False],
        display_profile={"scanlines": 0.2},
        effect_stack=[{"id": "x", "kind": "Invert", "enabled": True, "params": {}}],
        animation_tracks=[{"target": "effect:x:amount", "keyframes": [{"time": 0.0, "value": 1.0}]}],
    )
    clone = settings.clone()
    assert clone.to_dict() == settings.to_dict()

    clone.palette[0] = "#000000"
    clone.display_profile["scanlines"] = 0.8
    clone.effect_stack[0]["enabled"] = False
    clone.animation_tracks[0]["keyframes"][0]["value"] = 2.0

    assert settings.palette[0] == "#112233"
    assert settings.display_profile["scanlines"] == 0.2
    assert settings.effect_stack[0]["enabled"] is True
    assert settings.animation_tracks[0]["keyframes"][0]["value"] == 1.0


def _legacy_tile_limit_reference(
    arr: np.ndarray,
    tile_width: int,
    tile_height: int,
    max_colors: int,
    palette_groups: list[list[str]] | None = None,
) -> np.ndarray:
    from rastermint.core.palette import palette_array

    def remap(region: np.ndarray, palette: np.ndarray) -> np.ndarray:
        flat = region.reshape(-1, 3).astype(np.float32)
        diff = flat[:, None, :] - palette[None, :, :]
        idx = np.argmin(np.sum(diff * diff, axis=2), axis=1)
        return palette[idx].reshape(region.shape).astype(np.uint8)

    def choose(region: np.ndarray, limit: int) -> np.ndarray:
        pixels = region.reshape(-1, 3)
        colors, counts = np.unique(pixels, axis=0, return_counts=True)
        if len(colors) <= limit:
            return colors.astype(np.float32)
        order = np.argsort(counts)[::-1][:limit]
        return colors[order].astype(np.float32)

    h, w, _ = arr.shape
    tw = max(1, int(tile_width))
    th = max(1, int(tile_height))
    limit = max(1, int(max_colors))
    out = arr.copy()
    groups = [palette_array(group) for group in (palette_groups or []) if group]
    for y in range(0, h, th):
        for x in range(0, w, tw):
            region = out[y:min(h, y + th), x:min(w, x + tw)]
            if groups:
                best_group = None
                best_error = float("inf")
                for group in groups:
                    mapped = remap(region, group)
                    error = float(np.mean((region.astype(np.float32) - mapped.astype(np.float32)) ** 2))
                    if error < best_error:
                        best_error = error
                        best_group = group
                assert best_group is not None
                mapped = remap(region, best_group)
                chosen = choose(mapped, limit)
                region[:] = remap(region, chosen)
            else:
                chosen = choose(region, limit)
                region[:] = remap(region, chosen)
    return out


def test_optimized_tile_limits_match_previous_output_exactly():
    rng = np.random.default_rng(0x524D)
    source = rng.integers(0, 256, (29, 37, 3), dtype=np.uint8)
    cases = [
        (8, 8, 4, None),
        (7, 5, 3, None),
        (8, 8, 2, [
            ["#000000", "#FFFFFF"],
            ["#000000", "#FF0000", "#FFFF00"],
            ["#000000", "#0000FF", "#00FFFF"],
        ]),
    ]
    for args in cases:
        expected = _legacy_tile_limit_reference(source, *args)
        actual = _tile_color_limit(source, *args)
        assert np.array_equal(actual, expected), args



def test_chunked_kmeans_assignment_matches_legacy_distance_formula():
    rng = np.random.default_rng(0x203)
    pixels = rng.uniform(0.0, 255.0, (2500, 3)).astype(np.float32)
    centers = rng.uniform(0.0, 255.0, (96, 3)).astype(np.float32)
    expected = np.argmin(
        np.sum((pixels[:, None, :] - centers[None, :, :]) ** 2, axis=2),
        axis=1,
    )
    actual = _nearest_center_labels(pixels, centers, chunk_pixels=257)
    assert np.array_equal(actual, expected)

def test_chunked_kmeans_is_deterministic():
    rng = np.random.default_rng(123)
    image = Image.fromarray(rng.integers(0, 256, (80, 96, 3), dtype=np.uint8), "RGB")
    assert _kmeans_palette(image, 16) == _kmeans_palette(image, 16)


def test_removed_hidden_hardware_constraint_fields_are_ignored():
    settings = ProcessingSettings.from_dict({
        "hardware_profile_id": "custom",
        "hardware_constraints_enabled": True,
        "hardware_constraints": {"channel_bits": [2, 2, 2]},
    })
    assert not hasattr(settings, "hardware_constraints_enabled")
    assert not hasattr(settings, "hardware_constraints")


def test_default_layer_composite_skips_pre_effect_framebuffer_copy(monkeypatch):
    from rastermint.core.effect_schema import new_effect, normalize_effect_stack

    source = Image.new("RGB", (12, 10), (10, 20, 30))
    stack = normalize_effect_stack([new_effect("Invert")])
    original_composite = effect_stack_module._apply_layer_composite
    observed_base = None

    def capture_base(base, effect, step):
        nonlocal observed_base
        observed_base = base
        return original_composite(base, effect, step)

    monkeypatch.setattr(effect_stack_module, "_apply_layer_composite", capture_base)
    result = effect_stack_module.apply_normalized_effect_stack(source, stack, ["#000000", "#FFFFFF"])

    assert result.getpixel((0, 0)) == (245, 235, 225)
    assert observed_base is source


def test_non_default_layer_composite_keeps_pre_effect_framebuffer_copy(monkeypatch):
    from rastermint.core.effect_schema import new_effect, normalize_effect_stack

    source = Image.new("RGB", (12, 10), (10, 20, 30))
    step = new_effect("Invert")
    step["opacity"] = 0.5
    stack = normalize_effect_stack([step])
    original_composite = effect_stack_module._apply_layer_composite
    observed_base = None

    def capture_base(base, effect, step):
        nonlocal observed_base
        observed_base = base
        return original_composite(base, effect, step)

    monkeypatch.setattr(effect_stack_module, "_apply_layer_composite", capture_base)
    effect_stack_module.apply_normalized_effect_stack(source, stack, ["#000000", "#FFFFFF"])

    assert observed_base is not source

def test_processing_can_cancel_between_layers():
    from rastermint.core.effect_schema import new_effect

    settings = ProcessingSettings(effect_stack=[new_effect("Invert"), new_effect("Invert")])
    checks = 0

    def cancelled():
        nonlocal checks
        checks += 1
        return checks >= 3

    with __import__("pytest").raises(effect_stack_module.ProcessingCancelled):
        processor_module.process_image(
            Image.new("RGB", (16, 16), "white"),
            settings,
            cancel_callback=cancelled,
        )

    assert checks >= 3


def test_tiled_processing_can_cancel_between_tiles():
    from rastermint.core.effect_schema import new_effect

    settings = ProcessingSettings(effect_stack=[new_effect("Invert")])
    checks = 0

    def cancelled():
        nonlocal checks
        checks += 1
        return checks >= 4

    with __import__("pytest").raises(effect_stack_module.ProcessingCancelled):
        processor_module.process_image(
            Image.new("RGB", (600, 600), "white"),
            settings,
            tiled_processing=True,
            tile_size=256,
            tile_threshold_pixels=1,
            cancel_callback=cancelled,
        )

    assert checks >= 4


def test_workers_use_settings_clone_instead_of_serialization_round_trip():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "src/rastermint/qmlui/workers.py").read_text(encoding="utf-8")
    assert "ProcessingSettings.from_dict(settings.to_dict())" not in source
    assert source.count("settings.clone()") >= 8
