from __future__ import annotations

import numpy as np
from PIL import Image

from rastermint.core.pixel_cleanup import cleanup_pixel_art


def _image(array: np.ndarray) -> Image.Image:
    return Image.fromarray(np.asarray(array, dtype=np.uint8), "RGB")


def test_cleanup_removes_isolated_orphan_without_crossing_palette():
    arr = np.zeros((9, 9, 3), dtype=np.uint8)
    arr[:] = (18, 38, 72)
    arr[4, 4] = (245, 50, 45)
    out = np.asarray(cleanup_pixel_art(
        _image(arr), orphan_removal=100, cluster_cleanup=0, line_cleanup=0,
        staircase_correction=0, tiny_island_size=0,
    ))
    assert tuple(out[4, 4]) == (18, 38, 72)
    assert {tuple(value) for value in out.reshape(-1, 3)} <= {
        (18, 38, 72), (245, 50, 45)
    }


def test_cleanup_removes_tiny_component_but_preserves_larger_cluster():
    arr = np.zeros((14, 14, 3), dtype=np.uint8)
    arr[:] = (0, 0, 0)
    arr[2:4, 2:4] = (255, 255, 255)  # four-pixel island
    arr[7:10, 7:10] = (255, 255, 255)  # nine-pixel cluster
    out = np.asarray(cleanup_pixel_art(
        _image(arr), orphan_removal=0, cluster_cleanup=0, line_cleanup=0,
        staircase_correction=0, tiny_island_size=4,
    ))
    assert not np.any(out[2:4, 2:4])
    assert np.all(out[7:10, 7:10] == 255)


def test_line_cleanup_repairs_one_pixel_gap():
    arr = np.zeros((9, 9, 3), dtype=np.uint8)
    arr[:] = (5, 5, 5)
    arr[4, 2:7] = (240, 240, 240)
    arr[4, 4] = (5, 5, 5)
    out = np.asarray(cleanup_pixel_art(
        _image(arr), orphan_removal=0, cluster_cleanup=0, line_cleanup=100,
        staircase_correction=0, tiny_island_size=0, edge_preservation=0,
    ))
    assert tuple(out[4, 4]) == (240, 240, 240)


def test_staircase_cleanup_repairs_three_against_one_corner():
    arr = np.zeros((6, 6, 3), dtype=np.uint8)
    arr[:] = (20, 20, 20)
    arr[2:4, 2:4] = (230, 230, 230)
    arr[2, 2] = (20, 20, 20)
    out = np.asarray(cleanup_pixel_art(
        _image(arr), orphan_removal=0, cluster_cleanup=0, line_cleanup=0,
        staircase_correction=100, tiny_island_size=0, edge_preservation=0,
    ))
    assert tuple(out[2, 2]) == (230, 230, 230)


def test_cluster_visualization_views_are_deterministic_and_same_size():
    arr = np.zeros((8, 10, 3), dtype=np.uint8)
    arr[:, :5] = (20, 60, 100)
    arr[:, 5:] = (200, 210, 220)
    source = _image(arr)
    first = np.asarray(cleanup_pixel_art(source, analysis_view="Cluster Map"))
    second = np.asarray(cleanup_pixel_art(source, analysis_view="Cluster Map"))
    issues = np.asarray(cleanup_pixel_art(source, analysis_view="Issue Overlay"))
    assert first.shape == arr.shape == issues.shape
    assert np.array_equal(first, second)
    assert len({tuple(v) for v in first.reshape(-1, 3)}) == 2


def test_connectivity_changes_diagonal_component_grouping():
    arr = np.zeros((5, 5, 3), dtype=np.uint8)
    arr[:] = (0, 0, 0)
    arr[1, 1] = (255, 255, 255)
    arr[2, 2] = (255, 255, 255)
    four = np.asarray(cleanup_pixel_art(
        _image(arr), orphan_removal=0, cluster_cleanup=0, line_cleanup=0,
        staircase_correction=0, tiny_island_size=1, connectivity="4-neighbour",
    ))
    eight = np.asarray(cleanup_pixel_art(
        _image(arr), orphan_removal=0, cluster_cleanup=0, line_cleanup=0,
        staircase_correction=0, tiny_island_size=1, connectivity="8-neighbour",
    ))
    assert not np.any(four[1, 1]) and not np.any(four[2, 2])
    assert np.all(eight[1, 1] == 255) and np.all(eight[2, 2] == 255)


def test_cleanup_accepts_rgba_and_tiny_images_without_dimension_changes():
    rgba = np.asarray([[[10, 20, 30, 0], [240, 220, 200, 255]]], dtype=np.uint8)
    image = Image.fromarray(rgba, "RGBA")
    for view in ("Clean Result", "Issue Overlay", "Cluster Map"):
        out = cleanup_pixel_art(image, analysis_view=view, tiny_island_size=1)
        assert out.size == image.size
        assert out.mode == "RGB"
