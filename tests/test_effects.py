# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import numpy as np
from PIL import Image

from rastermint.core.effects import apply_filters
from rastermint.core.settings import ProcessingSettings


def test_grayscale_filter_keeps_rgb_mode_and_equal_channels():
    image = Image.new("RGB", (2, 1))
    image.putdata([(255, 0, 0), (0, 255, 80)])
    out = apply_filters(image, ProcessingSettings(grayscale=True))
    data = np.asarray(out)
    assert out.mode == "RGB"
    assert np.array_equal(data[:, :, 0], data[:, :, 1])
    assert np.array_equal(data[:, :, 1], data[:, :, 2])


def test_invert_filter_is_exact():
    image = Image.new("RGB", (1, 1), (10, 20, 30))
    out = apply_filters(image, ProcessingSettings(invert=True))
    assert out.getpixel((0, 0)) == (245, 235, 225)


def test_blur_and_sharpen_filters_preserve_size_and_mode():
    image = Image.new("RGB", (9, 7), "black")
    image.putpixel((4, 3), (255, 255, 255))
    settings = ProcessingSettings(blur_radius=1.5, sharpen=1.8)
    out = apply_filters(image, settings)
    assert out.size == image.size
    assert out.mode == "RGB"
