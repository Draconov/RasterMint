import numpy as np
from PIL import Image

from rastermint.core.effect_schema import EFFECT_DEFINITIONS, effect_categories, new_effect, normalize_effect_stack
from rastermint.core.effect_stack import apply_effect_stack
from rastermint.core.temporal import TemporalEffectState, max_persistence_seconds


def _moving_dot_frames():
    first = np.zeros((5, 5, 3), dtype=np.uint8)
    second = np.zeros_like(first)
    first[2, 1] = 255
    second[2, 3] = 255
    return Image.fromarray(first, "RGB"), Image.fromarray(second, "RGB")


def _effect(mode="Generic", duration=1.0, strength=0.75):
    effect = new_effect("Display Persistence", effect_id="persistence-test")
    effect["params"].update(
        display_type=mode,
        persistence_time=duration,
        strength=strength,
        decay=1.0,
    )
    return effect


def test_display_persistence_schema_supports_long_typed_duration_and_category():
    spec = EFFECT_DEFINITIONS["Display Persistence"]["params"]
    assert spec["persistence_time"]["type"] == "duration"
    assert spec["persistence_time"]["slider_max"] == 60.0
    assert spec["persistence_time"]["max"] == 300.0
    assert spec["display_type"]["options"] == ["Generic", "CRT", "LCD", "OLED"]
    normalized = normalize_effect_stack([
        {
            "id": "long",
            "kind": "Display Persistence",
            "enabled": True,
            "params": {"persistence_time": 240.0},
        }
    ])
    assert normalized[0]["params"]["persistence_time"] == 240.0
    assert any(
        row["name"] == "Display Geometry & Response" and "Display Persistence" in row["effects"]
        for row in effect_categories()
    )


def test_zero_seconds_is_true_bypass_and_clears_history():
    first, second = _moving_dot_frames()
    state = TemporalEffectState()
    effect = _effect(duration=1.0)
    apply_effect_stack(first, [effect], ["#000000", "#FFFFFF"], frame_time=0.0, frame_index=0, temporal_state=state)
    effect["params"]["persistence_time"] = 0.0
    bypass = apply_effect_stack(second, [effect], ["#000000", "#FFFFFF"], frame_time=1 / 30, frame_index=1, temporal_state=state)
    assert np.array_equal(np.asarray(bypass), np.asarray(second))

    effect["params"]["persistence_time"] = 1.0
    restarted = apply_effect_stack(second, [effect], ["#000000", "#FFFFFF"], frame_time=2 / 30, frame_index=2, temporal_state=state)
    assert np.array_equal(np.asarray(restarted), np.asarray(second))


def test_generic_persistence_keeps_current_frame_and_shows_dimmed_previous_frame():
    first, second = _moving_dot_frames()
    state = TemporalEffectState()
    effect = _effect(mode="Generic", duration=1.0, strength=0.8)

    apply_effect_stack(first, [effect], ["#000000", "#FFFFFF"], frame_time=0.0, frame_index=0, temporal_state=state)
    result = np.asarray(
        apply_effect_stack(second, [effect], ["#000000", "#FFFFFF"], frame_time=1 / 30, frame_index=1, temporal_state=state)
    )
    # Current bright pixel remains fully present.
    assert result[2, 3, 0] == 255
    # Previous bright pixel remains as a dimmer ghost.
    assert 0 < result[2, 1, 0] < 255


def test_display_models_are_distinct_and_crt_preserves_green_longest():
    first, second = _moving_dot_frames()
    outputs = {}
    for mode in ("Generic", "CRT", "LCD", "OLED"):
        state = TemporalEffectState()
        effect = _effect(mode=mode, duration=1.0, strength=0.8)
        apply_effect_stack(first, [effect], ["#000000", "#FFFFFF"], frame_time=0.0, frame_index=0, temporal_state=state)
        outputs[mode] = np.asarray(
            apply_effect_stack(second, [effect], ["#000000", "#FFFFFF"], frame_time=1 / 30, frame_index=1, temporal_state=state)
        )
    assert not np.array_equal(outputs["CRT"], outputs["LCD"])
    assert not np.array_equal(outputs["LCD"], outputs["OLED"])

    # A white CRT ghost separates into channel-specific phosphor persistence.
    ghost = outputs["CRT"][2, 1]
    assert ghost[1] >= ghost[0] >= ghost[2]


def test_rewind_resets_temporal_history_instead_of_leaking_future_frames():
    first, second = _moving_dot_frames()
    state = TemporalEffectState()
    effect = _effect(mode="CRT", duration=2.0, strength=1.0)
    apply_effect_stack(first, [effect], ["#000000", "#FFFFFF"], frame_time=0.0, frame_index=0, temporal_state=state)
    apply_effect_stack(second, [effect], ["#000000", "#FFFFFF"], frame_time=1 / 30, frame_index=1, temporal_state=state)

    rewound = apply_effect_stack(first, [effect], ["#000000", "#FFFFFF"], frame_time=0.0, frame_index=0, temporal_state=state)
    assert np.array_equal(np.asarray(rewound), np.asarray(first))


def test_max_persistence_seconds_ignores_disabled_layers():
    short = _effect(duration=2.0)
    long = _effect(duration=45.0)
    long["id"] = "long"
    disabled = _effect(duration=120.0)
    disabled["id"] = "disabled"
    disabled["enabled"] = False
    assert max_persistence_seconds([short, disabled, long]) == 45.0
