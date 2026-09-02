from __future__ import annotations

from importlib import resources


def _qml(relative: str) -> str:
    return resources.files("rastermint").joinpath(relative).read_text(encoding="utf-8")


def test_layers_group_button_creates_immediately_without_naming_dialog():
    qml = _qml("qml/pages/LayersPage.qml")
    assert 'text: qsTr("Group")' in qml
    assert "onClicked: backend.groupSelectedLayers()" in qml
    assert "Create Layer Group" not in qml
    assert "groupDialog" not in qml


def test_layers_support_nested_group_headers_inline_rename_and_drop_intent():
    qml = _qml("qml/pages/LayersPage.qml")
    assert "groupHeaders" in qml
    assert "editingGroupId" in qml
    assert "backend.renameLayerGroup" in qml
    assert "onDoubleClicked" in qml
    assert "backend.dropLayer(" in qml
    assert 'dragDropMode = "ungroup"' in qml
    assert "backend.dropLayerGroup(" in qml


def test_layer_card_tooltip_contains_effect_description_without_drag_hint():
    qml = _qml("qml/pages/LayersPage.qml")
    assert "MintToolTip" in qml
    assert "effectDescription(kind)" in qml
    assert "Drag anywhere on the layer card to reorder" not in qml
