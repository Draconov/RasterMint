from __future__ import annotations

from copy import deepcopy

from rastermint.core.preset_mutation import generate_preset_mutations


def _settings() -> dict:
    return {
        "palette": ["#101820", "#F2AA4C", "#F7F7F7"],
        "palette_locks": [True, False, False],
        "palette_name": "Test Palette",
        "target_width": 320,
        "target_height": 240,
        "animation_tracks": [{"target": "layer-1.brightness", "enabled": True}],
        "effect_stack": [
            {
                "id": "layer-1",
                "kind": "Adjustments",
                "enabled": True,
                "opacity": 1.0,
                "blend_mode": "Normal",
                "mask": {"type": "None", "invert": False, "feather": 0.0, "strength": 1.0},
                "params": {"brightness": 12, "contrast": 18, "saturation": 4, "gamma": 1.1},
            },
            {
                "id": "layer-2",
                "kind": "Bloom",
                "enabled": True,
                "opacity": 0.8,
                "blend_mode": "Screen",
                "mask": {"type": "Highlights", "invert": False, "feather": 0.2, "strength": 0.7},
                "params": {"threshold": 0.65, "soft_knee": 0.2, "radius": 8.0, "intensity": 0.8, "blend": "Screen"},
            },
        ],
    }


def test_mutation_count_is_clamped_to_six_through_twelve():
    source = _settings()
    assert len(generate_preset_mutations(source, count=1, seed=7)) == 6
    assert len(generate_preset_mutations(source, count=99, seed=7)) == 12


def test_mutations_are_deterministic_for_a_seed_and_do_not_modify_source():
    source = _settings()
    original = deepcopy(source)
    first = generate_preset_mutations(source, count=8, amount=0.35, seed=1234)
    second = generate_preset_mutations(source, count=8, amount=0.35, seed=1234)
    assert first == second
    assert source == original


def test_mutations_preserve_editable_stack_structure_and_locked_palette_colors():
    source = _settings()
    variants = generate_preset_mutations(source, count=8, amount=0.45, seed=31415)
    source_structure = [
        (step["id"], step["kind"], step["enabled"], step["blend_mode"], step["mask"])
        for step in source["effect_stack"]
    ]
    for item in variants:
        data = item["settings"]
        structure = [
            (step["id"], step["kind"], step["enabled"], step["blend_mode"], step["mask"])
            for step in data["effect_stack"]
        ]
        assert structure == source_structure
        assert data["palette"][0] == source["palette"][0]
        assert data["target_width"] == 320 and data["target_height"] == 240
        assert data["animation_tracks"] == source["animation_tracks"]
        assert data != source


def test_sparse_locked_preset_still_generates_real_variations():
    source = {
        "palette": ["#000000", "#FFFFFF"],
        "palette_locks": [True, True],
        "effect_stack": [{
            "id": "layer-empty",
            "kind": "Grayscale",
            "enabled": True,
            "opacity": 1.0,
            "blend_mode": "Normal",
            "mask": {"type": "None", "invert": False, "feather": 0.0, "strength": 1.0},
            "params": {},
        }],
    }
    variants = generate_preset_mutations(source, count=6, amount=0.35, seed=9)
    assert len(variants) == 6
    assert all(item["settings"] != source for item in variants)
    assert all(item["settings"]["effect_stack"][0]["id"] == "layer-empty" for item in variants)
    assert all(item["settings"]["effect_stack"][0]["mask"] == source["effect_stack"][0]["mask"] for item in variants)
