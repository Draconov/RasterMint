# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import pytest
from PIL import Image

from rastermint.core.effect_stack import default_effect_stack
from rastermint.core.media import export_image_animation, probe_video, video_support_available
from rastermint.core.settings import ProcessingSettings


@pytest.mark.skipif(not video_support_available(), reason="FFmpeg is unavailable")
def test_still_animation_exports_valid_mp4_and_gif(tmp_path):
    image = Image.new("RGB", (16, 12), (100, 130, 190))
    settings = ProcessingSettings(animation_duration=0.5, animation_fps=4)
    settings.effect_stack = default_effect_stack(settings)

    mp4 = export_image_animation(image, settings, tmp_path / "animation.mp4")
    info = probe_video(mp4)
    assert info.width == 16
    assert info.height == 12
    assert info.frames >= 2

    gif = export_image_animation(image, settings, tmp_path / "animation.gif")
    assert gif.exists()
    assert gif.stat().st_size > 0


@pytest.mark.skipif(not video_support_available(), reason="FFmpeg is unavailable")
def test_mp4_pads_odd_dimensions_for_yuv420p(tmp_path):
    image = Image.new("RGB", (15, 11), (20, 40, 60))
    settings = ProcessingSettings(animation_duration=0.25, animation_fps=4)
    settings.effect_stack = default_effect_stack(settings)

    mp4 = export_image_animation(image, settings, tmp_path / "odd.mp4")
    info = probe_video(mp4)
    assert info.width == 16
    assert info.height == 12
