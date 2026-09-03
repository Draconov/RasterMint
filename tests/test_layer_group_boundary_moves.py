from rastermint.core.layer_groups import move_layer_by_index


def _group(group_id: str, parent_id: str = "") -> dict:
    return {
        "id": group_id,
        "name": group_id,
        "parent_id": parent_id,
        "collapsed": False,
        "enabled": True,
        "opacity": 1.0,
        "blend_mode": "Normal",
        "color_label": "",
        "note": "",
    }


def test_moving_last_layer_down_steps_it_out_of_a_top_level_group():
    stack = [
        {"id": "a", "group_id": "g1"},
        {"id": "b", "group_id": "g1"},
        {"id": "c", "group_id": ""},
    ]

    updated_stack, updated_groups = move_layer_by_index(stack, [_group("g1")], 1, 2)

    assert [(step["id"], step.get("group_id", "")) for step in updated_stack] == [
        ("a", "g1"),
        ("c", ""),
        ("b", ""),
    ]
    assert [group["id"] for group in updated_groups] == ["g1"]


def test_moving_first_nested_layer_up_steps_it_to_the_parent_group():
    stack = [
        {"id": "outside", "group_id": ""},
        {"id": "a", "group_id": "child"},
        {"id": "b", "group_id": "child"},
        {"id": "tail", "group_id": "root"},
    ]
    groups = [_group("root"), _group("child", "root")]

    updated_stack, updated_groups = move_layer_by_index(stack, groups, 1, 0)

    assert [(step["id"], step.get("group_id", "")) for step in updated_stack] == [
        ("a", "root"),
        ("outside", ""),
        ("b", "child"),
        ("tail", "root"),
    ]
    assert [group["id"] for group in updated_groups] == ["root", "child"]


def test_regular_internal_move_keeps_the_direct_group_assignment():
    stack = [
        {"id": "a", "group_id": "g1"},
        {"id": "b", "group_id": "g1"},
        {"id": "c", "group_id": "g1"},
    ]

    updated_stack, _updated_groups = move_layer_by_index(stack, [_group("g1")], 1, 2)

    assert [(step["id"], step.get("group_id", "")) for step in updated_stack] == [
        ("a", "g1"),
        ("c", "g1"),
        ("b", "g1"),
    ]
