# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from pathlib import Path

from rastermint.core.palette_json import load_palette_json
from rastermint.core.palette_library import PALETTE_LIBRARY


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


def test_palette_loader_preserves_legitimate_numeric_name_prefix(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    path = base_dir / "rgb-6bit-64.json"
    path.write_text(
        json.dumps(
            {
                "format": "rastermint-palette",
                "version": 1,
                "id": "rgb-6bit-64",
                "name": "6-bit RGB 64",
                "category": "Test",
                "colors": ["#000000", "#ffffff"],
            }
        ),
        encoding="utf-8",
    )

    palette = load_palette_json(path)

    assert palette["name"] == "6-bit RGB 64"
    assert palette["id"] == "rgb-6bit-64"
    assert palette["colors"] == ["#000000", "#FFFFFF"]


def test_bundled_base_palette_filenames_have_no_sequence_prefix() -> None:
    base_dir = ROOT / "src" / "rastermint" / "data" / "palettes" / "base"
    numbered = [
        path.name
        for path in base_dir.glob("*.json")
        if len(path.name.split("-", 1)[0]) == 3 and path.name.split("-", 1)[0].isdigit()
    ]

    assert numbered == []


def test_base_palette_order_survives_filename_cleanup() -> None:
    expected_prefix = [
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
    ]

    assert [palette.id for palette in PALETTE_LIBRARY[:10]] == expected_prefix



def test_main_lazily_instantiates_inspector_pages() -> None:
    main_qml = ROOT / "src" / "rastermint" / "qml" / "Main.qml"
    text = main_qml.read_text(encoding="utf-8")

    # StackLayout used to instantiate all ten pages while engine.load() was
    # still constructing Main.qml. Each page is now behind a Loader and stays
    # alive after its first visit via the per-loader visited flag.
    assert text.count("property bool visited: false") == 10
    assert text.count("onLoaded: visited = true") == 10
    assert text.count("Layout.fillWidth: true") >= 10
    assert text.count("Layout.fillHeight: true") >= 10
    for index, page in enumerate(
        [
            "PresetsPage",
            "PreviewPage",
            "LayersPage",
            "PalettePage",
            "RasterPage",
            "HardwarePage",
            "SourcePage",
            "AnimationPage",
            "RandomizePage",
            "MediaPage",
        ]
    ):
        assert f"active: visited || window.inspectorIndex === {index}" in text
        assert f"Pages.{page}" in text


def test_gradient_presets_do_not_allocate_canvas_targets_at_startup() -> None:
    palette_page = ROOT / "src" / "rastermint" / "qml" / "pages" / "PalettePage.qml"
    text = palette_page.read_text(encoding="utf-8")

    assert "property bool gradientPresetsExpanded: false" in text
    assert "model: root.gradientPresetsExpanded ? root.gradientPresets : []" in text
    assert "Canvas {" not in text
    assert "orientation: Gradient.Horizontal" in text
