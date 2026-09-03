from copy import deepcopy

from rastermint.core.layer_groups import group_effective_enabled_for_solo, step_effective_enabled_for_solo


def _group(group_id, parent_id="", enabled=True):
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


def test_group_solo_forces_selected_path_on_and_preserves_disabled_nested_group():
    groups = [
        _group("outer", enabled=False),
        _group("target", "outer", enabled=False),
        _group("nested", "target", enabled=False),
    ]
    direct = {"id": "direct", "enabled": True, "group_id": "target"}
    nested = {"id": "nested-layer", "enabled": True, "group_id": "nested"}
    outside = {"id": "outside", "enabled": True, "group_id": ""}

    assert step_effective_enabled_for_solo(direct, groups, solo_group_id="target") is True
    assert step_effective_enabled_for_solo(nested, groups, solo_group_id="target") is False
    assert step_effective_enabled_for_solo(outside, groups, solo_group_id="target") is False


def test_group_toggle_state_reflects_temporary_solo_scope():
    groups = [
        _group("outer", enabled=False),
        _group("target", "outer", enabled=False),
        _group("nested", "target", enabled=False),
        _group("other", enabled=True),
    ]
    stack = [{"id": "layer", "enabled": True, "group_id": "target"}]

    assert group_effective_enabled_for_solo("outer", stack, groups, solo_group_id="target") is True
    assert group_effective_enabled_for_solo("target", stack, groups, solo_group_id="target") is True
    assert group_effective_enabled_for_solo("nested", stack, groups, solo_group_id="target") is False
    assert group_effective_enabled_for_solo("other", stack, groups, solo_group_id="target") is False

    assert group_effective_enabled_for_solo("outer", stack, groups, solo_layer_id="layer") is True
    assert group_effective_enabled_for_solo("target", stack, groups, solo_layer_id="layer") is True
    assert group_effective_enabled_for_solo("other", stack, groups, solo_layer_id="layer") is False
