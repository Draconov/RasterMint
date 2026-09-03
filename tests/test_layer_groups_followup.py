from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PIL import Image

from rastermint.core.effect_schema import new_effect
from rastermint.core.effect_stack import apply_effect_stack, apply_normalized_effect_stack
from rastermint.core.layer_groups import (
    canonicalize_layer_groups,
    create_layer_group,
    duplicate_layer_group,
    drop_layer,
    layer_indices_for_group,
    ungroup_layer_group,
)
from rastermint.core.processor import runtime_effect_stack
from rastermint.core.settings import ProcessingSettings


def _group(
    group_id: str,
    name: str,
    parent_id: str = "",
    *,
    collapsed: bool = False,
    enabled: bool = True,
    opacity: float = 1.0,
    blend_mode: str = "Normal",
    color_label: str = "",
    note: str = "",
) -> dict:
    return {
        "id": group_id,
        "name": name,
        "parent_id": parent_id,
        "collapsed": collapsed,
        "enabled": enabled,
        "opacity": opacity,
        "blend_mode": blend_mode,
        "color_label": color_label,
        "note": note,
    }


def test_group_metadata_defaults_and_custom_fields_are_canonicalized():
    groups = canonicalize_layer_groups([
        {"id": "g1", "name": "Group 1"},
        _group("g2", "Group 2", opacity=0.35, blend_mode="Overlay", color_label="#54a0ff", note="CRT finishing pass"),
    ])

    assert groups[0]["opacity"] == 1.0
    assert groups[0]["blend_mode"] == "Normal"
    assert groups[0]["color_label"] == ""
    assert groups[0]["note"] == ""
    assert groups[1]["opacity"] == 0.35
    assert groups[1]["blend_mode"] == "Overlay"
    assert groups[1]["color_label"] == "#54a0ff"
    assert groups[1]["note"] == "CRT finishing pass"



def test_multiselect_grouping_packs_selected_layers_together_while_preserving_order():
    stack = [new_effect("Adjustments"), new_effect("Grayscale"), new_effect("Invert"), new_effect("Gaussian Blur")]
    grouped_stack, grouped_groups = create_layer_group(
        stack,
        [],
        [1, 3],
        group_id="g1",
        group_name="Group 1",
    )

    assert [step["kind"] for step in grouped_stack] == ["Adjustments", "Grayscale", "Gaussian Blur", "Invert"]
    assert [step.get("group_id", "") for step in grouped_stack] == ["", "g1", "g1", ""]
    assert [group["id"] for group in grouped_groups] == ["g1"]



def test_duplicate_group_clones_entire_hierarchy_and_children():
    first = new_effect("Invert")
    second = new_effect("Grayscale")
    third = new_effect("Posterize")
    first["group_id"] = "g-root"
    second["group_id"] = "g-child"
    third["group_id"] = "g-child"
    stack = [first, second, third]
    groups = [
        _group("g-root", "Group 1", opacity=0.8, blend_mode="Multiply", color_label="#ff9f43"),
        _group("g-child", "Group 2", parent_id="g-root", note="cleanup"),
    ]

    duplicated_stack, duplicated_groups, duplicated_root_id = duplicate_layer_group(stack, groups, "g-root")

    assert duplicated_root_id
    assert len(duplicated_stack) == 6
    assert len(duplicated_groups) == 4
    new_root = next(group for group in duplicated_groups if group["id"] == duplicated_root_id)
    assert new_root["name"] == "Group 1 Copy"
    assert new_root["blend_mode"] == "Multiply"
    assert new_root["opacity"] == 0.8
    duplicate_indices = layer_indices_for_group(duplicated_stack, duplicated_groups, duplicated_root_id)
    assert duplicate_indices == [3, 4, 5]
    duplicate_group_ids = {duplicated_stack[i]["group_id"] for i in duplicate_indices}
    assert len(duplicate_group_ids) == 2
    assert duplicated_stack[3]["kind"] == "Invert"
    assert [duplicated_stack[i]["kind"] for i in duplicate_indices[1:]] == ["Grayscale", "Posterize"]



def test_ungroup_group_dissolves_container_but_keeps_children_in_place():
    first = new_effect("Invert")
    second = new_effect("Grayscale")
    first["group_id"] = "child"
    second["group_id"] = "nested"
    stack = [first, second]
    groups = [_group("root", "Group 1"), _group("child", "Group 2", "root"), _group("nested", "Group 3", "child")]

    updated_stack, updated_groups = ungroup_layer_group(stack, groups, "child")

    assert updated_stack[0]["group_id"] == "root"
    assert updated_stack[1]["group_id"] == "nested"
    nested = next(group for group in updated_groups if group["id"] == "nested")
    assert nested["parent_id"] == "root"
    assert [group["id"] for group in updated_groups] == ["root", "nested"]



def test_solo_group_hides_layers_outside_the_selected_group():
    inside = new_effect("Invert")
    outside = new_effect("Grayscale")
    inside["group_id"] = "g1"
    settings = ProcessingSettings()
    settings.effect_stack = [inside, outside]
    settings.layer_groups = [_group("g1", "Group 1")]
    settings.solo_group_id = "g1"

    runtime = runtime_effect_stack(settings)

    assert runtime[0]["enabled"] is True
    assert runtime[1]["enabled"] is False



def test_group_opacity_is_applied_after_the_group_is_composited():
    base = Image.new("RGB", (1, 1), (80, 140, 220))
    invert = new_effect("Invert")
    grayscale = new_effect("Grayscale")
    invert["group_id"] = "g1"
    grayscale["group_id"] = "g1"

    settings = ProcessingSettings()
    settings.effect_stack = [invert, grayscale]
    settings.layer_groups = [_group("g1", "Group 1", opacity=0.5, blend_mode="Normal")]

    runtime = runtime_effect_stack(settings)
    result = apply_normalized_effect_stack(base, runtime, settings.palette)

    flat_stack = [deepcopy(invert), deepcopy(grayscale)]
    for step in flat_stack:
        step["group_id"] = ""
    full_group_result = apply_effect_stack(base, flat_stack, settings.palette)
    expected = Image.blend(base.convert("RGB"), full_group_result.convert("RGB"), 0.5)

    assert result.getpixel((0, 0)) == expected.getpixel((0, 0))
