# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

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


def test_palette_file_import_hex_gpl_and_jasc(tmp_path):
    from rastermint.core.palette import read_palette_file

    hex_file = tmp_path / "sample.hex"
    hex_file.write_text("112233\n#AABBCC\n", encoding="utf-8")
    assert read_palette_file(hex_file) == ["#112233", "#AABBCC"]

    gpl = tmp_path / "sample.gpl"
    gpl.write_text("GIMP Palette\nName: Sample\n255 0 0 Red\n0 255 0 Green\n", encoding="utf-8")
    assert read_palette_file(gpl) == ["#FF0000", "#00FF00"]

    pal = tmp_path / "sample.pal"
    pal.write_text("JASC-PAL\n0100\n2\n0 0 255\n255 255 255\n", encoding="utf-8")
    assert read_palette_file(pal) == ["#0000FF", "#FFFFFF"]


# ---- merged from test_lospec.py ----

import json

from rastermint.core.lospec import normalize_lospec_slug, palette_json_url, parse_lospec_palette


def test_lospec_slug_accepts_slug_and_full_url():
    assert normalize_lospec_slug("PICO-8") == "pico-8"
    assert normalize_lospec_slug("https://lospec.com/palette-list/greyt-bit/") == "greyt-bit"
    assert palette_json_url("greyt-bit").endswith("/greyt-bit.json")


def test_lospec_json_parser_preserves_attribution_and_colors():
    payload = json.dumps({
        "name": "Example Palette",
        "author": "Pixel Artist",
        "colors": ["000000", "abcdef", "FFFFFF"],
    })
    palette = parse_lospec_palette("example-palette", payload)
    assert palette.name == "Example Palette"
    assert palette.author == "Pixel Artist"
    assert palette.colors == ["#000000", "#ABCDEF", "#FFFFFF"]
    assert palette.source_url.endswith("/example-palette")
