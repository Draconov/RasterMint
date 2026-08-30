from __future__ import annotations

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
