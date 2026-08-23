# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Iterable

PALETTE_FORMAT = "rastermint-palette"
PALETTE_VERSION = 1
_HEX_RE = re.compile(r"^#?([0-9A-Fa-f]{6})$")


def slugify_palette_name(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().casefold()).strip("-")
    return text or "palette"


def normalize_palette_colors(colors: Iterable[object]) -> list[str]:
    result: list[str] = []
    for raw in colors:
        match = _HEX_RE.fullmatch(str(raw).strip())
        if not match:
            raise ValueError(f"Invalid palette color: {raw!r}")
        result.append(f"#{match.group(1).upper()}")
        if len(result) >= 256:
            break
    if not result:
        raise ValueError("Palette is empty")
    return result


def normalize_palette_payload(
    payload: dict[str, Any],
    *,
    fallback_id: str = "",
    fallback_name: str = "",
) -> dict[str, Any]:
    if payload.get("format") != PALETTE_FORMAT:
        raise ValueError("Not a RasterMint palette")
    if int(payload.get("version", 0)) > PALETTE_VERSION:
        raise ValueError("Palette was created by a newer RasterMint version")
    name = str(payload.get("name") or fallback_name).strip()
    if not name:
        raise ValueError("Palette name is missing")

    palette_id = str(payload.get("id") or fallback_id).strip()
    if not palette_id:
        palette_id = slugify_palette_name(name)
    return {
        "format": PALETTE_FORMAT,
        "version": PALETTE_VERSION,
        "id": palette_id,
        "name": name,
        "category": str(payload.get("category") or "Custom").strip() or "Custom",
        "colors": normalize_palette_colors(payload.get("colors") or []),
        "description": str(payload.get("description") or "").strip(),
        "source": str(payload.get("source") or "").strip(),
    }


def load_palette_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Palette JSON must contain an object")
    return normalize_palette_payload(
        payload,
        fallback_id=source.stem,
        fallback_name=source.stem.replace("-", " ").title(),
    )


def write_palette_json(
    path: str | Path,
    *,
    palette_id: str,
    name: str,
    category: str,
    colors: Iterable[object],
    description: str = "",
    source: str = "",
) -> None:
    payload = normalize_palette_payload(
        {
            "format": PALETTE_FORMAT,
            "version": PALETTE_VERSION,
            "id": palette_id,
            "name": name,
            "category": category,
            "colors": list(colors),
            "description": description,
            "source": source,
        }
    )
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
