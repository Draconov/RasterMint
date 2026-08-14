from PIL import Image

from rastermint.core.palette import (
    BUILTIN_PALETTES,
    extract_palette,
    hex_to_rgb,
    rgb_to_hex,
)


def test_hex_roundtrip():
    assert hex_to_rgb("#12ABEF") == (0x12, 0xAB, 0xEF)
    assert rgb_to_hex((18, 171, 239)) == "#12ABEF"


def test_extract_palette_returns_requested_range():
    img = Image.new("RGB", (16, 16), "red")
    for x in range(8, 16):
        for y in range(16):
            img.putpixel((x, y), (0, 0, 255))
    colors = extract_palette(img, 4)
    assert 2 <= len(colors) <= 4


def test_builtin_palettes_have_colors():
    assert BUILTIN_PALETTES
    assert all(len(colors) >= 2 for colors in BUILTIN_PALETTES.values())
