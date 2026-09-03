# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Iterable
from uuid import uuid4

MAX_GROUP_DEPTH = 5
_GROUP_NAME_RE = re.compile(r"^Group\s+(\d+)$")
_DEFAULT_GROUP_COLOR = ""
_DEFAULT_GROUP_NOTE = ""
_DEFAULT_GROUP_BLEND = "Normal"
_DEFAULT_GROUP_OPACITY = 1.0


def _group_map(groups: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(group.get("id", "")): group
        for group in groups
        if isinstance(group, dict) and str(group.get("id", ""))
    }


def group_path(group_id: str, groups: Iterable[dict[str, Any]]) -> list[str]:
    """Return group ancestry from root to *group_id* without looping forever."""
    by_id = _group_map(groups)
    current = str(group_id or "")
    if not current or current not in by_id:
        return []
    reverse_path: list[str] = []
    seen: set[str] = set()
    while current and current in by_id and current not in seen:
        seen.add(current)
        reverse_path.append(current)
        current = str(by_id[current].get("parent_id", "") or "")
    return list(reversed(reverse_path))


def group_depth(group_id: str, groups: Iterable[dict[str, Any]]) -> int:
    return len(group_path(group_id, groups))


def group_parent_id(group_id: str, groups: Iterable[dict[str, Any]]) -> str:
    group = _group_map(groups).get(str(group_id or ""))
    return str(group.get("parent_id", "") or "") if group else ""


def group_subtree_height(group_id: str, groups: Iterable[dict[str, Any]]) -> int:
    """Return deepest descendant distance including the group itself."""
    key = str(group_id or "")
    if not key:
        return 0
    normalized = list(groups)
    by_parent: dict[str, list[str]] = {}
    for group in normalized:
        gid = str(group.get("id", "") or "")
        parent_id = str(group.get("parent_id", "") or "")
        if gid:
            by_parent.setdefault(parent_id, []).append(gid)

    def visit(gid: str, seen: set[str]) -> int:
        if gid in seen:
            return 0
        next_seen = set(seen)
        next_seen.add(gid)
        child_heights = [visit(child, next_seen) for child in by_parent.get(gid, [])]
        return 1 + (max(child_heights) if child_heights else 0)

    return visit(key, set())


def can_reparent_group(
    group_id: str,
    new_parent_id: str,
    groups: Iterable[dict[str, Any]],
    *,
    max_depth: int = MAX_GROUP_DEPTH,
) -> bool:
    normalized = list(groups)
    by_id = _group_map(normalized)
    group_id = str(group_id or "")
    new_parent_id = str(new_parent_id or "")
    if group_id not in by_id:
        return False
    if not new_parent_id:
        return group_subtree_height(group_id, normalized) <= max_depth
    if new_parent_id not in by_id or new_parent_id == group_id:
        return False
    if group_id in group_path(new_parent_id, normalized):
        return False
    return group_depth(new_parent_id, normalized) + group_subtree_height(group_id, normalized) <= max_depth


def canonicalize_layer_groups(groups: Any) -> list[dict[str, Any]]:
    if not isinstance(groups, list):
        return []

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in groups:
        if not isinstance(raw, dict):
            continue
        group_id = str(raw.get("id", "") or "").strip()
        if not group_id or group_id in seen:
            continue
        seen.add(group_id)
        try:
            opacity = float(raw.get("opacity", _DEFAULT_GROUP_OPACITY) or _DEFAULT_GROUP_OPACITY)
        except (TypeError, ValueError):
            opacity = _DEFAULT_GROUP_OPACITY
        normalized.append({
            "id": group_id,
            "name": str(raw.get("name", "Layer Group") or "Layer Group"),
            "parent_id": str(raw.get("parent_id", "") or "").strip(),
            "collapsed": bool(raw.get("collapsed", False)),
            "enabled": bool(raw.get("enabled", True)),
            "opacity": max(0.0, min(1.0, opacity)),
            "blend_mode": str(raw.get("blend_mode", _DEFAULT_GROUP_BLEND) or _DEFAULT_GROUP_BLEND),
            "color_label": str(raw.get("color_label", _DEFAULT_GROUP_COLOR) or _DEFAULT_GROUP_COLOR).strip(),
            "note": str(raw.get("note", _DEFAULT_GROUP_NOTE) or _DEFAULT_GROUP_NOTE),
        })

    by_id = _group_map(normalized)
    for group in normalized:
        parent_id = str(group.get("parent_id", "") or "")
        if parent_id not in by_id or parent_id == group["id"]:
            group["parent_id"] = ""

    # Break cycles and reject imported hierarchies deeper than RasterMint's UI limit.
    for group in normalized:
        gid = str(group["id"])
        current = gid
        visited: set[str] = set()
        depth = 0
        while current and current in by_id:
            if current in visited:
                group["parent_id"] = ""
                break
            visited.add(current)
            depth += 1
            if depth > MAX_GROUP_DEPTH:
                group["parent_id"] = ""
                break
            current = str(by_id[current].get("parent_id", "") or "")

    return normalized


def next_group_name(groups: Iterable[dict[str, Any]]) -> str:
    used: set[int] = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        match = _GROUP_NAME_RE.match(str(group.get("name", "") or "").strip())
        if match:
            used.add(int(match.group(1)))
    number = 1
    while number in used:
        number += 1
    return f"Group {number}"


def prune_layer_groups(groups: Iterable[dict[str, Any]], stack: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = canonicalize_layer_groups(list(groups))
    by_id = _group_map(normalized)
    keep: set[str] = set()
    for step in stack:
        if not isinstance(step, dict):
            continue
        group_id = str(step.get("group_id", "") or "")
        if group_id in by_id:
            keep.update(group_path(group_id, normalized))
    return [dict(group) for group in normalized if str(group.get("id", "")) in keep]


def group_is_effectively_enabled(group_id: str, groups: Iterable[dict[str, Any]]) -> bool:
    normalized = list(groups)
    by_id = _group_map(normalized)
    path = group_path(group_id, normalized)
    return all(bool(by_id[gid].get("enabled", True)) for gid in path if gid in by_id)


def step_effective_enabled_for_solo(
    step: dict[str, Any],
    groups: Iterable[dict[str, Any]],
    *,
    solo_layer_id: str = "",
    solo_group_id: str = "",
) -> bool:
    """Return temporary runtime visibility without mutating authored enable flags."""
    normalized = list(groups)
    solo_layer_id = str(solo_layer_id or "")
    solo_group_id = str(solo_group_id or "")
    if solo_layer_id:
        return str(step.get("id", "")) == solo_layer_id

    visible = bool(step.get("enabled", True))
    group_id = str(step.get("group_id", "") or "")
    path = group_path(group_id, normalized)
    by_id = _group_map(normalized)
    if solo_group_id:
        if solo_group_id not in path or not visible:
            return False
        forced = set(group_path(solo_group_id, normalized))
        return all(
            gid in forced or bool(by_id.get(gid, {}).get("enabled", True))
            for gid in path
        )
    if group_id:
        return visible and group_is_effectively_enabled(group_id, normalized)
    return visible


def group_effective_enabled_for_solo(
    group_id: str,
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    *,
    solo_layer_id: str = "",
    solo_group_id: str = "",
) -> bool:
    """Return the checkbox state a group should show while solo is active."""
    normalized = list(groups)
    key = str(group_id or "")
    by_id = _group_map(normalized)
    group = by_id.get(key)
    if group is None:
        return False

    solo_layer_id = str(solo_layer_id or "")
    solo_group_id = str(solo_group_id or "")
    if solo_layer_id:
        target = next(
            (step for step in stack if str(step.get("id", "")) == solo_layer_id),
            None,
        )
        if target is None:
            return False
        return key in group_path(str(target.get("group_id", "") or ""), normalized)

    if solo_group_id:
        solo_path = group_path(solo_group_id, normalized)
        if key in solo_path:
            return True
        current_path = group_path(key, normalized)
        if solo_group_id in current_path:
            return bool(group.get("enabled", True))
        return False

    return bool(group.get("enabled", True))


def step_group_path(step: dict[str, Any], groups: Iterable[dict[str, Any]]) -> list[str]:
    return group_path(str(step.get("group_id", "") or ""), groups) if isinstance(step, dict) else []


def group_descendant_ids(group_id: str, groups: Iterable[dict[str, Any]]) -> list[str]:
    normalized = canonicalize_layer_groups(list(groups))
    target = str(group_id or "")
    if not target:
        return []
    result: list[str] = []
    for group in normalized:
        gid = str(group.get("id", "") or "")
        if gid and target in group_path(gid, normalized):
            result.append(gid)
    return result


def layer_indices_for_group(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    group_id: str,
) -> list[int]:
    normalized_groups = canonicalize_layer_groups(list(groups))
    target = str(group_id or "")
    if not target:
        return []
    result: list[int] = []
    for index, step in enumerate(stack):
        if target in step_group_path(step, normalized_groups):
            result.append(index)
    return result


def build_layer_group_view(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build QML-friendly group header/visibility metadata for each flat layer."""
    normalized = canonicalize_layer_groups(list(groups))
    by_id = _group_map(normalized)
    seen_headers: set[str] = set()
    result: list[dict[str, Any]] = []

    for step in stack:
        direct_group_id = str(step.get("group_id", "") or "") if isinstance(step, dict) else ""
        path = group_path(direct_group_id, normalized)
        headers: list[dict[str, Any]] = []
        content_visible = True
        for depth, gid in enumerate(path, start=1):
            group = by_id[gid]
            if gid not in seen_headers:
                headers.append({
                    "id": gid,
                    "name": str(group.get("name", "Layer Group") or "Layer Group"),
                    "parent_id": str(group.get("parent_id", "") or ""),
                    "depth": depth,
                    "collapsed": bool(group.get("collapsed", False)),
                    "enabled": bool(group.get("enabled", True)),
                    "opacity": float(group.get("opacity", _DEFAULT_GROUP_OPACITY) or _DEFAULT_GROUP_OPACITY),
                    "blend_mode": str(group.get("blend_mode", _DEFAULT_GROUP_BLEND) or _DEFAULT_GROUP_BLEND),
                    "color_label": str(group.get("color_label", _DEFAULT_GROUP_COLOR) or _DEFAULT_GROUP_COLOR),
                    "note": str(group.get("note", _DEFAULT_GROUP_NOTE) or _DEFAULT_GROUP_NOTE),
                })
                seen_headers.add(gid)
            if bool(group.get("collapsed", False)):
                content_visible = False
                break

        result.append({
            "group_path": path,
            "group_depth": len(path),
            "group_headers": headers,
            "content_visible": content_visible,
        })
    return result


def _copy_stack(stack: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [deepcopy(step) for step in stack if isinstance(step, dict)]


def _add_group(
    groups: list[dict[str, Any]],
    *,
    group_id: str,
    name: str,
    parent_id: str = "",
    collapsed: bool = False,
    enabled: bool = True,
    opacity: float = _DEFAULT_GROUP_OPACITY,
    blend_mode: str = _DEFAULT_GROUP_BLEND,
    color_label: str = _DEFAULT_GROUP_COLOR,
    note: str = _DEFAULT_GROUP_NOTE,
) -> list[dict[str, Any]]:
    group_id = str(group_id or "").strip()
    if not group_id or group_id in _group_map(groups):
        raise ValueError("Layer group id must be unique")
    parent_id = str(parent_id or "")
    if parent_id and group_depth(parent_id, groups) >= MAX_GROUP_DEPTH:
        raise ValueError("Layer groups can be nested up to 5 levels")
    groups.append({
        "id": group_id,
        "name": str(name or "Layer Group").strip() or "Layer Group",
        "parent_id": parent_id,
        "collapsed": bool(collapsed),
        "enabled": bool(enabled),
        "opacity": max(0.0, min(1.0, float(opacity))),
        "blend_mode": str(blend_mode or _DEFAULT_GROUP_BLEND),
        "color_label": str(color_label or _DEFAULT_GROUP_COLOR).strip(),
        "note": str(note or _DEFAULT_GROUP_NOTE),
    })
    return groups


def create_layer_group(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    indices: Iterable[int],
    *,
    group_id: str,
    group_name: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Create a group around selected layers, nesting under their shared parent."""
    copied_stack = _copy_stack(stack)
    copied_groups = canonicalize_layer_groups(list(groups))
    selected = sorted({int(index) for index in indices if 0 <= int(index) < len(copied_stack)})
    if not selected:
        return copied_stack, copied_groups
    direct_groups = {str(copied_stack[index].get("group_id", "") or "") for index in selected}
    parent_id = next(iter(direct_groups)) if len(direct_groups) == 1 else ""
    if parent_id and group_depth(parent_id, copied_groups) >= MAX_GROUP_DEPTH:
        raise ValueError("Layer groups can be nested up to 5 levels")

    _add_group(copied_groups, group_id=group_id, name=group_name, parent_id=parent_id)

    selected_set = set(selected)
    grouped_steps = [copied_stack[index] for index in selected]
    for step in grouped_steps:
        step["group_id"] = group_id
    remaining = [step for index, step in enumerate(copied_stack) if index not in selected_set]
    insert_at = selected[0]
    copied_stack = remaining[:insert_at] + grouped_steps + remaining[insert_at:]
    return copied_stack, prune_layer_groups(copied_groups, copied_stack)


def ungroup_layers(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    indices: Iterable[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Move selected layers one level upward without splitting their old group."""
    copied_stack = _copy_stack(stack)
    copied_groups = canonicalize_layer_groups(list(groups))
    selected = sorted({int(index) for index in indices if 0 <= int(index) < len(copied_stack)})
    layer_ids = [str(copied_stack[index].get("id", "") or "") for index in selected]
    copied_stack = _ungroup_layer_ids(copied_stack, copied_groups, layer_ids)
    return copied_stack, prune_layer_groups(copied_groups, copied_stack)


def ungroup_layer_group(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    group_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Dissolve a group while keeping child layers/groups in the same place."""
    copied_stack = _copy_stack(stack)
    copied_groups = canonicalize_layer_groups(list(groups))
    target = str(group_id or "")
    by_id = _group_map(copied_groups)
    if target not in by_id:
        return copied_stack, copied_groups
    parent_id = group_parent_id(target, copied_groups)
    for step in copied_stack:
        if str(step.get("group_id", "") or "") == target:
            step["group_id"] = parent_id
    updated_groups: list[dict[str, Any]] = []
    for group in copied_groups:
        gid = str(group.get("id", "") or "")
        if gid == target:
            continue
        row = dict(group)
        if str(row.get("parent_id", "") or "") == target:
            row["parent_id"] = parent_id
        updated_groups.append(row)
    return copied_stack, prune_layer_groups(updated_groups, copied_stack)


def _reorder_layer(stack: list[dict[str, Any]], source: int, target: int, mode: str) -> list[dict[str, Any]]:
    if source == target:
        return stack
    item = stack.pop(source)
    adjusted_target = target - 1 if source < target else target
    insert_at = adjusted_target if mode == "before" else adjusted_target + 1
    insert_at = max(0, min(insert_at, len(stack)))
    stack.insert(insert_at, item)
    return stack


def _last_index_in_group(
    stack: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    group_id: str,
) -> int:
    target = str(group_id or "")
    result = -1
    for index, step in enumerate(stack):
        if target and target in step_group_path(step, groups):
            result = index
    return result


def _direct_group_member_indices(stack: list[dict[str, Any]], group_id: str) -> list[int]:
    target = str(group_id or "")
    if not target:
        return []
    return [
        index
        for index, step in enumerate(stack)
        if str(step.get("group_id", "") or "") == target
    ]


def _layer_index_by_id(stack: list[dict[str, Any]], layer_id: str) -> int:
    target = str(layer_id or "")
    return next(
        (index for index, step in enumerate(stack) if str(step.get("id", "") or "") == target),
        -1,
    )


def _move_layer_across_group_block(
    stack: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    source: int,
    group_id: str,
    direction: int,
) -> list[dict[str, Any]]:
    """Move one direct layer across an adjacent child-group subtree atomically."""
    if not (0 <= source < len(stack)):
        return stack
    item = stack.pop(source)
    block = layer_indices_for_group(stack, groups, group_id)
    if not block:
        stack.insert(max(0, min(source, len(stack))), item)
        return stack
    insert_at = min(block) if direction < 0 else max(block) + 1
    stack.insert(insert_at, item)
    return stack


def _shared_boundary_group(
    stack: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    target_id: str,
    mode: str,
) -> str:
    """Return the deepest group shared across the requested insertion edge.

    This lets an ungrouped layer join a group only when the user drops it
    *inside* that group's contiguous block. Dropping at the outer top/bottom
    edge of the block keeps the layer in its current/root container.
    """
    target_index = _layer_index_by_id(stack, target_id)
    if target_index < 0:
        return ""
    neighbor_index = target_index - 1 if mode == "before" else target_index + 1
    if not (0 <= neighbor_index < len(stack)):
        return ""

    target_path = step_group_path(stack[target_index], groups)
    neighbor_path = step_group_path(stack[neighbor_index], groups)
    shared: list[str] = []
    for left, right in zip(target_path, neighbor_path):
        if left != right:
            break
        shared.append(left)
    return shared[-1] if shared else ""


def _insert_layer_relative_in_container(
    stack: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    item: dict[str, Any],
    destination_group: str,
    target_id: str,
    mode: str,
    *,
    fallback_index: int,
) -> list[dict[str, Any]]:
    """Insert *item* at a legal sibling boundary in destination_group."""
    destination_group = str(destination_group or "")
    item["group_id"] = destination_group
    target_index = _layer_index_by_id(stack, target_id)
    if target_index < 0:
        stack.insert(max(0, min(fallback_index, len(stack))), item)
        return stack

    target_group = str(stack[target_index].get("group_id", "") or "")
    unit_start = target_index
    unit_end = target_index

    if destination_group:
        target_path = group_path(target_group, groups)
        if target_group == destination_group:
            pass
        elif destination_group in target_path:
            child_index = target_path.index(destination_group) + 1
            if child_index < len(target_path):
                child_group = target_path[child_index]
                block = layer_indices_for_group(stack, groups, child_group)
                if block:
                    unit_start, unit_end = min(block), max(block)
        else:
            # The target is outside the container the layer is allowed to join.
            # Stay at the nearest edge of that container rather than splitting it.
            destination_block = layer_indices_for_group(stack, groups, destination_group)
            if destination_block:
                insert_at = min(destination_block) if target_index < min(destination_block) else max(destination_block) + 1
            else:
                insert_at = max(0, min(fallback_index, len(stack)))
            stack.insert(insert_at, item)
            return stack
    elif target_group:
        target_path = group_path(target_group, groups)
        top_group = target_path[0] if target_path else target_group
        block = layer_indices_for_group(stack, groups, top_group)
        if block:
            unit_start, unit_end = min(block), max(block)

    insert_at = unit_start if mode == "before" else unit_end + 1
    stack.insert(insert_at, item)
    return stack


def _ungroup_layer_ids(
    stack: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    layer_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Move each requested layer one hierarchy level out without splitting groups."""
    wanted = {str(layer_id or "") for layer_id in layer_ids if str(layer_id or "")}
    if not wanted:
        return stack

    original_group = {
        str(step.get("id", "") or ""): str(step.get("group_id", "") or "")
        for step in stack
        if str(step.get("id", "") or "") in wanted
    }
    group_ids = sorted(
        {gid for gid in original_group.values() if gid},
        key=lambda gid: group_depth(gid, groups),
        reverse=True,
    )

    for group_id in group_ids:
        moving_ids = {
            layer_id for layer_id, direct_group in original_group.items()
            if direct_group == group_id
        }
        if not moving_ids:
            continue

        current_block = layer_indices_for_group(stack, groups, group_id)
        if not current_block:
            continue
        block_start = min(current_block)
        block_end = max(current_block)
        after_anchor_id = ""
        for index in range(block_end + 1, len(stack)):
            candidate_id = str(stack[index].get("id", "") or "")
            if candidate_id not in moving_ids:
                after_anchor_id = candidate_id
                break

        parent_id = group_parent_id(group_id, groups)
        moved_steps: list[dict[str, Any]] = []
        remaining: list[dict[str, Any]] = []
        for step in stack:
            layer_id = str(step.get("id", "") or "")
            if layer_id in moving_ids:
                step["group_id"] = parent_id
                moved_steps.append(step)
            else:
                remaining.append(step)

        remaining_block = layer_indices_for_group(remaining, groups, group_id)
        if remaining_block:
            insert_at = max(remaining_block) + 1
        elif after_anchor_id:
            anchor_index = _layer_index_by_id(remaining, after_anchor_id)
            insert_at = anchor_index if anchor_index >= 0 else len(remaining)
        else:
            insert_at = min(block_start, len(remaining))
        stack = remaining[:insert_at] + moved_steps + remaining[insert_at:]

    return stack


def move_layer_by_index(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    source: int,
    target: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Move one layer while treating nested group subtrees as atomic siblings."""
    copied_stack = _copy_stack(stack)
    copied_groups = canonicalize_layer_groups(list(groups))
    source = int(source)
    target = int(target)
    if not (0 <= source < len(copied_stack) and 0 <= target < len(copied_stack)):
        return copied_stack, copied_groups
    if source == target:
        return copied_stack, copied_groups

    # The UI arrow controls request adjacent moves. Keep legacy behavior for
    # non-adjacent programmatic callers rather than inventing multi-step nesting.
    if abs(target - source) != 1:
        item = copied_stack.pop(source)
        copied_stack.insert(target, item)
        return copied_stack, prune_layer_groups(copied_groups, copied_stack)

    direction = 1 if target > source else -1
    source_group = str(copied_stack[source].get("group_id", "") or "")
    target_group = str(copied_stack[target].get("group_id", "") or "")

    if source_group:
        source_block = layer_indices_for_group(copied_stack, copied_groups, source_group)
        target_inside_source = target in set(source_block)

        # Crossing out of a group's flat boundary is a one-level ungroup. Do
        # not also jump across an unrelated parent/sibling block in the same click.
        at_boundary = bool(source_block) and (
            (direction < 0 and source == min(source_block))
            or (direction > 0 and source == max(source_block))
        )
        if not target_inside_source and at_boundary:
            parent_id = group_parent_id(source_group, copied_groups)
            copied_stack[source]["group_id"] = parent_id
            if target_group == parent_id:
                item = copied_stack.pop(source)
                copied_stack.insert(target, item)
            return copied_stack, prune_layer_groups(copied_groups, copied_stack)

        # A direct layer moving over a nested child group must cross the whole
        # child subtree, never one flat row from its middle.
        target_path = group_path(target_group, copied_groups)
        if source_group in target_path and target_group != source_group:
            child_index = target_path.index(source_group) + 1
            if child_index < len(target_path):
                child_group = target_path[child_index]
                copied_stack = _move_layer_across_group_block(
                    copied_stack,
                    copied_groups,
                    source,
                    child_group,
                    direction,
                )
                return copied_stack, prune_layer_groups(copied_groups, copied_stack)

        if source_group == target_group:
            item = copied_stack.pop(source)
            copied_stack.insert(target, item)
            return copied_stack, prune_layer_groups(copied_groups, copied_stack)

        # This branch mainly repairs already-inconsistent old stacks. The moved
        # layer adopts the target's direct container instead of splitting it.
        copied_stack[source]["group_id"] = target_group
        item = copied_stack.pop(source)
        copied_stack.insert(target, item)
        return copied_stack, prune_layer_groups(copied_groups, copied_stack)

    # A top-level layer crossing a top-level group treats that group as one row.
    if target_group:
        target_path = group_path(target_group, copied_groups)
        top_group = target_path[0] if target_path else target_group
        copied_stack = _move_layer_across_group_block(
            copied_stack,
            copied_groups,
            source,
            top_group,
            direction,
        )
        return copied_stack, prune_layer_groups(copied_groups, copied_stack)

    item = copied_stack.pop(source)
    copied_stack.insert(target, item)
    return copied_stack, prune_layer_groups(copied_groups, copied_stack)


def drop_layer(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    source: int,
    target: int,
    mode: str,
    *,
    new_group_id: str,
    new_group_name: str,
    target_group_id: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply one layer drag/drop gesture without breaking group contiguity."""
    copied_stack = _copy_stack(stack)
    copied_groups = canonicalize_layer_groups(list(groups))
    source = int(source)
    target = int(target)
    mode = str(mode or "before").lower()
    if not (0 <= source < len(copied_stack) and 0 <= target < len(copied_stack)):
        return copied_stack, copied_groups

    source_id = str(copied_stack[source].get("id", "") or "")
    source_group = str(copied_stack[source].get("group_id", "") or "")
    if mode == "ungroup":
        if source_group:
            copied_stack = _ungroup_layer_ids(copied_stack, copied_groups, [source_id])
        return copied_stack, prune_layer_groups(copied_groups, copied_stack)

    if source == target:
        return copied_stack, copied_groups
    if mode not in {"into", "before", "after"}:
        mode = "before"

    target_id = str(copied_stack[target].get("id", "") or "")
    target_group = str(copied_stack[target].get("group_id", "") or "")
    requested_group = str(target_group_id or "")

    if mode == "into":
        effective_target_group = requested_group or target_group

        # Dropping onto the current group header simply moves the layer to the
        # end of that group; it must not create a nested group by accident.
        if requested_group and effective_target_group == source_group:
            item = copied_stack.pop(source)
            remaining_block = layer_indices_for_group(copied_stack, copied_groups, effective_target_group)
            insert_at = max(remaining_block) + 1 if remaining_block else min(source, len(copied_stack))
            copied_stack.insert(insert_at, item)

        # Dropping one layer onto another layer in the same container creates a
        # subgroup, which is RasterMint's intentional auto-group gesture.
        elif effective_target_group and source_group == effective_target_group and not requested_group:
            parent_id = effective_target_group
            if parent_id and group_depth(parent_id, copied_groups) >= MAX_GROUP_DEPTH:
                raise ValueError("Layer groups can be nested up to 5 levels")
            _add_group(copied_groups, group_id=new_group_id, name=new_group_name, parent_id=parent_id)
            for step in copied_stack:
                if str(step.get("id", "") or "") in {source_id, target_id}:
                    step["group_id"] = new_group_id
            copied_stack = _reorder_layer(copied_stack, source, target, "after")

        elif effective_target_group:
            item = copied_stack.pop(source)
            item["group_id"] = effective_target_group
            if requested_group:
                # Header drops target the whole group, not whichever descendant
                # layer happened to carry that header in the flat ListView.
                remaining_block = layer_indices_for_group(copied_stack, copied_groups, effective_target_group)
                insert_at = max(remaining_block) + 1 if remaining_block else len(copied_stack)
            else:
                remaining_target = _layer_index_by_id(copied_stack, target_id)
                insert_at = remaining_target + 1 if remaining_target >= 0 else len(copied_stack)
            copied_stack.insert(insert_at, item)

        else:
            # Two top-level layers dropped onto each other create a new group.
            _add_group(copied_groups, group_id=new_group_id, name=new_group_name, parent_id="")
            for step in copied_stack:
                if str(step.get("id", "") or "") in {source_id, target_id}:
                    step["group_id"] = new_group_id
            copied_stack = _reorder_layer(copied_stack, source, target, "after")

    else:
        # Edge drops are reorders. For an ungrouped layer, an insertion edge
        # that lies *inside* a group's contiguous block adopts the deepest group
        # shared by the two layers bordering that edge. An outer edge remains
        # top-level. This makes dropping between two group children intuitive
        # without making ordinary above/below-group reorders implicit grouping.
        item = copied_stack.pop(source)
        if source_group:
            destination_group = source_group
            if source_group != target_group:
                destination_group = group_parent_id(source_group, copied_groups)
        else:
            destination_group = _shared_boundary_group(
                copied_stack, copied_groups, target_id, mode
            )
        copied_stack = _insert_layer_relative_in_container(
            copied_stack,
            copied_groups,
            item,
            destination_group,
            target_id,
            mode,
            fallback_index=source,
        )

    return copied_stack, prune_layer_groups(copied_groups, copied_stack)


def move_layer_group(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    source_group_id: str,
    target_index: int,
    mode: str = "before",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Move an entire group subtree as one contiguous block.

    A normal group drag is a reorder operation, not a grouping gesture. The
    source group's child layers/nested groups keep their internal structure,
    while the source group itself moves into the target layer's container so
    the flat stack remains visually contiguous.
    """
    copied_stack = _copy_stack(stack)
    copied_groups = canonicalize_layer_groups(list(groups))
    source_group_id = str(source_group_id or "")
    target_index = int(target_index)
    mode = str(mode or "before").lower()
    if mode not in {"before", "after"}:
        mode = "before"

    by_id = _group_map(copied_groups)
    if source_group_id not in by_id or not (0 <= target_index < len(copied_stack)):
        return copied_stack, copied_groups

    source_indices = layer_indices_for_group(copied_stack, copied_groups, source_group_id)
    if not source_indices or target_index in set(source_indices):
        return copied_stack, copied_groups

    target_step = copied_stack[target_index]
    target_id = str(target_step.get("id", "") or "")
    target_group_id = str(target_step.get("group_id", "") or "")

    # The group becomes a sibling of the target layer. If that layer is inside
    # another group this means moving the source group into that same container;
    # dropping onto a group header is handled separately by reparent_layer_group.
    if target_group_id != group_parent_id(source_group_id, copied_groups):
        if not can_reparent_group(source_group_id, target_group_id, copied_groups):
            raise ValueError("Layer groups can be nested up to 5 levels")
        for group in copied_groups:
            if str(group.get("id", "") or "") == source_group_id:
                group["parent_id"] = target_group_id
                break

    source_set = set(source_indices)
    moved_steps = [copied_stack[index] for index in source_indices]
    remaining = [step for index, step in enumerate(copied_stack) if index not in source_set]
    remaining_target = next(
        (index for index, step in enumerate(remaining) if str(step.get("id", "") or "") == target_id),
        -1,
    )
    if remaining_target < 0:
        return copied_stack, copied_groups

    insert_at = remaining_target if mode == "before" else remaining_target + 1
    updated_stack = remaining[:insert_at] + moved_steps + remaining[insert_at:]
    return updated_stack, prune_layer_groups(copied_groups, updated_stack)


def reparent_layer_group(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    source_group_id: str,
    target_group_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Nest a group inside another and move its complete subtree into that block."""
    copied_stack = _copy_stack(stack)
    copied_groups = canonicalize_layer_groups(list(groups))
    source_group_id = str(source_group_id or "")
    target_group_id = str(target_group_id or "")
    by_id = _group_map(copied_groups)
    if source_group_id not in by_id or target_group_id not in by_id:
        return copied_stack, copied_groups
    if source_group_id == target_group_id or group_parent_id(source_group_id, copied_groups) == target_group_id:
        return copied_stack, copied_groups
    if not can_reparent_group(source_group_id, target_group_id, copied_groups):
        raise ValueError("Layer groups can be nested up to 5 levels")

    source_indices = layer_indices_for_group(copied_stack, copied_groups, source_group_id)
    if not source_indices:
        return copied_stack, copied_groups
    source_set = set(source_indices)
    moved_steps = [copied_stack[index] for index in source_indices]
    remaining = [step for index, step in enumerate(copied_stack) if index not in source_set]
    fallback = min(source_indices)

    for group in copied_groups:
        if str(group.get("id", "") or "") == source_group_id:
            group["parent_id"] = target_group_id
            break

    target_block = layer_indices_for_group(remaining, copied_groups, target_group_id)
    insert_at = max(target_block) + 1 if target_block else min(fallback, len(remaining))
    updated_stack = remaining[:insert_at] + moved_steps + remaining[insert_at:]
    return updated_stack, prune_layer_groups(copied_groups, updated_stack)


def drop_group_on_layer(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    source_group_id: str,
    target_index: int,
    *,
    new_group_id: str,
    new_group_name: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Nest a group on another group/layer, creating a parent group when needed."""
    copied_stack = _copy_stack(stack)
    copied_groups = canonicalize_layer_groups(list(groups))
    source_group_id = str(source_group_id or "")
    target_index = int(target_index)
    by_id = _group_map(copied_groups)
    if source_group_id not in by_id or not (0 <= target_index < len(copied_stack)):
        return copied_stack, copied_groups

    target_group = str(copied_stack[target_index].get("group_id", "") or "")
    if source_group_id in group_path(target_group, copied_groups):
        return copied_stack, copied_groups

    source_parent = group_parent_id(source_group_id, copied_groups)
    target_parent = group_parent_id(target_group, copied_groups) if target_group else ""

    if target_group and target_group != source_parent:
        if not can_reparent_group(source_group_id, target_group, copied_groups):
            raise ValueError("Layer groups can be nested up to 5 levels")
        for group in copied_groups:
            if str(group.get("id", "")) == source_group_id:
                group["parent_id"] = target_group
                break
    else:
        # Source group and target layer currently share a container. Create a
        # new group inside that container and put both under it.
        parent_id = source_parent if target_group == source_parent else ""
        parent_depth = group_depth(parent_id, copied_groups) if parent_id else 0
        if parent_depth + 1 + group_subtree_height(source_group_id, copied_groups) > MAX_GROUP_DEPTH:
            raise ValueError("Layer groups can be nested up to 5 levels")
        _add_group(copied_groups, group_id=new_group_id, name=new_group_name, parent_id=parent_id)
        for group in copied_groups:
            if str(group.get("id", "")) == source_group_id:
                group["parent_id"] = new_group_id
                break
        copied_stack[target_index]["group_id"] = new_group_id

    return copied_stack, prune_layer_groups(copied_groups, copied_stack)


def duplicate_layer_group(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    group_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Duplicate an entire group subtree with all of its layers."""
    copied_stack = _copy_stack(stack)
    copied_groups = canonicalize_layer_groups(list(groups))
    target = str(group_id or "")
    by_id = _group_map(copied_groups)
    if target not in by_id:
        return copied_stack, copied_groups, ""

    member_indices = layer_indices_for_group(copied_stack, copied_groups, target)
    if not member_indices:
        return copied_stack, copied_groups, ""

    subtree_ids = group_descendant_ids(target, copied_groups)
    id_map = {old_id: f"group-{uuid4().hex[:10]}" for old_id in subtree_ids}

    cloned_groups: list[dict[str, Any]] = []
    for old_id in subtree_ids:
        original = by_id[old_id]
        clone = dict(original)
        clone["id"] = id_map[old_id]
        parent_id = str(original.get("parent_id", "") or "")
        clone["parent_id"] = id_map[parent_id] if parent_id in id_map else parent_id
        if old_id == target:
            clone["name"] = f"{str(original.get('name', 'Layer Group') or 'Layer Group')} Copy"
        cloned_groups.append(clone)

    cloned_layers: list[dict[str, Any]] = []
    for index in member_indices:
        step = deepcopy(copied_stack[index])
        step["id"] = f"effect-{uuid4().hex[:10]}"
        direct_group = str(step.get("group_id", "") or "")
        if direct_group in id_map:
            step["group_id"] = id_map[direct_group]
        cloned_layers.append(step)

    insert_at = member_indices[-1] + 1
    copied_stack[insert_at:insert_at] = cloned_layers
    copied_groups.extend(cloned_groups)
    duplicated_group_id = id_map.get(target, "")
    return copied_stack, prune_layer_groups(copied_groups, copied_stack), duplicated_group_id
