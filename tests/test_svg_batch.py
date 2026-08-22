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


def test_batch_restores_each_source_size_before_export_scaling(tmp_path):
    source_path = tmp_path / "source.png"
    Image.new("RGB", (12, 8), "red").save(source_path)
    settings = ProcessingSettings(
        algorithm="Nearest Palette",
        palette=["#000000", "#FFFFFF"],
        target_enabled=True,
        target_width=3,
        target_height=2,
    )
    settings.effect_stack = default_effect_stack(settings)

    written = process_batch(
        [source_path],
        tmp_path / "out",
        settings,
        scale_percent=200,
        resampling="Bicubic",
    )

    with Image.open(written[0]) as exported:
        assert exported.size == (24, 16)


def test_batch_accepts_export_dialog_resampling_names(tmp_path):
    source_path = tmp_path / "source.png"
    Image.new("RGB", (5, 4), "blue").save(source_path)
    settings = ProcessingSettings(algorithm="Nearest Palette", palette=["#000000", "#FFFFFF"])
    settings.effect_stack = default_effect_stack(settings)

    for name in ("Nearest (pixel-perfect)", "Bilinear", "Bicubic", "Lanczos"):
        written = process_batch(
            [source_path],
            tmp_path / name.replace(" ", "-"),
            settings,
            resampling=name,
        )
        with Image.open(written[0]) as exported:
            assert exported.size == (5, 4)
