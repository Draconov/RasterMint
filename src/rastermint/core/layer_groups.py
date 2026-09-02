# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Iterable

MAX_GROUP_DEPTH = 5
_GROUP_NAME_RE = re.compile(r"^Group\s+(\d+)$")


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
        normalized.append({
            "id": group_id,
            "name": str(raw.get("name", "Layer Group") or "Layer Group"),
            "parent_id": str(raw.get("parent_id", "") or "").strip(),
            "collapsed": bool(raw.get("collapsed", False)),
            "enabled": bool(raw.get("enabled", True)),
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
        "collapsed": False,
        "enabled": True,
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
    for index in selected:
        copied_stack[index]["group_id"] = group_id
    return copied_stack, prune_layer_groups(copied_groups, copied_stack)


def ungroup_layers(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    indices: Iterable[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Move selected layers one level upward, keeping them inside any outer group."""
    copied_stack = _copy_stack(stack)
    copied_groups = canonicalize_layer_groups(list(groups))
    for index in sorted({int(index) for index in indices}):
        if not (0 <= index < len(copied_stack)):
            continue
        current = str(copied_stack[index].get("group_id", "") or "")
        copied_stack[index]["group_id"] = group_parent_id(current, copied_groups) if current else ""
    return copied_stack, prune_layer_groups(copied_groups, copied_stack)


def _reorder_layer(stack: list[dict[str, Any]], source: int, target: int, mode: str) -> list[dict[str, Any]]:
    if source == target:
        return stack
    item = stack.pop(source)
    adjusted_target = target - 1 if source < target else target
    insert_at = adjusted_target if mode == "before" else adjusted_target + 1
    insert_at = max(0, min(insert_at, len(stack)))
    stack.insert(insert_at, item)
    return stack


def drop_layer(
    stack: Iterable[dict[str, Any]],
    groups: Iterable[dict[str, Any]],
    source: int,
    target: int,
    mode: str,
    *,
    new_group_id: str,
    new_group_name: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply one layer drag/drop gesture to flat stack + nested group metadata."""
    copied_stack = _copy_stack(stack)
    copied_groups = canonicalize_layer_groups(list(groups))
    source = int(source)
    target = int(target)
    mode = str(mode or "before").lower()
    if not (0 <= source < len(copied_stack) and 0 <= target < len(copied_stack)):
        return copied_stack, copied_groups

    source_group = str(copied_stack[source].get("group_id", "") or "")
    if mode == "ungroup":
        if source_group:
            copied_stack[source]["group_id"] = group_parent_id(source_group, copied_groups)
        return copied_stack, prune_layer_groups(copied_groups, copied_stack)

    if source == target:
        return copied_stack, copied_groups
    if mode not in {"into", "before", "after"}:
        mode = "before"

    target_group = str(copied_stack[target].get("group_id", "") or "")

    if mode == "into":
        source_id = str(copied_stack[source].get("id", ""))
        target_id = str(copied_stack[target].get("id", ""))
        if source_group == target_group:
            parent_id = target_group
            if parent_id and group_depth(parent_id, copied_groups) >= MAX_GROUP_DEPTH:
                raise ValueError("Layer groups can be nested up to 5 levels")
            _add_group(copied_groups, group_id=new_group_id, name=new_group_name, parent_id=parent_id)
            for step in copied_stack:
                if str(step.get("id", "")) in {source_id, target_id}:
                    step["group_id"] = new_group_id
        elif target_group:
            copied_stack[source]["group_id"] = target_group
        else:
            _add_group(copied_groups, group_id=new_group_id, name=new_group_name, parent_id="")
            copied_stack[source]["group_id"] = new_group_id
            copied_stack[target]["group_id"] = new_group_id
        copied_stack = _reorder_layer(copied_stack, source, target, "after")
    else:
        if source_group and source_group != target_group:
            copied_stack[source]["group_id"] = group_parent_id(source_group, copied_groups)
        copied_stack = _reorder_layer(copied_stack, source, target, mode)

    return copied_stack, prune_layer_groups(copied_groups, copied_stack)


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
