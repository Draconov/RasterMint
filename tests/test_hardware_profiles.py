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
    assert not result.hardware_constraints_enabled
    assert result.hardware_constraints == {}
    assert result.display_profile == {}
    kinds = [step["kind"] for step in result.effect_stack]
    assert "Hardware Limits" in kinds
    assert "Hardware Display" in kinds
    assert kinds[-2:] == ["Hardware Limits", "Hardware Display"]
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


def test_strict_fixed_palette_layer_uses_live_active_palette_after_profile_apply():
    settings = apply_profile_to_settings(ProcessingSettings(), profile_map()["game-boy"], mode="strict")
    limits = next(step for step in settings.effect_stack if step["kind"] == "Hardware Limits")
    assert limits["params"]["palette_source"] == "Active Palette"

    settings.palette = ["#100000", "#500000", "#A00000", "#FF0000"]
    settings.palette_locks = [False] * 4
    source = Image.new("RGB", (24, 24), (128, 128, 128))
    result = np.asarray(process_image(source, settings).convert("RGB"))
    emitted = {tuple(color) for color in result.reshape(-1, 3)}
    active = {(16, 0, 0), (80, 0, 0), (160, 0, 0), (255, 0, 0)}
    assert emitted <= active


def test_hardware_display_is_visible_layer_but_remains_display_stage():
    settings = apply_profile_to_settings(ProcessingSettings(), profile_map()["crt-ntsc"], mode="visual")
    display = next(step for step in settings.effect_stack if step["kind"] == "Hardware Display")
    assert display["params"]["color_bleed"] > 0
    source = Image.new("RGB", (48, 32), (180, 80, 40))
    raw = process_image(source, settings, display_mode="raw")
    shown = process_image(source, settings, display_mode="display")
    assert raw.size != shown.size or not np.array_equal(np.asarray(raw), np.asarray(shown))

    display["enabled"] = False
    disabled = process_image(source, settings, display_mode="display")
    corrected = process_image(source, settings, display_mode="corrected")
    assert np.array_equal(np.asarray(disabled), np.asarray(corrected))


def test_legacy_hidden_hardware_constraints_still_work_for_old_presets():
    settings = ProcessingSettings(
        hardware_constraints_enabled=True,
        hardware_constraints={"channel_bits": [2, 2, 2]},
    )
    source = Image.new("RGB", (2, 1), (91, 147, 213))
    result = np.asarray(process_image(source, settings))
    levels = {round(i / 3 * 255) for i in range(4)}
    assert all(int(value) in levels for value in result.reshape(-1))


def test_hardware_palette_enforcement_has_only_active_or_profile_palette():
    from rastermint.core.effect_schema import EFFECT_DEFINITIONS, normalize_effect_stack

    spec = EFFECT_DEFINITIONS["Hardware Limits"]["params"]["palette_source"]
    assert spec["options"] == ["Active Palette", "Profile Palette"]

    unsupported_legacy = {
        "id": "hardware-limits",
        "kind": "Hardware Limits",
        "enabled": True,
        "params": {"palette_source": "None"},
    }
    normalized = normalize_effect_stack([unsupported_legacy])
    assert normalized[0]["params"]["palette_source"] == "Active Palette"


def test_hardware_limits_without_profile_palette_do_not_enforce_active_palette():
    from PIL import Image
    import numpy as np

    from rastermint.core.hardware import apply_hardware_limits_layer

    source = Image.new("RGB", (1, 1), (91, 147, 213))
    params = {
        "palette_source": "Active Palette",
        "profile_palette_json": "[]",
        "channel_r_bits": 8,
        "channel_g_bits": 8,
        "channel_b_bits": 8,
        "max_colors_global": 0,
        "tile_max_colors": 0,
        "tile_width": 8,
        "tile_height": 8,
        "use_profile_groups": False,
        "profile_group_indices_json": "[]",
    }
    result = apply_hardware_limits_layer(source, params, ["#000000", "#FFFFFF"])
    assert np.array_equal(np.asarray(result), np.asarray(source))



def test_hardware_limits_summary_hides_inapplicable_palette_source():
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")
    from rastermint.qmlui.models import LayerListModel

    model = LayerListModel()
    model.replace([{
        "id": "hardware-limits",
        "kind": "Hardware Limits",
        "enabled": True,
        "params": {
            "palette_source": "Active Palette",
            "channel_r_bits": 8,
            "channel_g_bits": 8,
            "profile_palette_json": "[]",
        },
    }])
    summary = model.data(model.index(0, 0), model.SummaryRole)
    assert "palette_source" not in summary
    assert "channel_r_bits: 8" in summary


def test_hardware_limits_summary_keeps_palette_source_when_profile_palette_exists():
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")
    from rastermint.qmlui.models import LayerListModel

    model = LayerListModel()
    model.replace([{
        "id": "hardware-limits",
        "kind": "Hardware Limits",
        "enabled": True,
        "params": {
            "palette_source": "Active Palette",
            "channel_r_bits": 8,
            "profile_palette_json": '["#000000", "#FFFFFF"]',
        },
    }])
    summary = model.data(model.index(0, 0), model.SummaryRole)
    assert "palette_source: Active Palette" in summary


def test_visual_mode_exposes_supported_hardware_limits_disabled_for_editing():
    profiles = profile_map()
    visual = apply_profile_to_settings(ProcessingSettings(), profiles["game-boy"], mode="visual")
    limits = next(step for step in visual.effect_stack if step["kind"] == "Hardware Limits")
    assert limits["enabled"] is False

    strict = apply_profile_to_settings(ProcessingSettings(), profiles["game-boy"], mode="strict")
    strict_limits = next(step for step in strict.effect_stack if step["kind"] == "Hardware Limits")
    assert strict_limits["enabled"] is True


def test_profiles_without_strict_constraints_do_not_get_empty_limits_layer():
    visual = apply_profile_to_settings(ProcessingSettings(), profile_map()["crt-ntsc"], mode="visual")
    assert all(step["kind"] != "Hardware Limits" for step in visual.effect_stack)
