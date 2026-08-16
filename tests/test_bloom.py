import numpy as np
from PIL import Image

from rastermint.core.effect_stack import EFFECT_DEFINITIONS, apply_effect_stack, new_effect


def _image_with_bright_center() -> Image.Image:
    arr = np.full((25, 25, 3), 20, dtype=np.uint8)
    arr[12, 12] = (255, 255, 255)
    return Image.fromarray(arr, "RGB")


def test_bloom_is_registered_and_animatable():
    params = EFFECT_DEFINITIONS["Bloom"]["params"]
    assert params["threshold"]["animatable"] is True
    assert params["soft_knee"]["animatable"] is True
    assert params["radius"]["animatable"] is True
    assert params["intensity"]["animatable"] is True
    assert params["blend"]["options"] == ["Screen", "Add"]


def test_bloom_zero_intensity_is_identity():
    image = _image_with_bright_center()
    bloom = new_effect("Bloom")
    bloom["params"]["intensity"] = 0.0
    result = apply_effect_stack(image, [bloom], ["#000000", "#FFFFFF"])
    assert np.array_equal(np.asarray(image), np.asarray(result))


def test_bloom_spreads_bright_highlight_to_neighbors():
    image = _image_with_bright_center()
    bloom = new_effect("Bloom")
    bloom["params"].update(threshold=0.7, soft_knee=0.1, radius=4.0, intensity=1.5, blend="Screen")
    result = np.asarray(apply_effect_stack(image, [bloom], ["#000000", "#FFFFFF"]))
    source = np.asarray(image)
    # A nearby dark pixel becomes brighter due to the blurred highlight.
    assert int(result[12, 10, 0]) > int(source[12, 10, 0])
    # A distant corner should remain substantially darker than the bloom area.
    assert int(result[0, 0, 0]) < int(result[12, 10, 0])


def test_bloom_threshold_excludes_dim_source():
    arr = np.full((21, 21, 3), 80, dtype=np.uint8)
    image = Image.fromarray(arr, "RGB")
    bloom = new_effect("Bloom")
    bloom["params"].update(threshold=0.9, soft_knee=0.0, radius=6.0, intensity=2.0)
    result = apply_effect_stack(image, [bloom], ["#000000", "#FFFFFF"])
    assert np.array_equal(np.asarray(image), np.asarray(result))
