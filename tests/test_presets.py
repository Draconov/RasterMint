# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import json

from rastermint.core.presets import (
    load_preset,
    load_preset_payload,
    save_preset,
    slugify_preset_name,
)
from rastermint.core.settings import ProcessingSettings


def test_preset_roundtrip(tmp_path):
    original = ProcessingSettings(
        algorithm="Bayer 8x8",
        brightness=12,
        contrast=-8,
        saturation=20,
        gamma=1.25,
        grayscale=True,
        invert=True,
        blur_radius=1.5,
        sharpen=1.6,
        dither_strength=0.75,
        pixel_size=3,
        serpentine=False,
        output_divisor=3,
        palette=["#112233", "#445566", "#FFFFFF"],
        hardware_profile_id="game-boy",
        hardware_mode="strict",
    )
    path = tmp_path / "test.json"
    save_preset(path, original)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["hardware_reference"] == {"profile_id": "game-boy", "mode": "strict"}
    loaded = load_preset(path)
    assert loaded.to_dict() == original.to_dict()


def test_library_metadata_api_is_backward_compatible(tmp_path):
    settings = ProcessingSettings(hardware_profile_id="game-boy", hardware_mode="visual")
    path = tmp_path / "portrait.json"
    save_preset(
        path,
        settings,
        preset_id="user-portrait",
        name="Portrait",
        description="A user preset",
    )
    payload = load_preset_payload(path)
    assert payload["id"] == "user-portrait"
    assert payload["name"] == "Portrait"
    assert payload["description"] == "A user preset"
    assert payload["hardware_reference"]["profile_id"] == "game-boy"



def test_preset_files_do_not_store_source_crop(tmp_path):
    settings = ProcessingSettings(
        crop_x=0.20, crop_y=0.15, crop_width=0.55, crop_height=0.60,
        brightness=14,
    )
    path = tmp_path / "no-crop.json"
    save_preset(path, settings)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "crop_x" not in payload["settings"]
    assert "crop_y" not in payload["settings"]
    assert "crop_width" not in payload["settings"]
    assert "crop_height" not in payload["settings"]
    assert payload["settings"]["brightness"] == 14

    loaded = load_preset(path)
    assert (loaded.crop_x, loaded.crop_y, loaded.crop_width, loaded.crop_height) == (0.0, 0.0, 1.0, 1.0)


def test_preset_application_merges_current_crop_without_other_source_state():
    import rastermint.core.presets as preset_module

    merge = getattr(preset_module, "merge_preset_with_current_crop", None)
    assert callable(merge)

    current = ProcessingSettings(
        crop_x=0.25, crop_y=0.10, crop_width=0.50, crop_height=0.65,
        brightness=-20,
    )
    preset = ProcessingSettings(brightness=35, contrast=12)
    merged = merge(preset, current)

    assert merged.brightness == 35
    assert merged.contrast == 12
    assert (merged.crop_x, merged.crop_y, merged.crop_width, merged.crop_height) == (0.25, 0.10, 0.50, 0.65)

def test_slugify_preset_name():
    assert slugify_preset_name("  My Fancy Preset!  ") == "my-fancy-preset"
    assert slugify_preset_name("") == "preset"


# ---- merged from test_preset_mutation_070.py ----

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
