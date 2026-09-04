# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import numpy as np

from rastermint.core.dither import ALGORITHMS, ERROR_DIFFUSION_KERNELS, apply_dither, error_diffusion
from rastermint.core.palette import nearest_palette_index, palette_array


def make_gradient() -> np.ndarray:
    x = np.linspace(0, 255, 12, dtype=np.float32)
    row = np.stack([x, np.roll(x, 3), np.roll(x, 6)], axis=1)
    return np.tile(row[None, :, :], (10, 1, 1))


def test_all_algorithms_only_emit_palette_colors():
    image = make_gradient()
    palette = palette_array(["#000000", "#FF0000", "#FFFFFF"])
    palette_set = {tuple(map(int, c)) for c in palette}

    for algorithm in ALGORITHMS:
        out = apply_dither(image, palette, algorithm, strength=1.0, serpentine=True)
        assert out.shape == image.shape
        emitted = {tuple(map(int, c)) for c in out.reshape(-1, 3)}
        assert emitted <= palette_set, algorithm


def test_dither_is_deterministic_including_random_mode():
    image = make_gradient()
    palette = palette_array(["#000000", "#FFFFFF"])
    for algorithm in ALGORITHMS:
        a = apply_dither(image, palette, algorithm)
        b = apply_dither(image, palette, algorithm)
        assert np.array_equal(a, b), algorithm


def _reference_error_diffusion(image, palette, kernel, divisor, strength=1.0, serpentine=True):
    work = image.astype(np.float32, copy=True)
    h, w, _ = work.shape
    for y in range(h):
        reverse = serpentine and (y % 2 == 1)
        xs = range(w - 1, -1, -1) if reverse else range(w)
        direction = -1 if reverse else 1
        for x in xs:
            old = np.clip(work[y, x], 0, 255)
            idx = nearest_palette_index(old, palette)
            new = palette[idx]
            work[y, x] = new
            error = (old - new) * strength
            for dx, dy, weight in kernel:
                nx = x + dx * direction
                ny = y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    work[ny, nx] += error * (weight / divisor)
    return np.clip(work, 0, 255)


def test_optimized_error_diffusion_matches_reference():
    image = np.random.default_rng(44).uniform(0, 255, (8, 11, 3)).astype(np.float32)
    palette = palette_array(["#101217", "#4A4F59", "#A9AFB9", "#F4F6F8"])
    for name, (kernel, divisor) in ERROR_DIFFUSION_KERNELS.items():
        for serpentine in (False, True):
            expected = _reference_error_diffusion(image, palette, kernel, divisor, 0.85, serpentine)
            actual = error_diffusion(image, palette, kernel, divisor, 0.85, serpentine)
            assert np.array_equal(actual, expected), (name, serpentine)


# ---- merged from test_modulated_diffusion.py ----

import json
from pathlib import Path

import numpy as np
from PIL import Image

from rastermint.core.builtin_presets import BUILTIN_PRESETS, build_builtin_preset
from rastermint.core.dither import apply_dither
from rastermint.core.dither_metadata import ALGORITHMS, MODULATION_MODES
from rastermint.core.effect_schema import EFFECT_DEFINITIONS, normalize_effect_stack
from rastermint.core.processor import process_image


EXPECTED_MODES = (
    "Smooth Diffuse",
    "Modulated Diffuse X",
    "Modulated Diffuse Y",
    "Uniform Modulation X",
    "Uniform Modulation Y",
    "Waveform",
    "Waveform Alt",
    "Ordered Modulation",
    "Stucki Diffusion Lines",
    "Atkinson Modulation",
    "Contrast Aware X",
    "Contrast Aware Y",
    "Displace Contour",
    "Sine Wave Modulation",
)


def _fixture() -> tuple[np.ndarray, np.ndarray]:
    h, w = 17, 23
    yy, xx = np.mgrid[0:h, 0:w]
    image = np.stack(
        [
            xx / max(1, w - 1) * 255.0,
            yy / max(1, h - 1) * 255.0,
            (0.5 + 0.5 * np.sin(xx * 0.55 + yy * 0.22)) * 255.0,
        ],
        axis=-1,
    ).astype(np.float32)
    palette = np.array(
        [[0, 0, 0], [18, 50, 65], [52, 122, 136], [115, 210, 216], [255, 255, 255]],
        dtype=np.float32,
    )
    return image, palette


def test_modulation_remains_one_algorithm_with_fourteen_modes():
    assert tuple(MODULATION_MODES) == EXPECTED_MODES
    assert ALGORITHMS.count("Modulation") == 1
    assert not any(mode in ALGORITHMS for mode in EXPECTED_MODES)

    spec = EFFECT_DEFINITIONS["Dither"]["params"]["modulation_mode"]
    assert spec["type"] == "choice"
    assert tuple(spec["options"]) == EXPECTED_MODES


def test_every_modulation_mode_is_deterministic_palette_bounded_and_distinct():
    image, palette = _fixture()
    fingerprints: set[bytes] = set()
    palette_rows = {tuple(row) for row in palette.tolist()}

    for mode in MODULATION_MODES:
        first = apply_dither(
            image,
            palette,
            "Modulation",
            strength=0.95,
            serpentine=True,
            modulation_mode=mode,
            modulation_scale=8.5,
            modulation_phase=23.0,
            modulation_bias=-0.04,
            modulation_detail=0.72,
            modulation_seed=71,
        )
        second = apply_dither(
            image,
            palette,
            "Modulation",
            strength=0.95,
            serpentine=True,
            modulation_mode=mode,
            modulation_scale=8.5,
            modulation_phase=23.0,
            modulation_bias=-0.04,
            modulation_detail=0.72,
            modulation_seed=71,
        )
        assert first.shape == image.shape
        assert np.array_equal(first, second), mode
        assert {tuple(row) for row in np.unique(first.reshape(-1, 3), axis=0).tolist()} <= palette_rows
        fingerprints.add(first.tobytes())

    assert len(fingerprints) == len(EXPECTED_MODES)


def test_modulation_phase_is_animation_ready():
    image, palette = _fixture()
    zero = apply_dither(image, palette, "Modulation", modulation_mode="Sine Wave Modulation", modulation_phase=0.0)
    shifted = apply_dither(image, palette, "Modulation", modulation_mode="Sine Wave Modulation", modulation_phase=90.0)
    assert not np.array_equal(zero, shifted)



def test_legacy_modulation_layers_keep_the_old_sine_family_behavior():
    legacy = [{
        "id": "legacy-dither",
        "kind": "Dither",
        "enabled": True,
        "params": {"algorithm": "Modulation", "strength": 1.0, "serpentine": True},
    }]
    normalized = normalize_effect_stack(legacy)
    assert normalized[0]["params"]["modulation_mode"] == "Sine Wave Modulation"

def test_modulation_presets_and_star_field_are_real_editable_stacks():
    ids = {item.id for item in BUILTIN_PRESETS}
    modulation_presets = {
        "mod-smooth-bloom",
        "mod-circuit-cyan",
        "mod-stucki-wire",
        "mod-contour-bend",
        "mod-waveform-bloom",
    }
    assert modulation_presets <= ids
    assert "particle-star-field" in ids

    for preset_id in modulation_presets:
        settings = build_builtin_preset(preset_id)
        dither = next(step for step in settings.effect_stack if step["kind"] == "Dither")
        assert dither["params"]["algorithm"] == "Modulation"
        assert dither["params"]["modulation_mode"] in MODULATION_MODES
        assert any(step["kind"] in {"Dither Glow", "Bloom", "Horizontal Bloom", "Phosphor Glow"} for step in settings.effect_stack)

    star = build_builtin_preset("particle-star-field")
    kinds = [str(step["kind"]) for step in star.effect_stack]
    assert "Particle" not in EFFECT_DEFINITIONS
    assert "Star Field" not in EFFECT_DEFINITIONS
    assert "Noise" in kinds
    assert "Temporal Pattern" in kinds
    assert "Dither Glow" in kinds
    assert "Bloom" in kinds
    noise = next(step for step in star.effect_stack if step["kind"] == "Noise")
    assert noise["params"]["temporal"] is True


def test_particle_star_field_changes_across_animation_frames():
    image = Image.new("RGB", (28, 20), (56, 72, 88))
    settings = build_builtin_preset("particle-star-field")
    first = process_image(image, settings, frame_time=0.0, frame_index=0, tiled_processing=False)
    second = process_image(image, settings, frame_time=0.4, frame_index=5, tiled_processing=False)
    assert first.size == image.size
    assert second.size == image.size
    assert first.tobytes() != second.tobytes()


def test_modulation_ui_and_translations_are_wired():
    root = Path(__file__).resolve().parents[1]
    qml = (root / "src/rastermint/qml/pages/LayersPage.qml").read_text(encoding="utf-8")
    assert 'var modulation = algorithm === "Modulation"' in qml
    assert 'String(param.key).indexOf("modulation_") === 0' in qml

    required = {"Modulation mode", "Modulation scale", "Modulation phase", "Modulation bias", "Contour detail", *EXPECTED_MODES}
    for path in (root / "src/rastermint/data/translations").glob("*.json"):
        messages = json.loads(path.read_text(encoding="utf-8"))["messages"]
        assert required <= set(messages), path.name


def test_dither_edge_treatment_schema_defaults_preserve_legacy_behavior():
    params = EFFECT_DEFINITIONS["Dither"]["params"]
    assert params["bleed"]["default"] == 0.0
    assert params["bleed"]["min"] == -10.0
    assert params["bleed"]["max"] == 10.0
    assert params["rounding"]["default"] == 0.0
    assert params["rounding"]["min"] == 0.0
    assert params["rounding"]["max"] == 100.0
    assert params["sampling"]["default"] == "Native"
    assert params["sampling"]["options"] == ["Native", "2× Supersampled"]


def test_dither_edge_treatment_bleed_and_rounding_stay_palette_bounded():
    from rastermint.core.effect_stack import _apply_dither_edge_treatment

    palette = np.array([[0, 0, 0], [255, 255, 255]], dtype=np.float32)
    result = np.full((7, 7, 3), 255.0, dtype=np.float32)
    result[3, 3] = 0.0

    bled = _apply_dither_edge_treatment(result, palette, bleed=1.0, rounding=0.0)
    assert np.all(bled[2:5, 2:5] == 0)

    dark_block = np.full((7, 7, 3), 255.0, dtype=np.float32)
    dark_block[2:5, 2:5] = 0.0
    contracted = _apply_dither_edge_treatment(dark_block, palette, bleed=-1.0, rounding=0.0)
    assert np.all(contracted[3, 3] == 0)
    contracted_copy = contracted.copy()
    contracted_copy[3, 3] = 255
    assert np.all(contracted_copy == 255)

    rounded = _apply_dither_edge_treatment(result, palette, bleed=0.0, rounding=40.0)
    assert np.all(rounded == 255)

    palette_rows = {tuple(map(int, row)) for row in palette}
    for candidate in (bled, contracted, rounded):
        emitted = {tuple(map(int, row)) for row in candidate.reshape(-1, 3)}
        assert emitted <= palette_rows


def test_dither_supersampling_keeps_size_and_palette_and_native_matches_direct_dither():
    from rastermint.core.effect_stack import apply_effect_stack, new_effect

    source_arr = np.rint(make_gradient()).astype(np.uint8)
    source = Image.fromarray(source_arr, "RGB")
    colors = ["#000000", "#FF0000", "#FFFFFF"]
    palette = palette_array(colors)

    effect = new_effect("Dither")
    effect["params"].update(algorithm="Bayer 4x4", strength=0.9, sampling="Native", bleed=0.0, rounding=0.0)
    native = np.asarray(apply_effect_stack(source, [effect], colors))
    direct = np.clip(apply_dither(source_arr.astype(np.float32), palette, "Bayer 4x4", strength=0.9), 0, 255).astype(np.uint8)
    assert np.array_equal(native, direct)

    effect["params"]["sampling"] = "2× Supersampled"
    supersampled = np.asarray(apply_effect_stack(source, [effect], colors))
    assert supersampled.shape == source_arr.shape
    palette_rows = {tuple(map(int, row)) for row in palette}
    emitted = {tuple(map(int, row)) for row in supersampled.reshape(-1, 3)}
    assert emitted <= palette_rows
