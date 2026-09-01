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



def test_layer_compositing_controls_follow_selected_layer_and_cards_show_masks():
    layers = (QML / "pages" / "LayersPage.qml").read_text(encoding="utf-8")

    # Blend/mask selectors must remain bindings to backend selection state.
    # Component.onCompleted only initialized them once and left stale values
    # visible after selecting another layer.
    assert 'currentIndex: Math.max(0, backend.layerBlendModes.indexOf(backend.selectedLayerBlendMode))' in layers
    assert 'currentIndex: Math.max(0, backend.layerMaskTypes.indexOf(String(backend.selectedLayerMask.type || "None")))' in layers
    assert 'Component.onCompleted: currentIndex = Math.max(0, backend.layerBlendModes.indexOf(backend.selectedLayerBlendMode))' not in layers
    assert 'Component.onCompleted: currentIndex = Math.max(0, backend.layerMaskTypes.indexOf(String(backend.selectedLayerMask.type || "None")))' not in layers

    # Layer cards expose non-default mask state alongside blend/opacity so
    # different compositing setups are visible without opening each layer.
    assert 'readonly property string maskType: String((layerMask && layerMask.type) || "None")' in layers
    assert 'if (maskType !== "None")' in layers
    assert 'parts.push(qsTr(maskType))' in layers

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
    assert 'text: qsTr("Save to Library")' in presets
    assert "backend.savePresetToLibrary" in presets
    assert "backend.deletePresetFromLibrary" in presets
    assert "model: backend.builtinPresets" not in presets


def test_gradient_presets_start_collapsed():
    palette = (QML / "pages" / "PalettePage.qml").read_text(encoding="utf-8")

    assert "property bool gradientPresetsExpanded: false" in palette


def test_palette_advanced_sections_start_collapsed_and_custom_dither_requires_apply():
    palette = (QML / "pages" / "PalettePage.qml").read_text(encoding="utf-8")
    backend = (ROOT / "src" / "rastermint" / "qmlui" / "backend.py").read_text(encoding="utf-8")

    assert "property bool optimizerExpanded: false" in palette
    assert "property bool paletteDitherLabExpanded: false" in palette
    assert "visible: root.optimizerExpanded" in palette
    assert "visible: root.paletteDitherLabExpanded" in palette
    assert "from: 2; to: 12; value: backend.customDitherMatrixSize" in palette
    assert 'text: qsTr("Apply custom")' in palette
    assert "backend.applyCustomDitherMatrix()" in palette

    # Editing the designer is draft-only; the settings stack is committed only
    # through the explicit Apply custom slot.
    assert "_CUSTOM_DITHER_MATRIX_MAX_SIZE = 12" in backend
    cell_start = backend.index("def setCustomDitherMatrixCell")
    apply_start = backend.index("def applyCustomDitherMatrix")
    cell_block = backend[cell_start:apply_start]
    assert "_replace_settings(" not in cell_block


def test_apply_custom_translation_key_exists_in_every_bundled_language():
    translations = ROOT / "src" / "rastermint" / "data" / "translations"
    for path in translations.glob("*.json"):
        payload = __import__("json").loads(path.read_text(encoding="utf-8"))
        assert "Apply custom" in payload.get("messages", {}), path.name


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

    generate_start = palette.index('text: qsTr("Generate")')
    generate_block = palette[generate_start: palette.index("            Item { Layout.preferredHeight: 4 }", generate_start)]
    assert "root.gradientDirty = false" in generate_block


def test_export_transparency_toggle_is_visibly_disabled_when_unavailable():
    export_dialog = (QML / "ExportImageDialog.qml").read_text(encoding="utf-8")

    assert "enabled: root.sourceHasTransparency && root.transparencySupported" in export_dialog
    assert "opacity: enabled ? 1.0 : 0.45" in export_dialog
    assert "Source image has no transparency to preserve." in export_dialog
    assert 'qsTr("%1 does not support transparency.").arg(root.selectedFormat)' in export_dialog


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


def test_inspector_navigation_order_groups_and_default_page():
    main = (QML / "Main.qml").read_text(encoding="utf-8")

    # Keep Layers as the startup page even though the navigation was regrouped.
    assert "property int inspectorIndex: 7" in main

    nav_start = main.index("                    ColumnLayout {", main.index("id: inspectorPanel"))
    nav_end = main.index("                Rectangle {\n                    Layout.fillWidth: true", nav_start + 1)
    nav = main[nav_start:nav_end]

    labels = [
        'text: qsTr("Randomize")',
        'text: qsTr("Presets")',
        'text: qsTr("Hardware")',
        'text: qsTr("Palette")',
        'text: qsTr("Layers")',
        'text: qsTr("Source")',
        'text: qsTr("Preview")',
        'text: qsTr("Raster")',
        'text: qsTr("Animation")',
        'text: qsTr("Media Playback")',
    ]
    positions = [nav.index(label) for label in labels]
    assert positions == sorted(positions)
    assert nav.count("Layout.preferredHeight: 11") == 3

    stack_start = main.index("                        StackLayout {")
    stack_end = main.index("                        }", stack_start)
    stack = main[stack_start:stack_end]
    pages = [
        "Pages.RandomizePage { }",
        "Pages.SourcePage { }",
        "Pages.PreviewPage { onFitRequested: canvas.resetView() }",
        "Pages.RasterPage { }",
        "Pages.PresetsPage { }",
        "Pages.HardwarePage { }",
        "Pages.PalettePage { }",
        "Pages.LayersPage { }",
        "Pages.AnimationPage { }",
        "Pages.MediaPage { }",
    ]
    page_positions = [stack.index(page) for page in pages]
    assert page_positions == sorted(page_positions)


def test_inspector_navigation_uses_sidebar_icons_and_hover_tooltips():
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    button = (QML / "components" / "InspectorNavButton.qml").read_text(encoding="utf-8")

    assert "Layout.preferredWidth: 56" in main

    icon_files = [
        "sidebar-random.png",
        "sidebar-source.png",
        "sidebar-preview.png",
        "sidebar-raster.png",
        "sidebar-presets.png",
        "sidebar-hardware.png",
        "sidebar-layers.png",
        "sidebar-animation.png",
        "sidebar-media-playback.png",
    ]
    for filename in icon_files:
        assert f'Qt.resolvedUrl("../data/icons/{filename}")' in main
        assert (ROOT / "src" / "rastermint" / "data" / "icons" / filename).is_file()

    # Palette is intentionally theme-driven rather than a static image.
    assert 'text: qsTr("Palette")\n                            paletteSwatches: true' in main
    assert "theme.panelRaisedColor" in button
    assert "theme.selectionColor" in button
    assert "theme.accentColor" in button
    assert "theme.textColor" in button

    # Static sidebar PNGs are used as alpha masks and tinted by pure QtQuick Canvas.
    # Do not depend on Qt5Compat.GraphicalEffects: that module is not present in
    # the Linux CI/runtime environment.
    assert "Qt5Compat.GraphicalEffects" not in button
    assert "ColorOverlay" not in button
    assert "property color iconColor: control.selected ? theme.accentColor : theme.textColor" in button
    assert "Canvas {" in button
    assert "property url imageSource: control.iconSource" in button
    assert "loadImage(imageSource)" in button
    assert 'ctx.globalCompositeOperation = "source-in"' in button
    assert "ctx.fillStyle = tintColor" in button
    assert "onTintColorChanged: requestPaint()" in button
    assert "control.selected ? theme.accentColor : theme.textColor" in button

    # Labels remain on the buttons for accessibility and are shown only as hover tooltips.
    assert "ToolTip.visible: control.hovered" in button
    assert "ToolTip.text: control.text" in button
    assert "visible: control.selected" not in button
    assert "contentItem: Item" in button
    assert "width: 32" in button
    assert "height: 32" in button


def test_runtime_localization_is_packaged_and_exposed_to_qml():
    app = (ROOT / "src" / "rastermint" / "app.py").read_text(encoding="utf-8")
    settings = (QML / "SettingsDialog.qml").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    spec = (ROOT / "build" / "rastermint.spec").read_text(encoding="utf-8")
    localization = (ROOT / "src" / "rastermint" / "qmlui" / "localization.py").read_text(encoding="utf-8")
    ukrainian = ROOT / "src" / "rastermint" / "data" / "translations" / "uk.json"

    assert "LocalizationManager(engine)" in app
    assert 'setContextProperty("localization", localization)' in app
    assert 'id: languageChooser' in settings
    assert 'localization.setLanguage(selectedId)' in settings
    assert 'separatorToken: "__language_separator__"' in settings
    assert 'qsTr("System default")' not in settings
    assert 'DEFAULT_LANGUAGE_ID = "en"' in localization
    for language_id in ("en", "uk", "fr", "de", "es", "pt", "it", "he", "ar", "pl", "ga", "lv",
                        "zh", "hi", "bn", "id", "ur", "pa", "ja", "vi", "tr", "ko"):
        assert f'"{language_id}"' in localization
    assert '"ru"' not in localization
    assert 'data/translations/*.json' in pyproject
    assert '"data/translations/*.json"' in spec
    assert ukrainian.is_file()
    assert "QCoreApplication.installTranslator" in localization
    assert "self._engine.retranslate()" in localization


def test_preset_mutation_uses_selected_preset_and_dynamic_last_category():
    presets = (QML / "pages" / "PresetsPage.qml").read_text(encoding="utf-8")

    # Preset cards only select/apply. Mutation is initiated once from the
    # dedicated Preset Mutation controls using the selected preset id.
    delegate_start = presets.index("Component {\n        id: presetCardDelegate")
    controls_start = presets.index('text: qsTr("Preset Mutation")')
    delegate = presets[delegate_start:controls_start]
    assert 'text: qsTr("Mutate")' not in delegate
    assert "root.selectPreset(modelData.id, presetCard.displayName)" in delegate
    assert 'border.color: (!Boolean(modelData.mutation) && root.selectedPresetId === String(modelData.id)) ? theme.accentColor : theme.borderColor' in delegate

    mutation_controls = presets[controls_start:presets.index("        ScrollView {", controls_start)]
    assert 'text: qsTr("Variants")' in mutation_controls
    assert 'text: qsTr("Mutation amount")' in mutation_controls
    assert 'text: qsTr("Mutate")' in mutation_controls
    assert "root.selectedPresetId" in mutation_controls
    assert 'root.setPresetCategoryExpanded("Mutations", true)' in mutation_controls

    # Mutations are no longer a special top grid; they are a dynamic category
    # after the normal category repeater, so the library ordering stays tidy.
    repeater_pos = presets.index("model: root.presetCategories")
    mutation_category_pos = presets.index("id: mutationCategorySection")
    assert mutation_category_pos > repeater_pos
    assert 'localization.translateRuntime(localization.effectiveLanguageId, "Mutations")' in presets
    assert 'presetModel: backend.presetMutations || []' in presets[mutation_category_pos:]


def test_mutations_translation_key_exists_in_every_bundled_language():
    translations = ROOT / "src" / "rastermint" / "data" / "translations"
    for path in translations.glob("*.json"):
        payload = __import__("json").loads(path.read_text(encoding="utf-8"))
        messages = payload.get("messages", {})
        assert "Mutations" in messages, path.name
        assert "Select a preset first" in messages, path.name


def test_new_widespread_translation_dictionaries_are_complete_and_preserve_placeholders():
    import json
    import re

    translations = ROOT / "src" / "rastermint" / "data" / "translations"
    reference = json.loads((translations / "uk.json").read_text(encoding="utf-8"))["messages"]
    placeholder = re.compile(r"%[12](?!\d)")
    expected = {"zh", "hi", "bn", "id", "ur", "pa", "ja", "vi", "tr", "ko"}

    for language_id in expected:
        path = translations / f"{language_id}.json"
        assert path.is_file(), language_id
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["language"] == language_id
        messages = payload["messages"]
        assert set(messages) == set(reference), language_id
        assert all(str(value).strip() for value in messages.values()), language_id
        for source, translated in messages.items():
            assert sorted(placeholder.findall(source)) == sorted(placeholder.findall(translated)), (language_id, source)

    assert not (translations / "ru.json").exists()
