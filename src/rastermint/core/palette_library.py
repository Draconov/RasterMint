# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from dataclasses import dataclass
import colorsys
import json
import math
from pathlib import Path
from typing import Iterable
import warnings

from .color_utils import hex_to_rgb, rgb_to_hex
from .extensions import asset_directories


@dataclass(frozen=True)
class PaletteRecord:
    id: str
    name: str
    category: str
    colors: tuple[str, ...]
    description: str = ""
    source: str = ""


_PALETTE_ROOT = Path(__file__).resolve().parent.parent / "data" / "palettes"

# Keep the original curated base-palette order even though the bundled JSON
# filenames no longer carry numeric sequence prefixes. New base palettes that
# are not listed here are appended alphabetically after the existing set.
_BASE_PALETTE_ORDER = (
    "ink",
    "graphite-4",
    "forest-4",
    "amber-4",
    "ocean-6",
    "arcade-8",
    "rgb-8",
    "rgb-6bit-64",
    "rgb-8bit-256",
    "gb-dmg",
    "gb-pocket",
    "gb-light",
    "virtual-boy",
    "nes-reference",
    "snes-reference",
    "sms-reference",
    "game-gear-reference",
    "genesis-reference",
    "c16-reference-16",
    "c64-16",
    "vic20-16",
    "plus4-16",
    "amiga-wb13",
    "amiga-wb20",
    "amiga-wb31",
    "zx-normal",
    "zx-bright",
    "zx-full",
    "amstrad-cpc-27",
    "msx-15",
    "ti99-16",
    "cga-p0-low",
    "cga-p0-high",
    "cga-p1-low",
    "cga-p1-high",
    "rgbi-16",
    "ega-16",
    "vga-16",
    "vga-gray16",
    "windows-20",
    "mda-green-2",
    "mda-green-4",
    "mda-green-8",
    "amber-2",
    "amber-monitor-4",
    "amber-8",
    "white-2",
    "white-4",
    "white-8",
    "apple2-hgr",
    "mac-1bit",
    "mac-gray4",
    "mac-system16",
    "atari-st16",
    "atari-8bit16",
    "atari2600-16",
    "bbc-8",
    "teletext-8",
    "oric-8",
    "dragon-8",
    "coco3-16",
    "pc98-16",
    "x68000-16",
    "fmtowns-16",
    "sam-coupe-16",
    "thomson-16",
    "intellivision-16",
    "coleco-16",
    "ngpc-gray",
    "wonderswan-gray",
    "pico8",
    "tic80",
)
_BASE_PALETTE_ORDER_INDEX = {palette_id: index for index, palette_id in enumerate(_BASE_PALETTE_ORDER)}


def _normalize_palette_color(value: object) -> str:
    text = str(value or "").strip()
    # Reuse the canonical parser so bundled JSON is validated exactly like
    # imported palette colors, while storing normalized uppercase #RRGGBB.
    return rgb_to_hex(hex_to_rgb(text))


def _palette_from_payload(payload: object, path: Path) -> PaletteRecord:
    if not isinstance(payload, dict):
        raise ValueError("palette document must be a JSON object")
    if payload.get("format") != "rastermint-palette":
        raise ValueError("unsupported palette format")
    if int(payload.get("version", 0)) != 1:
        raise ValueError("unsupported palette version")

    palette_id = str(payload.get("id", "")).strip()
    name = str(payload.get("name", "")).strip()
    category = str(payload.get("category", "")).strip() or "Other"
    raw_colors = payload.get("colors")
    if not palette_id or not name:
        raise ValueError("palette id and name are required")
    if not isinstance(raw_colors, list):
        raise ValueError("palette colors must be a JSON array")

    colors = tuple(_normalize_palette_color(value) for value in raw_colors)
    if not 2 <= len(colors) <= 256:
        raise ValueError("palette must contain between 2 and 256 colors")

    return PaletteRecord(
        id=palette_id,
        name=name,
        category=category,
        colors=colors,
        description=str(payload.get("description", "")).strip(),
        source=str(payload.get("source", "")).strip(),
    )


def _load_palette_directory(directory: Path) -> list[PaletteRecord]:
    records: list[PaletteRecord] = []
    if not directory.is_dir():
        return records
    for path in sorted(directory.glob("*.json"), key=lambda item: item.name.casefold()):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            records.append(_palette_from_payload(payload, path))
        except Exception as exc:
            # A single optional bundled palette should never stop RasterMint from
            # opening. CI validates the shipped data so this is a runtime guard.
            warnings.warn(f"Skipping invalid bundled palette {path.name}: {exc}", RuntimeWarning, stacklevel=2)
    return records


def load_bundled_palettes() -> tuple[PaletteRecord, ...]:
    records: list[PaletteRecord] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()

    # Base comes first to preserve the long-standing built-in library ordering;
    # extended palettes are appended and use the exact same JSON schema.
    for folder in ("base", "extended"):
        folder_records = _load_palette_directory(_PALETTE_ROOT / folder)
        if folder == "base":
            fallback_index = len(_BASE_PALETTE_ORDER_INDEX)
            folder_records.sort(
                key=lambda record: (
                    _BASE_PALETTE_ORDER_INDEX.get(record.id, fallback_index),
                    record.name.casefold(),
                )
            )
        for record in folder_records:
            if record.id in seen_ids or record.name in seen_names:
                warnings.warn(
                    f"Skipping duplicate bundled palette {record.name!r} ({record.id!r})",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            seen_ids.add(record.id)
            seen_names.add(record.name)
            records.append(record)

    # Extension palettes use the exact same rastermint-palette v1 schema. They
    # are appended after the shipped library and cannot shadow a built-in id or
    # name, keeping saved preset references deterministic.
    for directory in asset_directories("palettes"):
        for record in _load_palette_directory(directory):
            if record.id in seen_ids or record.name in seen_names:
                continue
            seen_ids.add(record.id)
            seen_names.add(record.name)
            records.append(record)

    if not records:
        raise RuntimeError(f"No bundled palettes were found under {_PALETTE_ROOT}")
    return tuple(records)


PALETTE_LIBRARY: tuple[PaletteRecord, ...] = load_bundled_palettes()

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


def _interpolate_pair(start: str, end: str, t: float, mode: str) -> str:
    start_rgb = _rgb01(start)
    end_rgb = _rgb01(end)

    if mode in {"HSV", "HSL"}:
        if mode == "HSV":
            a = colorsys.rgb_to_hsv(*start_rgb); b = colorsys.rgb_to_hsv(*end_rgb)
            converter = colorsys.hsv_to_rgb
        else:
            # colorsys calls HSL "HLS" and orders the last two components as L,S.
            a = colorsys.rgb_to_hls(*start_rgb); b = colorsys.rgb_to_hls(*end_rgb)
            converter = colorsys.hls_to_rgb
        values = (_lerp_hue(a[0], b[0], t), _lerp(a[1], b[1], t), _lerp(a[2], b[2], t))
        return _hex01(converter(*values))

    if mode in {"LINEARRGB", "LINEAR"}:
        a = tuple(_srgb_to_linear(c) for c in start_rgb)
        b = tuple(_srgb_to_linear(c) for c in end_rgb)
        return _hex01(_linear_to_srgb(_lerp(a[j], b[j], t)) for j in range(3))

    if mode == "RGB":
        return _hex01(_lerp(start_rgb[j], end_rgb[j], t) for j in range(3))

    a = _rgb_to_oklab(start_rgb)
    b = _rgb_to_oklab(end_rgb)
    return _hex01(_oklab_to_rgb(tuple(_lerp(a[j], b[j], t) for j in range(3))))


def interpolate_palette(start: str, end: str, count: int = 8, space: str = "OKLab") -> list[str]:
    """Generate a color ramp including both endpoints."""
    return interpolate_palette_stops([start, end], count, space)


def interpolate_palette_stops(
    stops: Iterable[str],
    count: int = 8,
    space: str = "OKLab",
    positions: Iterable[float] | None = None,
) -> list[str]:
    """Generate a color ramp through multiple anchor colors.

    ``positions`` optionally supplies normalized 0..1 stop locations. When it
    is omitted RasterMint keeps the historical equal-spacing behavior.
    """
    normalized = [str(stop).strip().upper() for stop in stops if str(stop).strip()]
    if len(normalized) < 2:
        raise ValueError("At least two colors are required to generate a gradient palette")

    count = max(2, min(256, int(count)))
    mode = str(space or "OKLab").strip().upper().replace(" ", "")

    if positions is None:
        stop_positions = [i / (len(normalized) - 1) for i in range(len(normalized))]
    else:
        stop_positions = [max(0.0, min(1.0, float(value))) for value in positions]
        if len(stop_positions) != len(normalized):
            raise ValueError("Gradient stop colors and positions must have the same length")
        if any(stop_positions[i] > stop_positions[i + 1] for i in range(len(stop_positions) - 1)):
            raise ValueError("Gradient stop positions must be in ascending order")

    result: list[str] = []
    for i in range(count):
        t = i / (count - 1)
        if t <= stop_positions[0]:
            result.append(normalized[0])
            continue
        if t >= stop_positions[-1]:
            result.append(normalized[-1])
            continue

        segment_index = 0
        for j in range(len(stop_positions) - 1):
            if stop_positions[j] <= t <= stop_positions[j + 1]:
                segment_index = j
                break

        left = stop_positions[segment_index]
        right = stop_positions[segment_index + 1]
        local_t = 1.0 if right <= left else (t - left) / (right - left)
        result.append(_interpolate_pair(normalized[segment_index], normalized[segment_index + 1], local_t, mode))
    return result
