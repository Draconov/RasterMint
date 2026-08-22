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

    # allPresets is the combined built-in + user library model. Using
    # builtinPresets here silently removes the user's saved preset library.
    assert "GridView" in presets
    assert "model: backend.allPresets" in presets
    assert "backend.applyPreset(modelData.id)" in presets
    assert 'text: "Save to Library"' in presets
    assert "backend.savePresetToLibrary" in presets
    assert "backend.deletePresetFromLibrary" in presets
    assert "model: backend.builtinPresets" not in presets
