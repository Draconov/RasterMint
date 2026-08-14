# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

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
