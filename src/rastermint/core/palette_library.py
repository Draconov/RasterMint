# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from dataclasses import dataclass
import colorsys
import math
from typing import Iterable

from .palette import hex_to_rgb, rgb_to_hex


@dataclass(frozen=True)
class PaletteRecord:
    id: str
    name: str
    category: str
    colors: tuple[str, ...]
    description: str = ""
    source: str = ""


def _record(id: str, name: str, category: str, colors: Iterable[str], description: str = "", source: str = "") -> PaletteRecord:
    return PaletteRecord(id, name, category, tuple(c.upper() for c in colors), description, source)


def _mono_ramp(tint: str, count: int) -> tuple[str, ...]:
    tr, tg, tb = hex_to_rgb(tint)
    values: list[str] = []
    for i in range(count):
        level = i / max(1, count - 1)
        # Phosphor-like ramps retain a very dark tinted black rather than pure black.
        r = round(tr * (0.05 + 0.95 * level))
        g = round(tg * (0.05 + 0.95 * level))
        b = round(tb * (0.05 + 0.95 * level))
        values.append(rgb_to_hex((r, g, b)))
    return tuple(values)


CGA_RGBI = (
    "#000000", "#0000AA", "#00AA00", "#00AAAA", "#AA0000", "#AA00AA", "#AA5500", "#AAAAAA",
    "#555555", "#5555FF", "#55FF55", "#55FFFF", "#FF5555", "#FF55FF", "#FFFF55", "#FFFFFF",
)

ZX_15 = (
    "#000000", "#0000D7", "#D70000", "#D700D7", "#00D700", "#00D7D7", "#D7D700", "#D7D7D7",
    "#0000FF", "#FF0000", "#FF00FF", "#00FF00", "#00FFFF", "#FFFF00", "#FFFFFF",
)

C64_16 = (
    "#000000", "#FFFFFF", "#813338", "#75CEC8", "#8E3C97", "#56AC4D", "#2E2C9B", "#EDF171",
    "#8E5029", "#553800", "#C46C71", "#4A4A4A", "#7B7B7B", "#A9FF9F", "#706DEB", "#B2B2B2",
)

MSX_15 = (
    "#000000", "#3EB849", "#74D07D", "#5955E0", "#8076F1", "#B95E51", "#65DBEF", "#DB6559",
    "#FF897D", "#CCC35E", "#DED087", "#3AA241", "#B766B5", "#CCCCCC", "#FFFFFF",
)

BBC_8 = ("#000000", "#FF0000", "#00FF00", "#FFFF00", "#0000FF", "#FF00FF", "#00FFFF", "#FFFFFF")

APPLE_II_6 = ("#000000", "#FFFFFF", "#D043E8", "#2CE446", "#2D6CFF", "#FF6A3C")

TI99_16 = (
    "#000000", "#000000", "#21C842", "#5EDC78", "#5455ED", "#7D76FC", "#D4524D", "#42EBF5",
    "#FC5554", "#FF7978", "#D4C154", "#E6CE80", "#21B03B", "#C95BBA", "#CCCCCC", "#FFFFFF",
)

PICO8 = (
    "#000000", "#1D2B53", "#7E2553", "#008751", "#AB5236", "#5F574F", "#C2C3C7", "#FFF1E8",
    "#FF004D", "#FFA300", "#FFEC27", "#00E436", "#29ADFF", "#83769C", "#FF77A8", "#FFCCAA",
)

TIC80 = (
    "#1A1C2C", "#5D275D", "#B13E53", "#EF7D57", "#FFCD75", "#A7F070", "#38B764", "#257179",
    "#29366F", "#3B5DC9", "#41A6F6", "#73EFF7", "#F4F4F4", "#94B0C2", "#566C86", "#333C57",
)

# Historical hardware often did not have one universal game palette. Entries marked
# "representative" or "approximation" are intentionally creative subsets rather
# than claims that every title on that machine used these exact RGB values.
PALETTE_LIBRARY: tuple[PaletteRecord, ...] = (
    _record("ink", "Ink", "RasterMint", ("#0B1020", "#F3F7FF"), "High-contrast two-color palette."),
    _record("graphite-4", "Graphite 4", "RasterMint", ("#101217", "#4A4F59", "#A9AFB9", "#F4F6F8"), "Neutral four-step grayscale."),
    _record("forest-4", "Forest 4", "RasterMint", ("#0D1B16", "#244D3D", "#6B9B64", "#D6E7B0"), "Dark organic green ramp."),
    _record("amber-4", "Amber 4", "RasterMint", ("#1B1209", "#70431D", "#D08A2E", "#FFE0A1"), "Warm amber ramp."),
    _record("ocean-6", "Ocean 6", "RasterMint", ("#08131D", "#12344A", "#1E6070", "#3F8E95", "#88BFB7", "#E2EFE7"), "Cool six-color ramp."),
    _record("arcade-8", "Arcade 8", "RasterMint", ("#151515", "#E83B3B", "#FF8C42", "#F4E04D", "#57C84D", "#36A2AE", "#4D63D6", "#E8E8E8"), "Small saturated arcade-style set."),

    _record("gb-dmg", "Game Boy DMG", "Nintendo", ("#0F380F", "#306230", "#8BAC0F", "#9BBC0F"), "Four-shade green LCD approximation used for the original Game Boy look."),
    _record("gb-pocket", "Game Boy Pocket", "Nintendo", ("#111111", "#555555", "#AAAAAA", "#E8E8E8"), "Neutral grayscale approximation for the later reflective LCD."),
    _record("gb-light", "Game Boy Light", "Nintendo", ("#082B28", "#145C4C", "#5FAF7A", "#C5F0A4"), "Backlit handheld-inspired green/cyan four-shade approximation."),
    _record("virtual-boy", "Virtual Boy", "Nintendo", ("#000000", "#550000", "#AA0000", "#FF0000"), "Four-step red monochrome look."),
    _record("nes-reference", "NES Reference 16", "Nintendo", ("#000000", "#FCFCFC", "#F8B800", "#F87858", "#B80000", "#D800CC", "#6844FC", "#0058F8", "#0078F8", "#00B8F8", "#00B800", "#58D854", "#B8F818", "#F8D878", "#F878F8", "#A4E4FC"), "Representative subset of commonly reproduced NES/Famicom output colors; not a full master palette."),
    _record("snes-reference", "SNES Reference 16", "Nintendo", ("#000000", "#FFFFFF", "#7B2D26", "#D95763", "#F2A65A", "#F4D35E", "#70C1B3", "#247BA0", "#1B4965", "#5C4B99", "#9B5DE5", "#F15BB5", "#00BBF9", "#00F5D4", "#9BDEAC", "#C7F9CC"), "Creative 16-color subset for SNES-style artwork; the hardware itself used a much larger RGB555 color space."),

    _record("sms-reference", "Master System Reference 16", "Sega", ("#000000", "#555555", "#AAAAAA", "#FFFFFF", "#0000AA", "#0055FF", "#00AA00", "#55FF55", "#00AAAA", "#55FFFF", "#AA0000", "#FF5555", "#AA00AA", "#FF55FF", "#AAAA00", "#FFFF55"), "Representative subset of the Master System 6-bit RGB color space."),
    _record("game-gear-reference", "Game Gear Reference 16", "Sega", ("#000000", "#202040", "#405080", "#6080C0", "#90B0E0", "#E0F0FF", "#204020", "#408040", "#70B050", "#B0D070", "#704020", "#B07040", "#D0A060", "#702050", "#B05090", "#F090C0"), "LCD-oriented representative subset; Game Gear hardware supported a larger RGB444 space."),
    _record("genesis-reference", "Mega Drive / Genesis 16", "Sega", ("#000000", "#222222", "#555555", "#AAAAAA", "#FFFFFF", "#002266", "#0044AA", "#2288DD", "#006622", "#22AA44", "#88CC44", "#662200", "#AA4422", "#DD8844", "#662266", "#BB55AA"), "Representative 16-color subset for RGB333-era Sega artwork."),

    _record("c64-16", "Commodore 64", "Commodore", C64_16, "Common modern RGB approximation of the C64 fixed 16-color set."),
    _record("vic20-16", "VIC-20", "Commodore", ("#000000", "#FFFFFF", "#A83D34", "#6ABFC6", "#A85FB4", "#50A04F", "#4E4A9E", "#D5D578", "#A76B2D", "#6B4B1F", "#E38A83", "#887ECB", "#B7B7B7", "#9EE493", "#8A85D1", "#D9D9D9"), "Common RGB approximation of the VIC family palette."),
    _record("plus4-16", "Commodore Plus/4", "Commodore", ("#000000", "#FFFFFF", "#681010", "#70A4B2", "#6F3D86", "#588D43", "#352879", "#B8C76F", "#6F4F25", "#433900", "#9A6759", "#444444", "#6C6C6C", "#9AD284", "#6C5EB5", "#959595"), "Representative 16-color subset of the TED palette."),
    _record("amiga-wb13", "Amiga Workbench 1.3", "Commodore", ("#0055AA", "#FFFFFF", "#000000", "#FF8800"), "Classic four-color Workbench-era UI look."),
    _record("amiga-wb20", "Amiga Workbench 2.x", "Commodore", ("#AAAAAA", "#000000", "#FFFFFF", "#6688BB", "#FF9900", "#335577", "#777777", "#CCCCCC"), "Representative Workbench 2.x desktop colors."),
    _record("amiga-wb31", "Amiga Workbench 3.x", "Commodore", ("#959595", "#000000", "#FFFFFF", "#3B67A2", "#FF8A00", "#5A5A5A", "#BDBDBD", "#D6D6D6"), "Representative Workbench 3.x desktop colors."),

    _record("zx-normal", "ZX Spectrum Normal", "Sinclair", ZX_15[:8], "Normal-brightness ZX Spectrum colors."),
    _record("zx-bright", "ZX Spectrum Bright", "Sinclair", ("#000000",) + ZX_15[8:], "Bright ZX Spectrum colors plus black."),
    _record("zx-full", "ZX Spectrum 15", "Sinclair", ZX_15, "Combined normal and bright Spectrum colors; black is shared."),

    _record("amstrad-cpc-27", "Amstrad CPC 27", "Amstrad", tuple(rgb_to_hex((r, g, b)) for r in (0, 128, 255) for g in (0, 128, 255) for b in (0, 128, 255)), "27-color RGB cube representation of the CPC hardware palette."),
    _record("msx-15", "MSX 15", "MSX", MSX_15, "Common RGB approximation of the MSX/TMS9918 fixed color set, excluding transparent."),
    _record("ti99-16", "TI-99/4A", "Texas Instruments", TI99_16, "Common RGB approximation of the TMS9918 color set."),

    _record("cga-p0-low", "CGA Palette 0 Low", "IBM PC", ("#000000", "#00AA00", "#AA0000", "#AA5500"), "CGA 320×200 palette 0 in low intensity."),
    _record("cga-p0-high", "CGA Palette 0 High", "IBM PC", ("#000000", "#55FF55", "#FF5555", "#FFFF55"), "CGA 320×200 palette 0 in high intensity."),
    _record("cga-p1-low", "CGA Palette 1 Low", "IBM PC", ("#000000", "#00AAAA", "#AA00AA", "#AAAAAA"), "CGA 320×200 palette 1 in low intensity."),
    _record("cga-p1-high", "CGA Palette 1 High", "IBM PC", ("#000000", "#55FFFF", "#FF55FF", "#FFFFFF"), "CGA 320×200 palette 1 in high intensity."),
    _record("rgbi-16", "IBM RGBI 16", "IBM PC", CGA_RGBI, "Standard 16-color RGBI set associated with PC text/EGA-style graphics."),
    _record("ega-16", "EGA 16", "IBM PC", CGA_RGBI, "Common 16-color EGA/RGBI subset."),
    _record("vga-16", "VGA Default 16", "IBM PC", CGA_RGBI, "Classic VGA-compatible default 16-color set."),
    _record("vga-gray16", "VGA Grayscale 16", "IBM PC", tuple(rgb_to_hex((i, i, i)) for i in range(0, 256, 17)), "Sixteen-step grayscale useful for VGA-era monochrome looks."),

    _record("mda-green-2", "MDA Green 2", "Monochrome Monitor", _mono_ramp("#66FF66", 2), "Two-level green phosphor terminal look."),
    _record("mda-green-4", "MDA Green 4", "Monochrome Monitor", _mono_ramp("#66FF66", 4), "Four-level green phosphor terminal ramp."),
    _record("mda-green-8", "MDA Green 8", "Monochrome Monitor", _mono_ramp("#66FF66", 8), "Eight-level green phosphor terminal ramp."),
    _record("amber-2", "Amber Monitor 2", "Monochrome Monitor", _mono_ramp("#FFB13B", 2), "Two-level amber phosphor look."),
    _record("amber-monitor-4", "Amber Monitor 4", "Monochrome Monitor", _mono_ramp("#FFB13B", 4), "Four-level amber phosphor ramp."),
    _record("amber-8", "Amber Monitor 8", "Monochrome Monitor", _mono_ramp("#FFB13B", 8), "Eight-level amber phosphor ramp."),
    _record("white-2", "White Phosphor 2", "Monochrome Monitor", _mono_ramp("#F4F7EE", 2), "Two-level white phosphor look."),
    _record("white-4", "White Phosphor 4", "Monochrome Monitor", _mono_ramp("#F4F7EE", 4), "Four-level white phosphor ramp."),
    _record("white-8", "White Phosphor 8", "Monochrome Monitor", _mono_ramp("#F4F7EE", 8), "Eight-level white phosphor ramp."),

    _record("apple2-hgr", "Apple II HGR Approx.", "Apple", APPLE_II_6, "Creative approximation of common NTSC artifact colors."),
    _record("mac-1bit", "Classic Macintosh 1-bit", "Apple", ("#000000", "#FFFFFF"), "Black-and-white compact Macintosh bitmap look."),
    _record("mac-gray4", "Macintosh Gray 4", "Apple", ("#000000", "#555555", "#AAAAAA", "#FFFFFF"), "Four-level grayscale Mac-style palette."),
    _record("mac-system16", "Macintosh System 16", "Apple", ("#FFFFFF", "#FCF305", "#FF6402", "#DD0806", "#F20884", "#4600A5", "#0000D4", "#02ABEA", "#1FB714", "#006411", "#562C05", "#90713A", "#C0C0C0", "#808080", "#404040", "#000000"), "Representative classic Macintosh 16-color desktop palette."),

    _record("atari-st16", "Atari ST 16", "Atari", ("#000000", "#0000AA", "#00AA00", "#00AAAA", "#AA0000", "#AA00AA", "#AA5500", "#AAAAAA", "#555555", "#5555FF", "#55FF55", "#55FFFF", "#FF5555", "#FF55FF", "#FFFF55", "#FFFFFF"), "Representative 16-color subset from the ST's 3-bit-per-channel color space."),
    _record("atari-8bit16", "Atari 8-bit Reference 16", "Atari", ("#000000", "#444444", "#888888", "#CCCCCC", "#7C2C20", "#B45C38", "#E08C58", "#E8C078", "#2450A4", "#4C78CC", "#70A0E8", "#388438", "#58AC48", "#8CD060", "#A85898", "#D080C0"), "Representative 16-color subset of Atari 8-bit luminance/hue output."),
    _record("atari2600-16", "Atari 2600 Reference 16", "Atari", ("#000000", "#404040", "#6C6C6C", "#909090", "#B0B0B0", "#ECECEC", "#444400", "#646410", "#846830", "#A87844", "#A03030", "#C05050", "#345C98", "#5084CC", "#208030", "#40A050"), "Representative NTSC-style subset; actual console color output varies by standard and display."),

    _record("bbc-8", "BBC Micro 8", "Acorn", BBC_8, "Eight logical RGB primaries used by the BBC Micro palette model."),
    _record("teletext-8", "Teletext 8", "Broadcast", BBC_8, "Classic teletext RGB primary palette."),
    _record("oric-8", "Oric Atmos 8", "Oric", BBC_8, "Eight-color RGB-style Oric palette."),
    _record("dragon-8", "Dragon / CoCo Reference 8", "Motorola 6847", ("#000000", "#00FF00", "#FFFF00", "#0000FF", "#FF0000", "#FFFFFF", "#00FFFF", "#FF00FF"), "Representative eight-color set for 6847-era microcomputer graphics."),
    _record("coco3-16", "CoCo 3 Reference 16", "Tandy", ("#000000", "#202020", "#606060", "#A0A0A0", "#FFFFFF", "#804000", "#C06020", "#E0A040", "#800000", "#D02020", "#006000", "#20B040", "#004080", "#2080D0", "#600080", "#B040D0"), "Creative 16-color subset for CoCo 3-era RGB output."),

    _record("pc98-16", "PC-98 16", "NEC", ("#000000", "#0000AA", "#00AA00", "#00AAAA", "#AA0000", "#AA00AA", "#AAAA00", "#AAAAAA", "#555555", "#5555FF", "#55FF55", "#55FFFF", "#FF5555", "#FF55FF", "#FFFF55", "#FFFFFF"), "Representative 16-color digital RGB set used in PC-98-era graphics."),
    _record("x68000-16", "X68000 Reference 16", "Sharp", ("#000000", "#202020", "#606060", "#A0A0A0", "#FFFFFF", "#7A2030", "#C04050", "#F08090", "#205080", "#4080C0", "#80B0F0", "#206030", "#40A050", "#90D070", "#804080", "#D080D0"), "Creative representative subset; X68000 hardware supported a much larger color space."),
    _record("fmtowns-16", "FM Towns Reference 16", "Fujitsu", ("#000000", "#000080", "#008000", "#008080", "#800000", "#800080", "#808000", "#C0C0C0", "#808080", "#0000FF", "#00FF00", "#00FFFF", "#FF0000", "#FF00FF", "#FFFF00", "#FFFFFF"), "Representative 16-color PC-like subset for FM Towns-style artwork."),
    _record("sam-coupe-16", "SAM Coupé 16", "MGT", ("#000000", "#0000AA", "#AA0000", "#AA00AA", "#00AA00", "#00AAAA", "#AAAA00", "#AAAAAA", "#555555", "#5555FF", "#FF5555", "#FF55FF", "#55FF55", "#55FFFF", "#FFFF55", "#FFFFFF"), "Representative 16-color subset of the SAM Coupé palette space."),
    _record("thomson-16", "Thomson TO7/MO5 16", "Thomson", ("#000000", "#0000FF", "#FF0000", "#FF00FF", "#00FF00", "#00FFFF", "#FFFF00", "#FFFFFF", "#777777", "#000077", "#770000", "#770077", "#007700", "#007777", "#777700", "#BBBBBB"), "Representative 16-color French microcomputer palette."),

    _record("intellivision-16", "Intellivision 16", "Mattel", ("#000000", "#002DFF", "#FF3D10", "#C9C744", "#00A756", "#FAEA50", "#A7A8A8", "#FFFFFF", "#BD95FF", "#25C5FF", "#FF5B5B", "#B84C00", "#00D0A0", "#7C7C00", "#5A5A5A", "#FF9A00"), "Common RGB approximation of the Intellivision fixed color set."),
    _record("coleco-16", "ColecoVision 16", "Coleco", TI99_16, "TMS9918-based color set, closely related to TI-99/MSX video hardware."),
    _record("ngpc-gray", "Neo Geo Pocket Grayscale", "SNK", _mono_ramp("#E8E8D8", 8), "Eight-step grayscale approximation for the original monochrome Neo Geo Pocket."),
    _record("wonderswan-gray", "WonderSwan Grayscale", "Bandai", _mono_ramp("#DCDCC8", 8), "Eight-step grayscale approximation for the original WonderSwan LCD."),

    _record("pico8", "PICO-8", "Fantasy Console", PICO8, "PICO-8's fixed 16-color palette."),
    _record("tic80", "TIC-80", "Fantasy Console", TIC80, "TIC-80's default 16-color palette."),
)

PALETTE_BY_ID = {palette.id: palette for palette in PALETTE_LIBRARY}
PALETTE_BY_NAME = {palette.name: palette for palette in PALETTE_LIBRARY}


def palette_categories() -> list[str]:
    return sorted({palette.category for palette in PALETTE_LIBRARY}, key=str.casefold)


def find_palette(name_or_id: str) -> PaletteRecord | None:
    return PALETTE_BY_ID.get(name_or_id) or PALETTE_BY_NAME.get(name_or_id)


def search_palettes(query: str = "", category: str = "All") -> list[PaletteRecord]:
    query_cf = query.strip().casefold()
    result = []
    for palette in PALETTE_LIBRARY:
        if category != "All" and palette.category != category:
            continue
        haystack = f"{palette.name} {palette.category} {palette.description}".casefold()
        if query_cf and query_cf not in haystack:
            continue
        result.append(palette)
    return result


# ---- palette interpolation -------------------------------------------------

def _srgb_to_linear(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return 12.92 * value if value <= 0.0031308 else 1.055 * (value ** (1.0 / 2.4)) - 0.055


def _rgb01(color: str) -> tuple[float, float, float]:
    return tuple(v / 255.0 for v in hex_to_rgb(color))


def _hex01(rgb: Iterable[float]) -> str:
    return rgb_to_hex(round(max(0.0, min(1.0, v)) * 255.0) for v in rgb)


def _rgb_to_oklab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = math.copysign(abs(l) ** (1 / 3), l), math.copysign(abs(m) ** (1 / 3), m), math.copysign(abs(s) ** (1 / 3), s)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _oklab_to_rgb(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    L, a, b = lab
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(_linear_to_srgb(v) for v in (r, g, bb))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_hue(a: float, b: float, t: float) -> float:
    delta = ((b - a + 0.5) % 1.0) - 0.5
    return (a + delta * t) % 1.0


def interpolate_palette(start: str, end: str, count: int = 8, space: str = "OKLab") -> list[str]:
    """Generate a color ramp including both endpoints."""
    count = max(2, min(256, int(count)))
    start_rgb = _rgb01(start)
    end_rgb = _rgb01(end)
    mode = str(space or "OKLab").strip().upper().replace(" ", "")
    result: list[str] = []

    if mode in {"HSV", "HSL"}:
        if mode == "HSV":
            a = colorsys.rgb_to_hsv(*start_rgb); b = colorsys.rgb_to_hsv(*end_rgb)
            converter = colorsys.hsv_to_rgb
        else:
            # colorsys calls HSL "HLS" and orders the last two components as L,S.
            a = colorsys.rgb_to_hls(*start_rgb); b = colorsys.rgb_to_hls(*end_rgb)
            converter = colorsys.hls_to_rgb
        for i in range(count):
            t = i / (count - 1)
            values = (_lerp_hue(a[0], b[0], t), _lerp(a[1], b[1], t), _lerp(a[2], b[2], t))
            result.append(_hex01(converter(*values)))
        return result

    if mode in {"LINEARRGB", "LINEAR"}:
        a = tuple(_srgb_to_linear(c) for c in start_rgb)
        b = tuple(_srgb_to_linear(c) for c in end_rgb)
        for i in range(count):
            t = i / (count - 1)
            result.append(_hex01(_linear_to_srgb(_lerp(a[j], b[j], t)) for j in range(3)))
        return result

    if mode == "RGB":
        for i in range(count):
            t = i / (count - 1)
            result.append(_hex01(_lerp(start_rgb[j], end_rgb[j], t) for j in range(3)))
        return result

    a = _rgb_to_oklab(start_rgb)
    b = _rgb_to_oklab(end_rgb)
    for i in range(count):
        t = i / (count - 1)
        result.append(_hex01(_oklab_to_rgb(tuple(_lerp(a[j], b[j], t) for j in range(3)))))
    return result
