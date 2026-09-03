from __future__ import annotations

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


def _group(group_id: str, name: str, parent_id: str = "", *, enabled: bool = True) -> dict:
    return {
        "id": group_id,
        "name": name,
        "parent_id": parent_id,
        "collapsed": False,
        "enabled": enabled,
    }


def test_next_group_name_uses_first_unused_number():
    groups = [_group("a", "Group 1"), _group("b", "Custom"), _group("c", "Group 3")]
    assert next_group_name(groups) == "Group 2"


def test_group_tree_supports_exactly_five_levels_and_rejects_cycles():
    groups = canonicalize_layer_groups([
        _group("g1", "Group 1"),
        _group("g2", "Group 2", "g1"),
        _group("g3", "Group 3", "g2"),
        _group("g4", "Group 4", "g3"),
        _group("g5", "Group 5", "g4"),
    ])
    assert MAX_GROUP_DEPTH == 5
    assert group_path("g5", groups) == ["g1", "g2", "g3", "g4", "g5"]
    assert group_depth("g5", groups) == 5
    assert not can_reparent_group("g1", "g5", groups)

    groups_with_root = groups + [_group("root", "Group 6")]
    assert not can_reparent_group("g1", "g5", groups_with_root)
    assert can_reparent_group("g5", "root", groups_with_root)


def test_pruning_keeps_ancestor_groups_but_removes_empty_branches():
    groups = [
        _group("root", "Group 1"),
        _group("child", "Group 2", "root"),
        _group("unused", "Group 3"),
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
        _group("root", "Group 1", enabled=False),
        _group("child", "Group 2", "root", enabled=True),
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
        {**_group("root", "Group 1"), "collapsed": True},
        _group("child", "Group 2", "root"),
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
    groups = [_group("root", "Group 1")]

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
    groups = [_group("source", "Group 1")]

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
        [_group("root", "Group 1"), _group("child", "Group 2", "root")],
        0,
        0,
        "ungroup",
        new_group_id="unused",
        new_group_name="Unused",
    )

    assert stack[0]["group_id"] == "root"
    assert [group["id"] for group in groups] == ["root"]
