from __future__ import annotations

from PIL import Image

from rastermint.core.batch import process_batch
from rastermint.core.effect_stack import default_effect_stack
from rastermint.core.processor import image_has_transparency, prepare_transparency_mask
from rastermint.core.settings import ProcessingSettings
from rastermint.core.svg_export import image_to_svg


def _settings() -> ProcessingSettings:
    settings = ProcessingSettings(
        algorithm="Nearest Palette",
        palette=["#000000", "#FFFFFF"],
    )
    settings.effect_stack = default_effect_stack(settings)
    return settings


def test_image_has_transparency_only_when_alpha_is_non_opaque():
    opaque = Image.new("RGBA", (2, 2), (10, 20, 30, 255))
    transparent = opaque.copy()
    transparent.putpixel((1, 1), (10, 20, 30, 0))
    assert not image_has_transparency(opaque)
    assert image_has_transparency(transparent)


def test_transparency_mask_follows_source_flip():
    image = Image.new("RGBA", (4, 2), (120, 80, 40, 0))
    for y in range(2):
        image.putpixel((0, y), (120, 80, 40, 255))
    settings = _settings()
    settings.flip_horizontal = True

    mask = prepare_transparency_mask(image, settings)

    assert mask is not None
    assert mask.size == image.size
    assert mask.getpixel((0, 0)) == 0
    assert mask.getpixel((3, 0)) == 255


def test_batch_preserves_source_alpha_by_default(tmp_path):
    source_path = tmp_path / "alpha.png"
    source = Image.new("RGBA", (4, 3), (80, 120, 160, 0))
    alpha_values = [0, 64, 128, 255, 255, 128, 64, 0, 0, 255, 255, 0]
    source.putalpha(Image.new("L", source.size))
    source.getchannel("A").putdata(alpha_values)
    # putdata on getchannel() does not write back, so build the final alpha once.
    alpha = Image.new("L", source.size)
    alpha.putdata(alpha_values)
    source.putalpha(alpha)
    source.save(source_path)

    written = process_batch([source_path], tmp_path / "out", _settings())

    with Image.open(written[0]) as exported:
        exported_alpha = list(exported.convert("RGBA").getchannel("A").tobytes())
    assert exported_alpha == alpha_values


def test_batch_can_flatten_transparency_when_disabled(tmp_path):
    source_path = tmp_path / "alpha.png"
    source = Image.new("RGBA", (3, 2), (80, 120, 160, 255))
    source.putpixel((0, 0), (80, 120, 160, 0))
    source.save(source_path)

    written = process_batch(
        [source_path],
        tmp_path / "out",
        _settings(),
        preserve_transparency=False,
    )

    with Image.open(written[0]) as exported:
        assert set(exported.convert("RGBA").getchannel("A").tobytes()) == {255}


def test_svg_keeps_partial_alpha_and_omits_fully_transparent_pixels():
    image = Image.new("RGBA", (2, 1))
    image.putpixel((0, 0), (255, 0, 0, 0))
    image.putpixel((1, 0), (0, 255, 0, 128))

    svg = image_to_svg(image)

    assert "#FF0000" not in svg.upper()
    assert "#00FF00" in svg.upper()
    assert 'fill-opacity="0.502"' in svg


def test_export_dialogs_expose_transparency_toggle():
    export_qml = open("src/rastermint/qml/ExportImageDialog.qml", encoding="utf-8").read()
    batch_qml = open("src/rastermint/qml/BatchExportDialog.qml", encoding="utf-8").read()
    assert "Preserve source transparency" in export_qml
    assert '"preserveTransparency"' in export_qml
    assert "Preserve source transparency" in batch_qml
    assert "preserveTransparency" in batch_qml


def test_application_uses_export_backend_layer():
    app_py = open("src/rastermint/app.py", encoding="utf-8").read()
    assert "from rastermint.qmlui.export_backend import RasterMintBackend" in app_py
