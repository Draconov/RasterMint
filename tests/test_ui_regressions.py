from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "src" / "rastermint" / "qml"


def test_layers_keep_slider_gesture_model_and_effect_categories():
    layers = (QML / "pages" / "LayersPage.qml").read_text(encoding="utf-8")
    slider = (QML / "components" / "MintSlider.qml").read_text(encoding="utf-8")

    # The parameter editor must stay stable while a slider owns the pointer.
    # Rebinding directly to backend.selectedLayerParams recreates the delegate
    # after the first live value update and breaks dragging.
    assert "property bool parameterInteractionActive" in layers
    assert "property var editorLayerParams" in layers
    assert "model: root.editorLayerParams" in layers
    assert "onInteractionActiveChanged" in layers
    assert "onUserMoved" in layers
    assert "beginParameterInteraction" in layers
    assert "endParameterInteraction" in layers

    # Keep the categorized, multi-open add-effect browser.
    assert "backend.layerCategories" in layers
    assert "expandedEffectCategories" in layers
    assert "toggleEffectCategory" in layers

    # LayersPage intentionally consumes the richer MintSlider interaction API.
    assert "readonly property bool interactionActive" in slider
    assert "readonly property real displayValue" in slider
    assert "signal userMoved(real newValue)" in slider


def test_presets_page_keeps_library_grid_and_custom_preset_controls():
    presets = (QML / "pages" / "PresetsPage.qml").read_text(encoding="utf-8")

    # allPresets is still the single combined built-in + user library source.
    # The categorized browser filters that source into per-category PresetGrid
    # models instead of binding a GridView directly to backend.allPresets.
    assert "GridView" in presets
    assert "backend.allPresets ? backend.allPresets : []" in presets
    assert "component PresetGrid: GridView" in presets
    assert "model: presetModel" in presets
    assert "presetCategories" in presets
    assert "expandedPresetCategories" in presets
    assert "togglePresetCategory" in presets
    assert "property int presetColumns: width >= 500 ? 2 : 1" in presets
    assert "backend.applyPreset(modelData.id)" in presets
    assert 'text: "Save to Library"' in presets
    assert "backend.savePresetToLibrary" in presets
    assert "backend.deletePresetFromLibrary" in presets
    assert "model: backend.builtinPresets" not in presets


def test_gradient_presets_start_collapsed():
    palette = (QML / "pages" / "PalettePage.qml").read_text(encoding="utf-8")

    assert "property bool gradientPresetsExpanded: false" in palette


def test_gradient_presets_and_custom_generate_use_palette_backend():
    palette = (QML / "pages" / "PalettePage.qml").read_text(encoding="utf-8")

    # QML structure/syntax is covered by the real Qt compile smoke test. Keep
    # only the behavioral wiring contract here: presets and the custom editor
    # both generate a palette through the backend.
    preset_function = palette[
        palette.index("function applyGradientPreset(preset)") : palette.index("function gradientPresetSelected(preset)")
    ]
    assert "backend.generatePaletteFromPositionedStops(" in preset_function
    assert palette.count("backend.generatePaletteFromPositionedStops(") >= 2


def test_gradient_editor_marks_generate_button_as_pending_after_manual_changes():
    palette = (QML / "pages" / "PalettePage.qml").read_text(encoding="utf-8")

    assert "property bool gradientDirty: false" in palette
    assert "selected: root.gradientDirty" in palette
    assert "onValueModified: root.gradientDirty = true" in palette
    assert "onActivated: root.gradientDirty = true" in palette

    for function_name in (
        "updateGradientStop",
        "addGradientStop",
        "removeGradientStop",
        "moveGradientStop",
    ):
        start = palette.index("function " + function_name)
        next_function = palette.find("function ", start + 9)
        block = palette[start: next_function if next_function >= 0 else len(palette)]
        assert "gradientDirty = true" in block, function_name

    generate_start = palette.index('text: "Generate"')
    generate_block = palette[generate_start: palette.index("            Item { Layout.preferredHeight: 4 }", generate_start)]
    assert "root.gradientDirty = false" in generate_block


def test_export_transparency_toggle_is_visibly_disabled_when_unavailable():
    export_dialog = (QML / "ExportImageDialog.qml").read_text(encoding="utf-8")

    assert "enabled: root.sourceHasTransparency && root.transparencySupported" in export_dialog
    assert "opacity: enabled ? 1.0 : 0.45" in export_dialog
    assert "Source image has no transparency to preserve." in export_dialog
    assert 'root.selectedFormat + " does not support transparency."' in export_dialog


def test_palette_swatches_support_middle_click_delete_without_bypassing_locks():
    palette = (QML / "pages" / "PalettePage.qml").read_text(encoding="utf-8")
    backend = (ROOT / "src" / "rastermint" / "qmlui" / "backend.py").read_text(encoding="utf-8")

    assert "Qt.MiddleButton" in palette
    assert "backend.removePaletteColor(index)" in palette
    assert "middle-click to delete" in palette
    assert "if candidate >= 0:" in backend
    assert "or locks[candidate]" in backend
    assert "last unlocked colour" in backend


def test_palette_page_expands_category_for_applied_palette_changes():
    palette = (QML / "pages" / "PalettePage.qml").read_text(encoding="utf-8")

    assert "function appliedPaletteCategory()" in palette
    assert "function expandAppliedPaletteCategory()" in palette
    assert "function samePaletteColors(left, right)" in palette
    assert "function onSettingsChanged()" in palette
    assert "next[category] = true" in palette
