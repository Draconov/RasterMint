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


def _rich_group(
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
        _rich_group("g2", "Group 2", opacity=0.35, blend_mode="Overlay", color_label="#54a0ff", note="CRT finishing pass"),
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
        _rich_group("g-root", "Group 1", opacity=0.8, blend_mode="Multiply", color_label="#ff9f43"),
        _rich_group("g-child", "Group 2", parent_id="g-root", note="cleanup"),
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
    groups = [_rich_group("root", "Group 1"), _rich_group("child", "Group 2", "root"), _rich_group("nested", "Group 3", "child")]

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
    settings.layer_groups = [_rich_group("g1", "Group 1")]
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
    settings.layer_groups = [_rich_group("g1", "Group 1", opacity=0.5, blend_mode="Normal")]

    runtime = runtime_effect_stack(settings)
    result = apply_normalized_effect_stack(base, runtime, settings.palette)

    flat_stack = [deepcopy(invert), deepcopy(grayscale)]
    for step in flat_stack:
        step["group_id"] = ""
    full_group_result = apply_effect_stack(base, flat_stack, settings.palette)
    expected = Image.blend(base.convert("RGB"), full_group_result.convert("RGB"), 0.5)

    assert result.getpixel((0, 0)) == expected.getpixel((0, 0))


# ---- merged from test_layer_groups_v071.py ----

from rastermint.core.effect_schema import new_effect
from rastermint.core.layer_groups import (
    MAX_GROUP_DEPTH,
    can_reparent_group,
    canonicalize_layer_groups,
    group_depth,
    group_path,
    next_group_name,
    prune_layer_groups,
)
from rastermint.core.processor import runtime_effect_stack
from rastermint.core.settings import ProcessingSettings


def _nested_group(group_id: str, name: str, parent_id: str = "", *, enabled: bool = True) -> dict:
    return {
        "id": group_id,
        "name": name,
        "parent_id": parent_id,
        "collapsed": False,
        "enabled": enabled,
    }


def test_next_group_name_uses_first_unused_number():
    groups = [_nested_group("a", "Group 1"), _nested_group("b", "Custom"), _nested_group("c", "Group 3")]
    assert next_group_name(groups) == "Group 2"


def test_group_tree_supports_exactly_five_levels_and_rejects_cycles():
    groups = canonicalize_layer_groups([
        _nested_group("g1", "Group 1"),
        _nested_group("g2", "Group 2", "g1"),
        _nested_group("g3", "Group 3", "g2"),
        _nested_group("g4", "Group 4", "g3"),
        _nested_group("g5", "Group 5", "g4"),
    ])
    assert MAX_GROUP_DEPTH == 5
    assert group_path("g5", groups) == ["g1", "g2", "g3", "g4", "g5"]
    assert group_depth("g5", groups) == 5
    assert not can_reparent_group("g1", "g5", groups)

    groups_with_root = groups + [_nested_group("root", "Group 6")]
    assert not can_reparent_group("g1", "g5", groups_with_root)
    assert can_reparent_group("g5", "root", groups_with_root)


def test_pruning_keeps_ancestor_groups_but_removes_empty_branches():
    groups = [
        _nested_group("root", "Group 1"),
        _nested_group("child", "Group 2", "root"),
        _nested_group("unused", "Group 3"),
    ]
    layer = new_effect("Invert")
    layer["group_id"] = "child"

    pruned = prune_layer_groups(groups, [layer])

    assert [group["id"] for group in pruned] == ["root", "child"]


def test_disabled_ancestor_group_disables_descendant_layers_at_runtime():
    settings = ProcessingSettings()
    layer = new_effect("Invert")
    layer["group_id"] = "child"
    settings.effect_stack = [layer]
    settings.layer_groups = [
        _nested_group("root", "Group 1", enabled=False),
        _nested_group("child", "Group 2", "root", enabled=True),
    ]

    runtime = runtime_effect_stack(settings)

    assert runtime[0]["enabled"] is False


def test_group_view_exposes_nested_headers_and_hides_contents_when_parent_collapsed():
    from rastermint.core.layer_groups import build_layer_group_view

    first = new_effect("Invert")
    second = new_effect("Grayscale")
    first["group_id"] = "child"
    second["group_id"] = "child"
    groups = [
        {**_nested_group("root", "Group 1"), "collapsed": True},
        _nested_group("child", "Group 2", "root"),
    ]

    view = build_layer_group_view([first, second], groups)

    assert [header["id"] for header in view[0]["group_headers"]] == ["root"]
    assert view[0]["content_visible"] is False
    assert view[1]["group_headers"] == []
    assert view[1]["content_visible"] is False
    assert view[0]["group_depth"] == 2


def test_drop_layer_into_same_container_creates_nested_group_and_edge_drop_ungroups_one_level():
    from rastermint.core.layer_groups import drop_layer

    first = new_effect("Invert")
    second = new_effect("Grayscale")
    outside = new_effect("Posterize")
    first["group_id"] = "root"
    second["group_id"] = "root"
    stack = [first, second, outside]
    groups = [_nested_group("root", "Group 1")]

    nested_stack, nested_groups = drop_layer(
        stack,
        groups,
        0,
        1,
        "into",
        new_group_id="nested",
        new_group_name="Group 2",
    )
    nested = next(group for group in nested_groups if group["id"] == "nested")
    assert nested["parent_id"] == "root"
    assert {nested_stack[0]["group_id"], nested_stack[1]["group_id"]} == {"nested"}

    source_index = next(i for i, step in enumerate(nested_stack) if step["id"] == first["id"])
    target_index = next(i for i, step in enumerate(nested_stack) if step["id"] == outside["id"])
    moved_stack, moved_groups = drop_layer(
        nested_stack,
        nested_groups,
        source_index,
        target_index,
        "after",
        new_group_id="unused",
        new_group_name="Unused",
    )
    moved = next(step for step in moved_stack if step["id"] == first["id"])
    assert moved["group_id"] == "root"
    assert any(group["id"] == "nested" for group in moved_groups)


def test_drop_group_on_layer_builds_parent_group_and_honours_depth_limit():
    from rastermint.core.layer_groups import drop_group_on_layer

    inside = new_effect("Invert")
    target = new_effect("Grayscale")
    inside["group_id"] = "source"
    groups = [_nested_group("source", "Group 1")]

    stack, updated = drop_group_on_layer(
        [inside, target],
        groups,
        "source",
        1,
        new_group_id="parent",
        new_group_name="Group 2",
    )
    parent = next(group for group in updated if group["id"] == "parent")
    source = next(group for group in updated if group["id"] == "source")
    assert parent["parent_id"] == ""
    assert source["parent_id"] == "parent"
    assert stack[1]["group_id"] == "parent"



def test_dragging_layer_out_of_group_ungroups_one_level_even_without_an_outside_target():
    from rastermint.core.layer_groups import drop_layer

    layer = new_effect("Invert")
    layer["group_id"] = "child"
    stack, groups = drop_layer(
        [layer],
        [_nested_group("root", "Group 1"), _nested_group("child", "Group 2", "root")],
        0,
        0,
        "ungroup",
        new_group_id="unused",
        new_group_name="Unused",
    )

    assert stack[0]["group_id"] == "root"
    assert [group["id"] for group in groups] == ["root"]


# ---- merged from test_solo_visibility.py ----

from copy import deepcopy

from rastermint.core.layer_groups import group_effective_enabled_for_solo, step_effective_enabled_for_solo


def _solo_group(group_id, parent_id="", enabled=True):
    return {"id": group_id, "name": group_id, "parent_id": parent_id, "enabled": enabled}


def test_layer_solo_forces_only_target_on_without_mutating_authored_flags():
    stack = [
        {"id": "a", "enabled": False, "group_id": ""},
        {"id": "b", "enabled": True, "group_id": ""},
    ]
    original = deepcopy(stack)

    states = [step_effective_enabled_for_solo(step, [], solo_layer_id="a") for step in stack]

    assert states == [True, False]
    assert stack == original


def test_group_solo_forces_selected_path_on_and_preserves_disabled_nested_solo_group():
    groups = [
        _solo_group("outer", enabled=False),
        _solo_group("target", "outer", enabled=False),
        _solo_group("nested", "target", enabled=False),
    ]
    direct = {"id": "direct", "enabled": True, "group_id": "target"}
    nested = {"id": "nested-layer", "enabled": True, "group_id": "nested"}
    outside = {"id": "outside", "enabled": True, "group_id": ""}

    assert step_effective_enabled_for_solo(direct, groups, solo_group_id="target") is True
    assert step_effective_enabled_for_solo(nested, groups, solo_group_id="target") is False
    assert step_effective_enabled_for_solo(outside, groups, solo_group_id="target") is False


def test_group_toggle_state_reflects_temporary_solo_scope():
    groups = [
        _solo_group("outer", enabled=False),
        _solo_group("target", "outer", enabled=False),
        _solo_group("nested", "target", enabled=False),
        _solo_group("other", enabled=True),
    ]
    stack = [{"id": "layer", "enabled": True, "group_id": "target"}]

    assert group_effective_enabled_for_solo("outer", stack, groups, solo_group_id="target") is True
    assert group_effective_enabled_for_solo("target", stack, groups, solo_group_id="target") is True
    assert group_effective_enabled_for_solo("nested", stack, groups, solo_group_id="target") is False
    assert group_effective_enabled_for_solo("other", stack, groups, solo_group_id="target") is False

    assert group_effective_enabled_for_solo("outer", stack, groups, solo_layer_id="layer") is True
    assert group_effective_enabled_for_solo("target", stack, groups, solo_layer_id="layer") is True
    assert group_effective_enabled_for_solo("other", stack, groups, solo_layer_id="layer") is False
