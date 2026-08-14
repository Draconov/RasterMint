# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

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
