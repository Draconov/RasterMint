# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from pathlib import Path


PROFILE_DIR = Path(__file__).resolve().parents[1] / "src" / "rastermint" / "data" / "hardware_profiles"


def _load(name: str) -> dict:
    return json.loads((PROFILE_DIR / name).read_text(encoding="utf-8"))


def test_playstation_composite_profile_keeps_rgb555_strict_limit() -> None:
    profile = _load("playstation.json")
    assert profile["id"] == "playstation"
    assert profile["raster"]["width"] == 320
    assert profile["raster"]["height"] == 240
    assert profile["strict"]["supported"] is True
    assert profile["strict"]["constraints"]["channel_bits"] == [5, 5, 5]
    kinds = [item["kind"] for item in profile["visual"]["effects"]]
    assert "Dot Crawl" in kinds
    assert "Composite Noise" in kinds
    assert "CRT Mask" in kinds


def test_playstation_rgb_profile_is_cleaner_but_keeps_same_depth() -> None:
    profile = _load("playstation-rgb.json")
    assert profile["id"] == "playstation-rgb"
    assert profile["strict"]["constraints"]["channel_bits"] == [5, 5, 5]
    kinds = [item["kind"] for item in profile["visual"]["effects"]]
    assert "CRT Mask" in kinds
    assert "Dot Crawl" not in kinds
    assert "Composite Noise" not in kinds
