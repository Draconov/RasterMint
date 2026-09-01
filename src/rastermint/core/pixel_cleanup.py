# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np
from PIL import Image


_NEIGHBOURS_8: tuple[tuple[int, int], ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),            (0, 1),
    (1, -1),  (1, 0),   (1, 1),
)


@dataclass(slots=True)
class _RunTable:
    """Compact run-length connected-component table.

    Pixel art can alternate color every pixel, so storing one Python object per
    run becomes surprisingly expensive on large dithered images.  All run
    fields live in contiguous NumPy arrays instead.
    """

    row_offsets: np.ndarray
    y: np.ndarray
    x0: np.ndarray
    x1: np.ndarray
    color: np.ndarray
    root: np.ndarray
    component_size: np.ndarray


def _encode_rgb(arr: np.ndarray) -> np.ndarray:
    work = np.asarray(arr, dtype=np.uint32)
    return (work[..., 0] << 16) | (work[..., 1] << 8) | work[..., 2]


def _decode_color(value: int) -> np.ndarray:
    return np.asarray([(value >> 16) & 255, (value >> 8) & 255, value & 255], dtype=np.uint8)


def _edge_strength(arr: np.ndarray) -> np.ndarray:
    rgb = np.asarray(arr, dtype=np.float32)
    lum = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    pad = np.pad(lum, 1, mode="edge")
    gx = np.abs(pad[1:-1, 2:] - pad[1:-1, :-2])
    gy = np.abs(pad[2:, 1:-1] - pad[:-2, 1:-1])
    return np.clip((gx + gy) / 510.0, 0.0, 1.0).astype(np.float32)


def _same_neighbour_count(ids: np.ndarray) -> np.ndarray:
    pad = np.pad(ids, 1, mode="edge")
    h, w = ids.shape
    out = np.zeros((h, w), dtype=np.uint8)
    for dy, dx in _NEIGHBOURS_8:
        neighbour = pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        out += (neighbour == ids).astype(np.uint8)
    return out


def _coordinate_gate(shape: tuple[int, int], amount: float, salt: int) -> np.ndarray:
    amount = max(0.0, min(1.0, float(amount)))
    if amount <= 0.0:
        return np.zeros(shape, dtype=bool)
    if amount >= 1.0:
        return np.ones(shape, dtype=bool)
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.uint64)
    value = (xx * np.uint64(0x9E3779B185EBCA87) + yy * np.uint64(0xC2B2AE3D27D4EB4F) + np.uint64(salt))
    value ^= value >> np.uint64(29)
    value *= np.uint64(0x165667B19E3779F9)
    value ^= value >> np.uint64(32)
    threshold = int(round(amount * 65535.0))
    return (value & np.uint64(0xFFFF)) <= np.uint64(threshold)


def _edge_allowed(edge: np.ndarray, preservation: float) -> np.ndarray:
    preservation = max(0.0, min(1.0, float(preservation)))
    if preservation <= 0.0:
        return np.ones(edge.shape, dtype=bool)
    # 100% preservation protects even moderately strong image edges. Lower
    # values progressively allow cleanup to cross stronger gradients.
    limit = 1.0 - 0.86 * preservation
    return edge <= max(0.08, limit)


def _representative_neighbour(arr: np.ndarray) -> np.ndarray:
    """Choose an existing neighbouring colour closest to the local mean.

    The function never invents a new colour, which is important when cleanup
    follows a palette-limited dither layer. It deliberately avoids stacking all
    eight neighbours into one H×W×8×3 float array so large images stay bounded.
    """
    h, w = arr.shape[:2]
    pad = np.pad(arr, ((1, 1), (1, 1), (0, 0)), mode="edge")
    total = np.zeros((h, w, 3), dtype=np.float32)
    views: list[np.ndarray] = []
    for dy, dx in _NEIGHBOURS_8:
        view = pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        views.append(view)
        total += view.astype(np.float32)
    mean = total / 8.0
    best_distance = np.full((h, w), np.inf, dtype=np.float32)
    selected = arr.copy()
    for view in views:
        work = view.astype(np.float32)
        distance = np.sum((work - mean) ** 2, axis=2)
        better = distance < best_distance
        selected[better] = view[better]
        best_distance[better] = distance[better]
    return selected


def _staircase_candidates(ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h, w = ids.shape
    mask = np.zeros((h, w), dtype=bool)
    replacement = ids.copy()
    if h < 2 or w < 2:
        return mask, replacement

    a = ids[:-1, :-1]
    b = ids[:-1, 1:]
    c = ids[1:, :-1]
    d = ids[1:, 1:]

    cases = (
        ((b == c) & (c == d) & (a != b), (slice(None, -1), slice(None, -1)), b),
        ((a == c) & (c == d) & (b != a), (slice(None, -1), slice(1, None)), a),
        ((a == b) & (b == d) & (c != a), (slice(1, None), slice(None, -1)), a),
        ((a == b) & (b == c) & (d != a), (slice(1, None), slice(1, None)), a),
    )
    for case, target, majority in cases:
        target_mask = mask[target]
        target_repl = replacement[target]
        target_mask |= case
        target_repl[case] = majority[case]
    return mask, replacement


def _line_gap_candidates(ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h, w = ids.shape
    pad = np.pad(ids, 1, mode="edge")
    center = ids
    left = pad[1:1 + h, 0:w]
    right = pad[1:1 + h, 2:2 + w]
    up = pad[0:h, 1:1 + w]
    down = pad[2:2 + h, 1:1 + w]
    ul = pad[0:h, 0:w]
    ur = pad[0:h, 2:2 + w]
    dl = pad[2:2 + h, 0:w]
    dr = pad[2:2 + h, 2:2 + w]

    horizontal = (left == right) & (center != left)
    vertical = (up == down) & (center != up)
    diag_a = (ul == dr) & (center != ul)
    diag_b = (ur == dl) & (center != ur)

    mask = horizontal | vertical | diag_a | diag_b
    replacement = center.copy()
    replacement[diag_b] = ur[diag_b]
    replacement[diag_a] = ul[diag_a]
    replacement[vertical] = up[vertical]
    replacement[horizontal] = left[horizontal]
    return mask, replacement


def _build_runs(ids: np.ndarray, connectivity: int) -> _RunTable:
    """Build same-color connected components using compact horizontal runs."""
    h, w = ids.shape
    row_offsets = np.zeros(h + 1, dtype=np.int64)
    x0_parts: list[np.ndarray] = []
    x1_parts: list[np.ndarray] = []
    color_parts: list[np.ndarray] = []

    for y in range(h):
        row = ids[y]
        boundaries = (np.flatnonzero(row[1:] != row[:-1]) + 1).astype(np.int32) if w > 1 else np.empty(0, dtype=np.int32)
        starts = np.concatenate((np.asarray([0], dtype=np.int32), boundaries))
        ends = np.concatenate((boundaries, np.asarray([w], dtype=np.int32)))
        x0_parts.append(starts)
        x1_parts.append(ends)
        color_parts.append(row[starts].astype(np.uint32, copy=False))
        row_offsets[y + 1] = row_offsets[y] + len(starts)

    n = int(row_offsets[-1])
    if n == 0:
        empty_i = np.empty(0, dtype=np.int32)
        return _RunTable(row_offsets, empty_i, empty_i, empty_i, np.empty(0, dtype=np.uint32), empty_i, empty_i)

    counts = np.diff(row_offsets).astype(np.int32, copy=False)
    y_index = np.repeat(np.arange(h, dtype=np.int32), counts)
    x0 = np.concatenate(x0_parts).astype(np.int32, copy=False)
    x1 = np.concatenate(x1_parts).astype(np.int32, copy=False)
    color = np.concatenate(color_parts).astype(np.uint32, copy=False)
    parent = np.arange(n, dtype=np.int32)
    comp_size = (x1 - x0).astype(np.int32, copy=True)

    def find(index: int) -> int:
        root = index
        while int(parent[root]) != root:
            root = int(parent[root])
        while int(parent[index]) != index:
            nxt = int(parent[index])
            parent[index] = root
            index = nxt
        return root

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if int(comp_size[ra]) < int(comp_size[rb]):
            ra, rb = rb, ra
        parent[rb] = ra
        comp_size[ra] += comp_size[rb]

    margin = 1 if int(connectivity) == 8 else 0
    for y in range(1, h):
        p0, p1 = int(row_offsets[y - 1]), int(row_offsets[y])
        c0, c1 = int(row_offsets[y]), int(row_offsets[y + 1])
        j = p0
        for ci in range(c0, c1):
            left = int(x0[ci]) - margin
            right = int(x1[ci]) - 1 + margin
            while j < p1 and int(x1[j]) - 1 < left:
                j += 1
            k = j
            while k < p1 and int(x0[k]) <= right:
                if color[k] == color[ci] and int(x1[k]) - 1 >= left:
                    union(ci, k)
                k += 1

    root = np.empty(n, dtype=np.int32)
    for index in range(n):
        root[index] = find(index)
    component_size = comp_size[root].astype(np.int32, copy=False)
    return _RunTable(row_offsets, y_index, x0, x1, color, root, component_size)

def _small_component_mask(
    ids: np.ndarray,
    *,
    max_size: int,
    connectivity: int,
) -> tuple[np.ndarray, _RunTable]:
    max_size = max(0, int(max_size))
    mask = np.zeros(ids.shape, dtype=bool)
    table = _build_runs(ids, connectivity)
    if max_size <= 0 or table.x0.size == 0:
        return mask, table
    small = np.flatnonzero(table.component_size <= max_size)
    for index in small.tolist():
        y = int(table.y[index])
        mask[y, int(table.x0[index]):int(table.x1[index])] = True
    return mask, table


def _component_replacement(
    ids: np.ndarray,
    arr: np.ndarray,
    table: _RunTable,
    *,
    max_size: int,
) -> np.ndarray:
    out = arr.copy()
    h, w = ids.shape
    if table.x0.size == 0 or max_size <= 0:
        return out

    candidates = np.flatnonzero(table.component_size <= max_size)
    if candidates.size == 0:
        return out
    roots = table.root[candidates]
    order = np.argsort(roots, kind="stable")
    candidates = candidates[order]
    roots = roots[order]

    begin = 0
    while begin < len(candidates):
        end = begin + 1
        root = int(roots[begin])
        while end < len(candidates) and int(roots[end]) == root:
            end += 1
        indexes = candidates[begin:end]
        source_color = int(table.color[int(indexes[0])])
        boundary: Counter[int] = Counter()
        for raw_index in indexes.tolist():
            index = int(raw_index)
            y = int(table.y[index])
            x0, x1 = int(table.x0[index]), int(table.x1[index])
            if x0 > 0:
                value = int(ids[y, x0 - 1])
                if value != source_color:
                    boundary[value] += 1
            if x1 < w:
                value = int(ids[y, x1])
                if value != source_color:
                    boundary[value] += 1
            if y > 0:
                values, counts = np.unique(ids[y - 1, x0:x1], return_counts=True)
                for value, count in zip(values.tolist(), counts.tolist()):
                    if int(value) != source_color:
                        boundary[int(value)] += int(count)
            if y + 1 < h:
                values, counts = np.unique(ids[y + 1, x0:x1], return_counts=True)
                for value, count in zip(values.tolist(), counts.tolist()):
                    if int(value) != source_color:
                        boundary[int(value)] += int(count)
        if boundary:
            target = min(boundary.items(), key=lambda item: (-item[1], item[0]))[0]
            rgb = _decode_color(target)
            for raw_index in indexes.tolist():
                index = int(raw_index)
                y = int(table.y[index])
                out[y, int(table.x0[index]):int(table.x1[index])] = rgb
        begin = end
    return out

def _cluster_map(ids: np.ndarray, connectivity: int) -> np.ndarray:
    table = _build_runs(ids, connectivity)
    out = np.zeros((*ids.shape, 3), dtype=np.uint8)
    if table.x0.size == 0:
        return out
    # Compute one deterministic diagnostic color per run/component without a
    # Python dictionary containing every connected component.
    values = (table.root.astype(np.uint64) * np.uint64(0x45D9F3B) + table.color.astype(np.uint64) * np.uint64(0x119DE1F3)) & np.uint64(0xFFFFFFFF)
    values ^= values >> np.uint64(16)
    rr = (48 + ((values >> np.uint64(16)) & np.uint64(0xCF))).astype(np.uint8)
    gg = (48 + ((values >> np.uint64(8)) & np.uint64(0xCF))).astype(np.uint8)
    bb = (48 + (values & np.uint64(0xCF))).astype(np.uint8)
    for index in range(len(table.x0)):
        y = int(table.y[index])
        out[y, int(table.x0[index]):int(table.x1[index])] = (rr[index], gg[index], bb[index])
    return out

def _issue_overlay(arr: np.ndarray, *, max_island: int, connectivity: int) -> np.ndarray:
    ids = _encode_rgb(arr)
    same = _same_neighbour_count(ids)
    stair, _ = _staircase_candidates(ids)
    line, _ = _line_gap_candidates(ids)
    tiny, _ = _small_component_mask(ids, max_size=max_island, connectivity=connectivity)

    orphan = same <= 1
    cluster = same <= 2
    base = np.clip(arr.astype(np.float32) * 0.36, 0, 255).astype(np.uint8)
    # Later assignments have higher visual priority.
    base[cluster] = np.asarray([190, 45, 220], dtype=np.uint8)   # magenta: weak cluster
    base[line] = np.asarray([50, 210, 255], dtype=np.uint8)     # cyan: line break/spike
    base[stair] = np.asarray([255, 210, 45], dtype=np.uint8)    # yellow: staircase candidate
    base[tiny] = np.asarray([255, 120, 35], dtype=np.uint8)     # orange: tiny component
    base[orphan] = np.asarray([255, 45, 45], dtype=np.uint8)    # red: orphan pixel
    return base


def cleanup_pixel_art(
    image: Image.Image,
    *,
    orphan_removal: float = 75.0,
    cluster_cleanup: float = 35.0,
    line_cleanup: float = 50.0,
    staircase_correction: float = 45.0,
    tiny_island_size: int = 4,
    edge_preservation: float = 80.0,
    passes: int = 2,
    connectivity: str | int = "8-neighbour",
    analysis_view: str = "Clean Result",
) -> Image.Image:
    """Clean common machine-dither/pixel-art artifacts without inventing colors.

    The cleanup works only with colors already present in the image. This keeps
    a dithered indexed/palette-style image palette-safe when this layer follows
    the Dither layer. ``Issue Overlay`` and ``Cluster Map`` are analysis views;
    they intentionally return diagnostic colors.
    """
    source = np.asarray(image.convert("RGB"), dtype=np.uint8)
    if source.size == 0:
        return image.convert("RGB")

    conn = 4 if str(connectivity).startswith("4") else 8
    max_island = max(0, min(64, int(tiny_island_size)))
    view = str(analysis_view or "Clean Result")
    ids = _encode_rgb(source)
    if view == "Cluster Map":
        return Image.fromarray(_cluster_map(ids, conn), "RGB")
    if view == "Issue Overlay":
        return Image.fromarray(_issue_overlay(source, max_island=max_island, connectivity=conn), "RGB")

    work = source.copy()
    edge = _edge_strength(source)
    allowed = _edge_allowed(edge, float(edge_preservation) / 100.0)
    passes = max(1, min(4, int(passes)))

    orphan_amount = max(0.0, min(1.0, float(orphan_removal) / 100.0))
    line_amount = max(0.0, min(1.0, float(line_cleanup) / 100.0))
    stair_amount = max(0.0, min(1.0, float(staircase_correction) / 100.0))
    cluster_amount = max(0.0, min(1.0, float(cluster_cleanup) / 100.0))

    # 1. Orphan pixels: one or fewer matching neighbors.
    if orphan_amount > 0.0:
        ids = _encode_rgb(work)
        same = _same_neighbour_count(ids)
        # An orphan has almost no same-color support, so it is not treated as a
        # structural contour even when Edge Preservation is high.
        mask = (same <= 1) & _coordinate_gate(ids.shape, orphan_amount, 0xA11CE)
        if np.any(mask):
            representative = _representative_neighbour(work)
            work[mask] = representative[mask]

    # 2. Repair one-pixel breaks/protrusions along straight/diagonal lines.
    if line_amount > 0.0:
        ids = _encode_rgb(work)
        mask, replacement_ids = _line_gap_candidates(ids)
        mask &= allowed & _coordinate_gate(ids.shape, line_amount, 0x1A1E)
        if np.any(mask):
            replacement = np.stack((
                (replacement_ids >> 16) & 255,
                (replacement_ids >> 8) & 255,
                replacement_ids & 255,
            ), axis=2).astype(np.uint8)
            work[mask] = replacement[mask]

    # 3. Remove classic 3-vs-1 2×2 staircase burrs.
    if stair_amount > 0.0:
        ids = _encode_rgb(work)
        mask, replacement_ids = _staircase_candidates(ids)
        mask &= allowed & _coordinate_gate(ids.shape, stair_amount, 0x57A1)
        if np.any(mask):
            replacement = np.stack((
                (replacement_ids >> 16) & 255,
                (replacement_ids >> 8) & 255,
                replacement_ids & 255,
            ), axis=2).astype(np.uint8)
            work[mask] = replacement[mask]

    # 4. Exact small connected-component removal. The run-length component
    # representation avoids a Python object per pixel and is fast on the flat
    # color runs typical of pixel art.
    if max_island > 0:
        ids = _encode_rgb(work)
        _, run_table = _small_component_mask(ids, max_size=max_island, connectivity=conn)
        work = _component_replacement(ids, work, run_table, max_size=max_island)

    # 5. Conservative iterative cluster smoothing. Only poorly-supported
    # pixels are candidates, and the replacement is always an existing neighbor.
    if cluster_amount > 0.0:
        for pass_index in range(passes):
            ids = _encode_rgb(work)
            same = _same_neighbour_count(ids)
            # Higher cleanup strength gradually admits pixels with one extra
            # same-color neighbor, but never broad flat regions.
            support_limit = 2 + (1 if cluster_amount >= 0.72 else 0)
            gate_amount = cluster_amount * (0.86 ** pass_index)
            mask = (same <= support_limit) & allowed & _coordinate_gate(ids.shape, gate_amount, 0xC1EA + pass_index * 313)
            if not np.any(mask):
                break
            representative = _representative_neighbour(work)
            changed = mask & np.any(representative != work, axis=2)
            if not np.any(changed):
                break
            work[changed] = representative[changed]

    return Image.fromarray(work, "RGB")


__all__ = ["cleanup_pixel_art"]
