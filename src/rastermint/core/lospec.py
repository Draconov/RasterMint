# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from rastermint import __version__

LOSPEC_PALETTE_LIST = "https://lospec.com/palette-list"


@dataclass(frozen=True, slots=True)
class LospecPalette:
    slug: str
    name: str
    author: str
    colors: list[str]

    @property
    def source_url(self) -> str:
        return f"{LOSPEC_PALETTE_LIST}/{self.slug}"


def normalize_lospec_slug(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Enter a Lospec palette slug or URL")
    if "://" in value:
        parsed = urlparse(value)
        parts = [part for part in parsed.path.split("/") if part]
        if "palette-list" in parts:
            index = parts.index("palette-list")
            if index + 1 < len(parts):
                value = parts[index + 1]
    value = value.removesuffix(".json").strip("/ ")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Invalid Lospec palette slug")
    return value.lower()


def palette_json_url(value: str) -> str:
    slug = normalize_lospec_slug(value)
    return f"{LOSPEC_PALETTE_LIST}/{slug}.json"


def parse_lospec_palette(slug: str, payload: bytes | str | dict) -> LospecPalette:
    if isinstance(payload, (bytes, bytearray)):
        data = json.loads(payload.decode("utf-8"))
    elif isinstance(payload, str):
        data = json.loads(payload)
    else:
        data = payload
    if not isinstance(data, dict) or data.get("error"):
        raise ValueError("Lospec palette was not found")
    raw_colors = data.get("colors")
    if not isinstance(raw_colors, list) or not raw_colors:
        raise ValueError("Lospec returned a palette without colors")
    colors: list[str] = []
    for value in raw_colors[:256]:
        text = str(value).strip().lstrip("#")
        if not re.fullmatch(r"[0-9A-Fa-f]{6}", text):
            continue
        colors.append(f"#{text.upper()}")
    if not colors:
        raise ValueError("Lospec returned no valid RGB colors")
    return LospecPalette(
        slug=normalize_lospec_slug(slug),
        name=str(data.get("name") or slug),
        author=str(data.get("author") or "Unknown"),
        colors=colors,
    )


def fetch_lospec_palette(value: str, timeout: float = 12.0) -> LospecPalette:
    slug = normalize_lospec_slug(value)
    request = Request(
        palette_json_url(slug),
        headers={"User-Agent": f"RasterMint/{__version__} (+https://github.com/Draconov/RasterMint)"},
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS host
        if getattr(response, "status", 200) != 200:
            raise ValueError(f"Lospec request failed with HTTP {response.status}")
        return parse_lospec_palette(slug, response.read())
