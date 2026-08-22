from __future__ import annotations

import numpy as np
from PIL import Image

from rastermint.core.hardware import (
    apply_hardware_constraints,
    apply_profile_to_settings,
    correct_pixel_aspect,
    load_builtin_profiles,
    profile_map,
)
from rastermint.core.processor import display_output_size, process_image, target_raster_size
from rastermint.core.settings import ProcessingSettings


def test_builtin_profiles_cover_requested_families():
    profiles = profile_map(load_builtin_profiles())
    expected = {
        "game-boy", "game-boy-color", "game-boy-advance", "nes", "snes",
        "mega-drive", "playstation", "zx-spectrum", "cga-320", "ega-320",
        "c64-multicolor", "amiga-ocs", "apple-ii-hgr", "crt-ntsc",
        "crt-pal", "monochrome-lcd",
    }
    assert expected <= set(profiles)


def test_game_boy_profile_applies_raster_palette_and_display():
    settings = ProcessingSettings()
    result = apply_profile_to_settings(settings, profile_map()["game-boy"], mode="strict")
    assert (result.target_width, result.target_height) == (160, 144)
    assert result.target_enabled
    assert len(result.palette) == 4
    assert result.hardware_constraints_enabled
    assert result.display_mode == "display"


def test_gba_strict_rgb555_quantizes_each_channel_to_5_bits():
    constraints = {"channel_bits": [5, 5, 5]}
    source = Image.fromarray(np.array([[[17, 83, 241], [255, 127, 3]]], dtype=np.uint8), "RGB")
    result = np.asarray(apply_hardware_constraints(source, constraints))
    # RGB555 expansion can only land on 32 equally spaced code values.
    levels = {round(i / 31 * 255) for i in range(32)}
    assert all(int(v) in levels for v in result.reshape(-1))


def test_zx_strict_limits_each_attribute_cell_to_two_colors():
    rng = np.random.default_rng(7)
    source = Image.fromarray(rng.integers(0, 256, (16, 16, 3), dtype=np.uint8), "RGB")
    profile = profile_map()["zx-spectrum"]
    constraints = profile.strict["constraints"]
    result = np.asarray(apply_hardware_constraints(source, constraints))
    for y in range(0, 16, 8):
        for x in range(0, 16, 8):
            colors = np.unique(result[y:y+8, x:x+8].reshape(-1, 3), axis=0)
            assert len(colors) <= 2


def test_pixel_aspect_correction_changes_display_width_not_framebuffer():
    image = Image.new("RGB", (320, 200), "red")
    corrected = correct_pixel_aspect(image, 5, 6)
    assert image.size == (320, 200)
    assert corrected.size == (267, 200)

    settings = ProcessingSettings(target_enabled=True, target_width=320, target_height=200, pixel_aspect_x=5, pixel_aspect_y=6, display_mode="corrected")
    assert target_raster_size((800, 600), settings) == (320, 200)
    assert display_output_size((800, 600), settings) == (267, 200)


def test_strict_profile_runs_in_full_processor():
    profile = profile_map()["game-boy"]
    settings = apply_profile_to_settings(ProcessingSettings(), profile, mode="strict")
    source = Image.new("RGB", (80, 80), (180, 80, 220))
    result = process_image(source, settings)
    assert result.size == (160, 144)
    assert len(np.unique(np.asarray(result).reshape(-1, 3), axis=0)) <= 4


def test_new_settings_round_trip_hardware_raster_grid_and_random_locks():
    settings = ProcessingSettings(
        target_enabled=True,
        target_width=320,
        target_height=200,
        crop_left=0.1,
        pixel_aspect_x=5,
        pixel_aspect_y=6,
        display_mode="display",
        display_export=True,
        display_profile={"scanlines": 0.2},
        grid_enabled=True,
        grid_preview=True,
        grid_export=True,
        grid_spacing=2,
        grid_major_spacing=8,
        hardware_profile_id="cga-320",
        hardware_mode="strict",
        hardware_constraints_enabled=True,
        hardware_constraints={"max_colors_global": 4},
        random_locks={"palette": True, "resolution": False},
    )
    restored = ProcessingSettings.from_dict(settings.to_dict())
    assert restored.to_dict() == settings.to_dict()
