from __future__ import annotations

import numpy as np
from PIL import Image

from rastermint.core.animation import settings_at_time
from rastermint.core.animation_presets import ANIMATION_PRESETS, apply_animation_preset
from rastermint.core.effect_stack import EFFECT_DEFINITIONS, animatable_targets, apply_effect_stack, default_effect_stack, new_effect
from rastermint.core.media import export_image_sequence, export_processed_video_sequence, render_image_preview_frames
from rastermint.core.settings import ProcessingSettings


def test_dither_mix_zero_is_true_clean_image_and_mix_one_changes_it():
    source = Image.fromarray(np.array([
        [[30, 60, 90], [100, 130, 160]],
        [[180, 150, 120], [240, 210, 180]],
    ], dtype=np.uint8), "RGB")
    dither = new_effect("Dither")
    dither["params"].update(algorithm="Nearest Palette", mix=0.0)
    clean = apply_effect_stack(source, [dither], ["#000000", "#FFFFFF"])
    assert np.array_equal(np.asarray(clean), np.asarray(source))

    dither["params"]["mix"] = 1.0
    processed = apply_effect_stack(source, [dither], ["#000000", "#FFFFFF"])
    assert not np.array_equal(np.asarray(processed), np.asarray(source))


def test_temporal_pattern_changes_over_time_but_is_repeatable():
    source = Image.new("RGB", (20, 12), (120, 130, 140))
    effect = new_effect("Temporal Pattern")
    effect["params"].update(pattern="Wave X", amount=0.6, speed=1.0, scale=6.0, phase=0.0)
    a = apply_effect_stack(source, [effect], ["#000000", "#FFFFFF"], frame_time=0.0, frame_index=0)
    b = apply_effect_stack(source, [effect], ["#000000", "#FFFFFF"], frame_time=0.25, frame_index=3)
    a2 = apply_effect_stack(source, [effect], ["#000000", "#FFFFFF"], frame_time=0.0, frame_index=0)
    assert not np.array_equal(np.asarray(a), np.asarray(b))
    assert np.array_equal(np.asarray(a), np.asarray(a2))


def test_numeric_effect_parameters_are_animatable_except_seed():
    stack = [new_effect("Local Contrast"), new_effect("Median Denoise"), new_effect("Databend"), new_effect("Dither")]
    targets = {target for target, _label, _value in animatable_targets(stack)}
    by_kind = {step["kind"]: step for step in stack}
    assert f"effect:{by_kind['Local Contrast']['id']}:threshold" in targets
    assert f"effect:{by_kind['Median Denoise']['id']}:radius" in targets
    assert f"effect:{by_kind['Databend']['id']}:quality" in targets
    assert f"effect:{by_kind['Dither']['id']}:mix" in targets
    assert f"effect:{by_kind['Databend']['id']}:seed" not in targets


def test_sequential_tracks_on_same_parameter_do_not_override_early_segment():
    settings = ProcessingSettings(animation_duration=4.0)
    settings.effect_stack = default_effect_stack(settings)
    dither = next(step for step in settings.effect_stack if step["kind"] == "Dither")
    target = f"effect:{dither['id']}:mix"
    settings.animation_tracks = [
        {"target": target, "from": 0.0, "to": 1.0, "start": 0.0, "end": 2.0, "easing": "Linear", "enabled": True},
        {"target": target, "from": 1.0, "to": 0.0, "start": 2.0, "end": 4.0, "easing": "Linear", "enabled": True},
    ]
    at_one = settings_at_time(settings, 1.0)
    at_three = settings_at_time(settings, 3.0)
    d1 = next(step for step in at_one.effect_stack if step["id"] == dither["id"])
    d3 = next(step for step in at_three.effect_stack if step["id"] == dither["id"])
    assert d1["params"]["mix"] == 0.5
    assert d3["params"]["mix"] == 0.5


def test_animation_presets_create_expected_effects_and_tracks():
    ids = {preset.id for preset in ANIMATION_PRESETS}
    assert {"dither-in", "dither-out", "dither-in-out", "temporal-wave"} <= ids

    settings = ProcessingSettings(animation_duration=2.0)
    settings.effect_stack = default_effect_stack(settings)
    animated = apply_animation_preset(settings, "dither-in-out")
    assert len(animated.animation_tracks) == 2
    assert all(track["target"].endswith(":mix") for track in animated.animation_tracks)

    wave = apply_animation_preset(settings, "temporal-wave")
    assert any(step["kind"] == "Temporal Pattern" for step in wave.effect_stack)
    assert len(wave.animation_tracks) == 1


def test_rendered_preview_and_png_sequence(tmp_path):
    image = Image.new("RGB", (24, 16), (100, 140, 180))
    settings = ProcessingSettings(animation_duration=0.5, animation_fps=4)
    settings.effect_stack = default_effect_stack(settings)
    frames, times, fps = render_image_preview_frames(image, settings, max_side=32)
    assert len(frames) == 2
    assert len(times) == 2
    assert fps == 4
    assert all(frame.width <= 32 and frame.height <= 32 for frame in frames)

    paths = export_image_sequence(image, settings, tmp_path / "frames", prefix="mint")
    assert len(paths) == 2
    assert paths[0].name == "mint_0001.png"
    assert all(path.exists() for path in paths)


def test_gif_png_sequence_export(tmp_path):
    source = tmp_path / "source.gif"
    a = Image.new("RGB", (8, 8), (255, 0, 0))
    b = Image.new("RGB", (8, 8), (0, 255, 0))
    a.save(source, save_all=True, append_images=[b], duration=[80, 120], loop=0)
    settings = ProcessingSettings()
    settings.effect_stack = default_effect_stack(settings)
    paths = export_processed_video_sequence(source, settings, tmp_path / "gif-frames", prefix="gif")
    assert len(paths) == 2
    assert all(path.exists() for path in paths)
