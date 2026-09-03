from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_layer_and_group_descriptions_live_on_cards_while_solo_hints_live_on_toggles():
    source = (ROOT / "src/rastermint/qml/pages/LayersPage.qml").read_text(encoding="utf-8")

    assert "id: layerEnabledToggleMouse" in source
    assert 'text: qsTr("Alt+Click to solo this layer")' in source
    assert "visible: layerEnabledToggleMouse.containsMouse" in source
    assert "visible: layerHover.hovered" in source
    assert "&& !layerEnabledToggleMouse.containsMouse" in source

    assert "id: groupEnabledToggleMouse" in source
    assert 'text: qsTr("Alt+Click to solo this group")' in source
    assert "visible: groupEnabledToggleMouse.containsMouse" in source
    assert "visible: groupHeaderHover.hovered" in source
    assert "&& !groupEnabledToggleMouse.containsMouse" in source


def test_alt_click_is_handled_by_enable_toggles_and_selects_the_target_for_bottom_buttons():
    source = (ROOT / "src/rastermint/qml/pages/LayersPage.qml").read_text(encoding="utf-8")

    assert "backend.selectLayer(index)" in source
    assert "backend.toggleSoloLayer(index)" in source
    assert "root.selectedGroupId = groupHeader.groupIdText" in source
    assert "backend.toggleSoloLayerGroup(groupHeader.groupIdText)" in source
    group_name_mouse_area = source.split("id: groupNameEditor", 1)[1].split("HoverHandler { id: groupHeaderHover", 1)[0]
    assert "Qt.AltModifier" not in group_name_mouse_area


def test_solo_visual_state_uses_safe_boolean_bindings_and_a_highlighted_toggle_shell():
    source = (ROOT / "src/rastermint/qml/pages/LayersPage.qml").read_text(encoding="utf-8")
    backend_source = (ROOT / "src/rastermint/qmlui/backend.py").read_text(encoding="utf-8")

    assert "property bool authoredLayerEnabled: Boolean(layerEnabled)" in source
    assert "property bool layerSoloTarget: backend.layerSolo(index)" in source
    assert "property bool groupEnabledState: Boolean(groupModelReady && groupHeader.modelData.enabled)" in source
    assert "property bool groupSoloTarget: backend.layerGroupSolo(groupIdText)" in source
    assert "checked: Boolean(backend.soloActive ? backend.layerEffectiveEnabled(index) : layerDelegate.authoredLayerEnabled)" in source
    assert "backend.layerGroupEffectiveEnabled(groupHeader.groupIdText)" in source
    assert "color: layerDelegate.layerSoloTarget ? Qt.alpha(theme.accentColor, 0.18) : \"transparent\"" in source
    assert "color: groupHeader.groupSoloTarget ? Qt.alpha(theme.accentColor, 0.18) : \"transparent\"" in source
    assert "def layerEffectiveEnabled(self, index: int)" in backend_source
    assert "def layerGroupEffectiveEnabled(self, group_id: str)" in backend_source
    assert "def toggleSoloLayer(self, index: int)" in backend_source
    assert "def layerSolo(self, index: int)" in backend_source


def test_menu_shortcut_uses_sequences_for_standard_keys_and_menu_items_survive_theme_teardown():
    source = (ROOT / "src/rastermint/qml/components/MintMenuItem.qml").read_text(encoding="utf-8")

    assert "Shortcut {" in source
    assert "sequences:" in source
    assert "sequence:" not in source
    assert "readonly property color safeTextColor" in source
    assert "readonly property color safeSelectionColor" in source


def test_group_selection_keeps_bottom_solo_button_available():
    source = (ROOT / "src/rastermint/qml/pages/LayersPage.qml").read_text(encoding="utf-8")

    assert 'backend.layerGroupSolo(root.selectedGroupId)' in source
    assert 'backend.toggleSoloLayerGroup(root.selectedGroupId)' in source
    group_solo_pos = source.index('backend.layerGroupSolo(root.selectedGroupId)')
    solo_button_start = source.rfind('MintButton {', 0, group_solo_pos)
    solo_button_end = source.index('MintButton { Layout.fillWidth: true; text: qsTr("Group")', group_solo_pos)
    solo_button = source[solo_button_start:solo_button_end]
    assert 'enabled: !root.groupExists(root.selectedGroupId)' not in solo_button


def test_group_drag_uses_the_same_line_feedback_pattern_as_layer_drag():
    source = (ROOT / "src/rastermint/qml/pages/LayersPage.qml").read_text(encoding="utf-8")

    assert "function clearGroupDragIndicator()" in source
    assert "function setGroupDragIndicator(x, y, width)" in source
    assert "root.updateGroupDragAt(point.y)" in source
    assert "visible: root.groupDragId !== \"\" && root.groupDragIndicatorY >= 0" in source


def test_tooltip_component_has_theme_fallbacks_for_shutdown_teardown():
    source = (ROOT / "src/rastermint/qml/components/MintToolTip.qml").read_text(encoding="utf-8")

    assert "readonly property color safeTextColor" in source
    assert "readonly property color safePanelColor" in source
    assert "readonly property color safeAccentColor" in source
    assert "color: control.safeTextColor" in source
    assert "color: control.safePanelColor" in source
    assert "border.color: control.safeAccentColor" in source
