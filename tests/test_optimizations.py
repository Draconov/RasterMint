from __future__ import annotations

import numpy as np
from PIL import Image

from rastermint.core import effect_stack as effect_stack_module
from rastermint.core import processor as processor_module
from rastermint.core.hardware import _tile_color_limit
from rastermint.core.palette import _kmeans_palette, _nearest_center_labels
from rastermint.core.settings import ProcessingSettings


def test_process_image_normalizes_effect_stack_only_once(monkeypatch):
    source = Image.new("RGB", (8, 8), (100, 140, 180))
    settings = ProcessingSettings(palette=["#000000", "#FFFFFF"])

    original = processor_module.normalize_effect_stack
    calls = 0

    def counted(stack, owner=None):
        nonlocal calls
        calls += 1
        return original(stack, owner)

    monkeypatch.setattr(processor_module, "normalize_effect_stack", counted)

    def unexpected_second_normalization(*_args, **_kwargs):
        raise AssertionError("normalized processor stack was normalized a second time")

    monkeypatch.setattr(effect_stack_module, "normalize_effect_stack", unexpected_second_normalization)
    processor_module.process_image(source, settings)
    assert calls == 1


def test_settings_clone_is_independent_without_serialization_round_trip():
    settings = ProcessingSettings(
        palette=["#112233", "#AABBCC"],
        palette_locks=[True, False],
        display_profile={"scanlines": 0.2},
        effect_stack=[{"id": "x", "kind": "Invert", "enabled": True, "params": {}}],
        animation_tracks=[{"target": "effect:x:amount", "keyframes": [{"time": 0.0, "value": 1.0}]}],
    )
    clone = settings.clone()
    assert clone.to_dict() == settings.to_dict()

    clone.palette[0] = "#000000"
    clone.display_profile["scanlines"] = 0.8
    clone.effect_stack[0]["enabled"] = False
    clone.animation_tracks[0]["keyframes"][0]["value"] = 2.0

    assert settings.palette[0] == "#112233"
    assert settings.display_profile["scanlines"] == 0.2
    assert settings.effect_stack[0]["enabled"] is True
    assert settings.animation_tracks[0]["keyframes"][0]["value"] == 1.0


def _legacy_tile_limit_reference(
    arr: np.ndarray,
    tile_width: int,
    tile_height: int,
    max_colors: int,
    palette_groups: list[list[str]] | None = None,
) -> np.ndarray:
    from rastermint.core.palette import palette_array

    def remap(region: np.ndarray, palette: np.ndarray) -> np.ndarray:
        flat = region.reshape(-1, 3).astype(np.float32)
        diff = flat[:, None, :] - palette[None, :, :]
        idx = np.argmin(np.sum(diff * diff, axis=2), axis=1)
        return palette[idx].reshape(region.shape).astype(np.uint8)

    def choose(region: np.ndarray, limit: int) -> np.ndarray:
        pixels = region.reshape(-1, 3)
        colors, counts = np.unique(pixels, axis=0, return_counts=True)
        if len(colors) <= limit:
            return colors.astype(np.float32)
        order = np.argsort(counts)[::-1][:limit]
        return colors[order].astype(np.float32)

    h, w, _ = arr.shape
    tw = max(1, int(tile_width))
    th = max(1, int(tile_height))
    limit = max(1, int(max_colors))
    out = arr.copy()
    groups = [palette_array(group) for group in (palette_groups or []) if group]
    for y in range(0, h, th):
        for x in range(0, w, tw):
            region = out[y:min(h, y + th), x:min(w, x + tw)]
            if groups:
                best_group = None
                best_error = float("inf")
                for group in groups:
                    mapped = remap(region, group)
                    error = float(np.mean((region.astype(np.float32) - mapped.astype(np.float32)) ** 2))
                    if error < best_error:
                        best_error = error
                        best_group = group
                assert best_group is not None
                mapped = remap(region, best_group)
                chosen = choose(mapped, limit)
                region[:] = remap(region, chosen)
            else:
                chosen = choose(region, limit)
                region[:] = remap(region, chosen)
    return out


def test_optimized_tile_limits_match_previous_output_exactly():
    rng = np.random.default_rng(0x524D)
    source = rng.integers(0, 256, (29, 37, 3), dtype=np.uint8)
    cases = [
        (8, 8, 4, None),
        (7, 5, 3, None),
        (8, 8, 2, [
            ["#000000", "#FFFFFF"],
            ["#000000", "#FF0000", "#FFFF00"],
            ["#000000", "#0000FF", "#00FFFF"],
        ]),
    ]
    for args in cases:
        expected = _legacy_tile_limit_reference(source, *args)
        actual = _tile_color_limit(source, *args)
        assert np.array_equal(actual, expected), args



def test_chunked_kmeans_assignment_matches_legacy_distance_formula():
    rng = np.random.default_rng(0x203)
    pixels = rng.uniform(0.0, 255.0, (2500, 3)).astype(np.float32)
    centers = rng.uniform(0.0, 255.0, (96, 3)).astype(np.float32)
    expected = np.argmin(
        np.sum((pixels[:, None, :] - centers[None, :, :]) ** 2, axis=2),
        axis=1,
    )
    actual = _nearest_center_labels(pixels, centers, chunk_pixels=257)
    assert np.array_equal(actual, expected)

def test_chunked_kmeans_is_deterministic():
    rng = np.random.default_rng(123)
    image = Image.fromarray(rng.integers(0, 256, (80, 96, 3), dtype=np.uint8), "RGB")
    assert _kmeans_palette(image, 16) == _kmeans_palette(image, 16)


def test_removed_hidden_hardware_constraint_fields_are_ignored():
    settings = ProcessingSettings.from_dict({
        "hardware_profile_id": "custom",
        "hardware_constraints_enabled": True,
        "hardware_constraints": {"channel_bits": [2, 2, 2]},
    })
    assert not hasattr(settings, "hardware_constraints_enabled")
    assert not hasattr(settings, "hardware_constraints")
