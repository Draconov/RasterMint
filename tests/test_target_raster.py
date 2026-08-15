from __future__ import annotations

from PIL import Image

from rastermint.core.processor import make_preview_source, process_image, target_raster_size
from rastermint.core.settings import ProcessingSettings


def test_exact_target_raster_output():
    source = Image.new("RGB", (640, 360), "white")
    settings = ProcessingSettings(target_enabled=True, target_width=320, target_height=200, fit_mode="fit")
    result = process_image(source, settings)
    assert result.size == (320, 200)


def test_crop_and_rotation_change_implicit_raster_size():
    settings = ProcessingSettings(crop_left=0.1, crop_right=0.1, rotation=90)
    assert target_raster_size((100, 50), settings) == (50, 80)


def test_preview_source_respects_exact_raster_but_caps_budget():
    source = Image.new("RGB", (1920, 1080), "white")
    settings = ProcessingSettings(target_enabled=True, target_width=640, target_height=480)
    preview = make_preview_source(source, max_side=320, settings=settings)
    assert preview.size == (320, 240)


def test_processed_raster_size_accounts_for_pixel_aspect_layer():
    from rastermint.core.effect_stack import new_effect
    from rastermint.core.processor import processed_raster_size

    settings = ProcessingSettings(target_enabled=True, target_width=100, target_height=80)
    layer = new_effect("Pixel Aspect Ratio")
    layer["params"]["x"] = 1.5
    layer["params"]["y"] = 1.0
    settings.effect_stack = [layer]
    assert processed_raster_size((640, 480), settings) == (150, 80)
