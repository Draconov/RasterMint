# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import json

from rastermint.core.presets import load_preset, save_preset
from rastermint.core.settings import ProcessingSettings


def test_preset_roundtrip(tmp_path):
    original = ProcessingSettings(
        algorithm="Bayer 8x8",
        brightness=12,
        contrast=-8,
        saturation=20,
        gamma=1.25,
        grayscale=True,
        invert=True,
        blur_radius=1.5,
        sharpen=1.6,
        dither_strength=0.75,
        pixel_size=3,
        serpentine=False,
        output_divisor=3,
        palette=["#112233", "#445566", "#FFFFFF"],
        hardware_profile_id="game-boy",
        hardware_mode="strict",
    )
    path = tmp_path / "test.json"
    save_preset(path, original)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["hardware_reference"] == {"profile_id": "game-boy", "mode": "strict"}
    loaded = load_preset(path)
    assert loaded.to_dict() == original.to_dict()
