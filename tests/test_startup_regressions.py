# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from pathlib import Path

from rastermint.core.palette_json import load_palette_json


ROOT = Path(__file__).resolve().parents[1]
COLOR_PICKER = ROOT / "src" / "rastermint" / "qml" / "components" / "MintColorPicker.qml"


def test_color_picker_defers_heavy_startup_objects() -> None:
    text = COLOR_PICKER.read_text(encoding="utf-8")

    surface_component = text.index("id: pickerSurfaceComponent")
    first_canvas = text.index("Canvas {")
    surface_loader = text.index("id: pickerSurfaceLoader")
    eyedropper_component = text.index("id: eyedropperComponent")
    color_dialog = text.index("ColorDialog {")

    assert surface_component < first_canvas < surface_loader
    assert "active: popup.visible" in text
    assert text.count("Canvas {") == 2
    assert "id: eyedropperDialog" not in text
    assert eyedropper_component < color_dialog
    assert "eyedropperComponent.createObject(root)" in text


def test_base_palette_number_prefix_is_display_only_cleanup(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    path = base_dir / "example.json"
    path.write_text(
        json.dumps(
            {
                "format": "rastermint-palette",
                "version": 1,
                "id": "stable-palette-id",
                "name": "01. Autumn",
                "category": "Test",
                "colors": ["#000000", "#ffffff"],
            }
        ),
        encoding="utf-8",
    )

    palette = load_palette_json(path)

    assert palette["name"] == "Autumn"
    assert palette["id"] == "stable-palette-id"
    assert palette["colors"] == ["#000000", "#FFFFFF"]


def test_number_cleanup_does_not_touch_other_palette_folders(tmp_path: Path) -> None:
    extended_dir = tmp_path / "extended"
    extended_dir.mkdir()
    path = extended_dir / "example.json"
    path.write_text(
        json.dumps(
            {
                "format": "rastermint-palette",
                "version": 1,
                "id": "stable-palette-id",
                "name": "01. Autumn",
                "category": "Test",
                "colors": ["#000000"],
            }
        ),
        encoding="utf-8",
    )

    assert load_palette_json(path)["name"] == "01. Autumn"
