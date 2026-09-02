from rastermint.core.effect_schema import (
    EFFECT_CATEGORIES,
    EFFECT_DEFINITIONS,
    EFFECT_DESCRIPTIONS,
    _HIDDEN_EFFECT_KINDS,
    effect_categories,
)


def test_layer_catalog_categories_are_small_and_complete():
    visible = set(EFFECT_DEFINITIONS) - set(_HIDDEN_EFFECT_KINDS)
    flattened = [kind for _, kinds in EFFECT_CATEGORIES for kind in kinds]

    assert len(flattened) == len(set(flattened)), "An effect appears in more than one add-layer category"
    assert set(flattened) == visible, "Every visible effect should have one explicit logical category"
    assert max(len(kinds) for _, kinds in EFFECT_CATEGORIES) <= 10


def test_every_visible_layer_effect_has_hover_description():
    visible = set(EFFECT_DEFINITIONS) - set(_HIDDEN_EFFECT_KINDS)
    assert visible <= set(EFFECT_DESCRIPTIONS)
    assert all(EFFECT_DESCRIPTIONS[kind].strip() for kind in visible)

    categories = effect_categories()
    for category in categories:
        descriptions = category.get("descriptions", {})
        for kind in category["effects"]:
            assert descriptions.get(kind) == EFFECT_DESCRIPTIONS[kind]


def test_display_and_glitch_groups_have_expected_workflow_order():
    names = [name for name, _ in EFFECT_CATEGORIES]
    assert names == [
        "Color & Tone",
        "Detail & Light",
        "Pixel & Dither",
        "Print Lab",
        "Text & Overlay",
        "Noise & Motion",
        "Channels & Color Glitch",
        "Pixel & Data Glitch",
        "Display Geometry & Response",
        "CRT & Scan",
        "Analog Signal",
        "Tape & Compression",
        "Hardware Stages",
    ]


def test_layers_page_uses_effect_descriptions_for_hover_tooltips():
    from importlib import resources

    qml = resources.files("rastermint").joinpath("qml/pages/LayersPage.qml").read_text(encoding="utf-8")
    assert "function effectDescription(kind)" in qml
    assert "MintToolTip" in qml
    assert "visible: effectDelegate.hovered" in qml
    assert "readonly property string effectDescription: root.effectDescription(modelData)" in qml
