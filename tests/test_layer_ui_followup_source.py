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


def test_alt_click_is_handled_by_enable_toggles_and_not_the_group_card():
    source = (ROOT / "src/rastermint/qml/pages/LayersPage.qml").read_text(encoding="utf-8")

    assert "backend.toggleSoloLayer(index)" in source
    assert "backend.toggleSoloLayerGroup(String(groupHeader.modelData.id))" in source
    group_name_mouse_area = source.split("id: groupNameEditor", 1)[1].split("HoverHandler { id: groupHeaderHover", 1)[0]
    assert "Qt.AltModifier" not in group_name_mouse_area


def test_solo_visual_state_uses_effective_toggle_state_without_mutating_authored_enabled_state():
    source = (ROOT / "src/rastermint/qml/pages/LayersPage.qml").read_text(encoding="utf-8")
    backend_source = (ROOT / "src/rastermint/qmlui/backend.py").read_text(encoding="utf-8")

    assert "backend.layerEffectiveEnabled(index)" in source
    assert "backend.layerGroupEffectiveEnabled(String(groupHeader.modelData.id))" in source
    assert "def layerEffectiveEnabled(self, index: int)" in backend_source
    assert "def layerGroupEffectiveEnabled(self, group_id: str)" in backend_source
    assert "def toggleSoloLayer(self, index: int)" in backend_source


def test_menu_shortcut_uses_sequences_for_standard_keys():
    source = (ROOT / "src/rastermint/qml/components/MintMenuItem.qml").read_text(encoding="utf-8")

    assert "Shortcut {" in source
    assert "sequences:" in source
    assert "sequence:" not in source
