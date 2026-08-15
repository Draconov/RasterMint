from rastermint.core.palette_library import (
    PALETTE_LIBRARY,
    find_palette,
    interpolate_palette,
    search_palettes,
)


def test_palette_library_has_many_unique_entries():
    assert len(PALETTE_LIBRARY) >= 50
    assert len({item.id for item in PALETTE_LIBRARY}) == len(PALETTE_LIBRARY)
    assert len({item.name for item in PALETTE_LIBRARY}) == len(PALETTE_LIBRARY)
    assert all(2 <= len(item.colors) <= 256 for item in PALETTE_LIBRARY)


def test_palette_search_and_lookup():
    assert find_palette("Game Boy DMG") is not None
    results = search_palettes("spectrum")
    assert any(item.name == "ZX Spectrum 15" for item in results)
    cga = search_palettes(category="IBM PC")
    assert any("CGA" in item.name for item in cga)


def test_interpolation_includes_endpoints_for_every_mode():
    for mode in ["OKLab", "RGB", "Linear RGB", "HSV", "HSL"]:
        colors = interpolate_palette("#102030", "#E0C080", 9, mode)
        assert len(colors) == 9
        assert colors[0] == "#102030"
        assert colors[-1] == "#E0C080"
        assert len(set(colors)) >= 5


def test_interpolation_clamps_count():
    assert len(interpolate_palette("#000000", "#FFFFFF", 1)) == 2
    assert len(interpolate_palette("#000000", "#FFFFFF", 999)) == 256
