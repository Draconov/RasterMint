from __future__ import annotations

import numpy as np
from PIL import Image

from rastermint.core.effect_stack import EFFECT_DEFINITIONS, apply_effect_stack, new_effect


def _image_with_bright_center() -> Image.Image:
    arr = np.full((25, 25, 3), 18, dtype=np.uint8)
    arr[12, 12] = (255, 255, 255)
    return Image.fromarray(arr, "RGB")


def test_dither_glow_is_registered_and_animatable():
    params = EFFECT_DEFINITIONS["Dither Glow"]["params"]
    assert params["threshold"]["animatable"] is True
    assert params["softness"]["animatable"] is True
    assert params["radius"]["animatable"] is True
    assert params["spread"]["animatable"] is True
    assert params["intensity"]["animatable"] is True
    assert params["blend"]["options"] == ["Screen", "Add"]


def test_dither_glow_zero_intensity_is_identity():
    image = _image_with_bright_center()
    effect = new_effect("Dither Glow")
    effect["params"]["intensity"] = 0.0
    result = apply_effect_stack(image, [effect], ["#000000", "#FFFFFF"])
    assert np.array_equal(np.asarray(image), np.asarray(result))


def test_dither_glow_spreads_bright_highlight_to_neighbors():
    image = _image_with_bright_center()
    effect = new_effect("Dither Glow")
    effect["params"].update(threshold=0.7, softness=0.05, radius=4.0, spread=1, intensity=1.6, blend="Screen")
    result = np.asarray(apply_effect_stack(image, [effect], ["#000000", "#FFFFFF"]))
    source = np.asarray(image)
    assert int(result[12, 10, 0]) > int(source[12, 10, 0])
    assert int(result[0, 0, 0]) < int(result[12, 10, 0])


def test_dither_glow_custom_tint_biases_colour_channels():
    image = _image_with_bright_center()
    effect = new_effect("Dither Glow")
    effect["params"].update(
        threshold=0.7, softness=0.05, radius=4.0, spread=0, intensity=1.8,
        glow_color_mode="Custom Tint", glow_color="#00FFFF", preserve_core=True,
    )
    result = np.asarray(apply_effect_stack(image, [effect], ["#000000", "#FFFFFF"]))
    assert int(result[12, 10, 1]) >= int(result[12, 10, 0])
    assert int(result[12, 10, 2]) >= int(result[12, 10, 0])
