from PIL import Image

from rastermint.core.processor import make_preview_source, process_image
from rastermint.core.settings import ProcessingSettings


def test_processor_preserves_output_size_with_pixelation():
    img = Image.new("RGB", (31, 19), (120, 150, 200))
    settings = ProcessingSettings(pixel_size=4, algorithm="Atkinson")
    out = process_image(img, settings)
    assert out.size == img.size
    assert out.mode == "RGB"


def test_preview_is_bounded():
    img = Image.new("RGB", (2000, 1000), "white")
    preview = make_preview_source(img, max_side=500)
    assert max(preview.size) <= 500
