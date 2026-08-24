from rastermint.core.builtin_presets import BUILTIN_PRESETS, build_builtin_preset
from rastermint.core.effect_stack import normalize_effect_stack
from rastermint.core.hardware import profile_map


def test_builtin_presets_are_unique_and_buildable():
    assert len(BUILTIN_PRESETS) >= 20
    assert len({item.id for item in BUILTIN_PRESETS}) == len(BUILTIN_PRESETS)
    profiles = profile_map()
    for preset in BUILTIN_PRESETS:
        settings = build_builtin_preset(preset.id)
        assert settings.palette
        assert normalize_effect_stack(settings.effect_stack, settings)
        if preset.hardware_profile_id:
            assert preset.hardware_profile_id in profiles
            assert settings.hardware_profile_id == preset.hardware_profile_id


def test_hardware_presets_apply_expected_rasters():
    game_boy = build_builtin_preset("game-boy")
    assert game_boy.target_enabled
    assert (game_boy.target_width, game_boy.target_height) == (160, 144)
    assert len(game_boy.palette) == 4

    c64 = build_builtin_preset("c64-multicolor")
    assert c64.hardware_profile_id == "c64-multicolor"
    assert any(step["kind"] == "Hardware Limits" for step in c64.effect_stack)

    playstation = build_builtin_preset("playstation")
    assert playstation.hardware_profile_id == "playstation"
    assert any(step["kind"] == "Hardware Limits" for step in playstation.effect_stack)
