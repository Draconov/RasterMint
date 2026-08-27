import numpy as np
from PIL import Image

from rastermint.core.effect_schema import EFFECT_DEFINITIONS, effect_categories, new_effect
from rastermint.core.effect_stack import apply_effect_stack


def _test_pattern() -> Image.Image:
    arr = np.zeros((24, 32, 3), dtype=np.uint8)
    arr[:, :11] = (255, 0, 0)
    arr[:, 11:21] = (0, 255, 0)
    arr[:, 21:] = (0, 0, 255)
    return Image.fromarray(arr, "RGB")


def test_display_effects_category_contains_vhs_layers():
    category = next(row for row in effect_categories() if row["name"] == "Display Effects")
    expected = {
        "Display Persistence",
        "Chroma Bleed",
        "Tracking Error",
        "Tape Dropout",
        "Temporal Jitter",
        "Head Switching Noise",
    }
    assert expected <= set(category["effects"])
    assert EFFECT_DEFINITIONS["Chroma Bleed"]["params"]["bleed"]["pixel_scaled"] is True
    assert EFFECT_DEFINITIONS["Tracking Error"]["params"]["band_height"]["pixel_scaled"] is True


def test_chroma_bleed_spreads_colour_horizontally_without_resizing():
    image = _test_pattern()
    effect = new_effect("Chroma Bleed")
    effect["params"].update(bleed=5.0, delay=2, strength=1.0)
    out = np.asarray(apply_effect_stack(image, [effect], ["#000000", "#FFFFFF"]))
    src = np.asarray(image)
    assert out.shape == src.shape
    seam_column = 11
    assert not np.array_equal(out[:, seam_column - 1], src[:, seam_column - 1])


def test_temporal_jitter_changes_with_time_and_tracking_error_preserves_size():
    image = _test_pattern()
    jitter = new_effect("Temporal Jitter")
    jitter["params"].update(x=3.0, y=2.0, speed=8.0, seed=7)
    frame_0 = np.asarray(apply_effect_stack(image, [jitter], ["#000000", "#FFFFFF"], frame_time=0.0, frame_index=0))
    frame_1 = np.asarray(apply_effect_stack(image, [jitter], ["#000000", "#FFFFFF"], frame_time=1 / 15, frame_index=2))
    assert not np.array_equal(frame_0, frame_1)

    tracking = new_effect("Tracking Error")
    tracking["params"].update(amount=6, band_height=3, instability=0.9, speed=4.0, seed=4)
    tracked = apply_effect_stack(image, [tracking], ["#000000", "#FFFFFF"], frame_time=1 / 30, frame_index=1)
    assert tracked.size == image.size


def test_tape_dropout_and_head_switching_noise_modify_expected_regions():
    image = Image.new("RGB", (48, 36), (120, 120, 120))

    dropout = new_effect("Tape Dropout")
    dropout["params"].update(amount=1.0, length=20, thickness=3, strength=1.0, seed=9)
    dropped = np.asarray(apply_effect_stack(image, [dropout], ["#000000", "#FFFFFF"], frame_time=0.0, frame_index=0))
    assert not np.array_equal(dropped, np.asarray(image))

    head = new_effect("Head Switching Noise")
    head["params"].update(height=10, shift=16, noise=1.0, strength=1.0, seed=3)
    headed = np.asarray(apply_effect_stack(image, [head], ["#000000", "#FFFFFF"], frame_time=1 / 30, frame_index=1))
    original = np.asarray(image)
    top_diff = np.abs(headed[:20].astype(np.int16) - original[:20].astype(np.int16)).sum()
    bottom_diff = np.abs(headed[-10:].astype(np.int16) - original[-10:].astype(np.int16)).sum()
    assert bottom_diff > top_diff
