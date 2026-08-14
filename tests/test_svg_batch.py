# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from PIL import Image

from rastermint.core.batch import process_batch
from rastermint.core.effect_stack import default_effect_stack
from rastermint.core.settings import ProcessingSettings
from rastermint.core.svg_export import image_to_svg


def test_svg_export_contains_dimensions_and_colors():
    image = Image.new("RGB", (3, 2), "#123456")
    svg = image_to_svg(image)
    assert 'width="3"' in svg
    assert 'height="2"' in svg
    assert "#123456" in svg.upper()


def test_batch_processes_multiple_images(tmp_path):
    inputs = []
    for index, color in enumerate(("red", "blue")):
        path = tmp_path / f"input-{index}.png"
        Image.new("RGB", (4, 3), color).save(path)
        inputs.append(path)
    out_dir = tmp_path / "out"
    settings = ProcessingSettings(algorithm="Nearest Palette", palette=["#000000", "#FFFFFF"])
    settings.effect_stack = default_effect_stack(settings)
    written = process_batch(inputs, out_dir, settings)
    assert len(written) == 2
    assert all(path.exists() for path in written)
