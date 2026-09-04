from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from rastermint.core.builtin_presets import build_builtin_preset
from rastermint.core.dither import beehive_dither, polygon_dither, pop_tone_dither
from rastermint.core.effect_schema import new_effect, normalize_effect_stack
from rastermint.core.print_lab import build_separations, export_print_separations, render_print_lab, screen_separation
from rastermint.core.settings import ProcessingSettings


def _image(w=48, h=35):
    yy, xx = np.mgrid[0:h, 0:w]
    arr = np.stack([
        (xx / max(1, w - 1) * 255),
        (yy / max(1, h - 1) * 255),
        (((xx + yy) % 17) / 16 * 255),
    ], axis=-1).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def _palette():
    return np.asarray([[0, 0, 0], [255, 255, 255], [230, 40, 55], [30, 90, 200], [245, 205, 50]], dtype=np.float32)


def test_print_lab_modes_and_spot_counts():
    image = _image()
    expected = {"Monochrome": 1, "CMYK": 4, "RGB": 3, "Spot Colors": 6}
    for mode, count in expected.items():
        seps, params = build_separations(image, {"mode": mode, "ink_count": 6})
        assert len(seps) == count
        assert all(sep.coverage.shape == (image.height, image.width) for sep in seps)
        rendered = render_print_lab(image, {"mode": mode, "ink_count": 6, "cell_size": 7})
        assert rendered.size == image.size
        assert rendered.mode == "RGB"


def test_cmyk_black_mix_changes_undercolour_removal():
    image = Image.new("RGB", (16, 16), (45, 55, 65))
    low, _ = build_separations(image, {"mode": "CMYK", "black_mix": 0})
    high, _ = build_separations(image, {"mode": "CMYK", "black_mix": 100})
    assert float(high[3].coverage.mean()) > float(low[3].coverage.mean())
    assert float(high[0].coverage.mean()) < float(low[0].coverage.mean())


def test_angles_phase_registration_and_shapes_change_screen():
    image = _image(61, 47)
    for shape in ["Round", "Ellipse", "Square", "Diamond", "Line"]:
        seps, params = build_separations(image, {"mode": "CMYK", "cell_size": 9, "dot_shape": shape})
        screen = screen_separation(seps[0], params)
        assert screen.shape == (47, 61)
        assert 0.0 <= float(screen.mean()) <= 1.0
    a = np.asarray(render_print_lab(image, {"mode": "CMYK", "cell_size": 9, "ink1_angle": 15}), dtype=np.uint8)
    b = np.asarray(render_print_lab(image, {"mode": "CMYK", "cell_size": 9, "ink1_angle": 38, "phase_offsets": True, "ink1_phase_x": .3, "ink1_offset_x": 2}), dtype=np.uint8)
    assert not np.array_equal(a, b)


def test_imperfections_are_optional_and_deterministic():
    image = _image(52, 41)
    clean = np.asarray(render_print_lab(image, {"mode": "CMYK", "seed": 9}), dtype=np.uint8)
    p = {"mode": "CMYK", "seed": 9, "registration_error": 2, "roughness": .3, "missing_ink": .2, "ink_spread": .2, "paper_grain": .2, "squeegee": .3}
    dirty1 = np.asarray(render_print_lab(image, p), dtype=np.uint8)
    dirty2 = np.asarray(render_print_lab(image, p), dtype=np.uint8)
    assert np.array_equal(dirty1, dirty2)
    assert not np.array_equal(clean, dirty1)


def test_separation_export_is_real_vector_svg(tmp_path: Path):
    image = _image(32, 24)
    paths = export_print_separations(image, {"mode": "CMYK", "cell_size": 8, "dot_shape": "Diamond"}, tmp_path, stem="sample")
    names = {p.name for p in paths}
    assert {"sample_cyan.svg", "sample_magenta.svg", "sample_yellow.svg", "sample_black.svg", "sample_composite.png"} <= names
    text = (tmp_path / "sample_cyan.svg").read_text(encoding="utf-8")
    assert "<svg" in text
    assert "<image" not in text
    assert any(tag in text for tag in ("<circle", "<ellipse", "<rect", "<polygon"))


def test_new_dither_families_are_palette_bounded_and_structural():
    image = np.asarray(_image(45, 37), dtype=np.float32)
    palette = _palette()
    palette_set = {tuple(int(v) for v in row) for row in palette}
    outputs = [
        pop_tone_dither(image, palette, 7, .8, .4),
        beehive_dither(image, palette, 9, .5, 8),
    ]
    for variant in ["Hexa-Poly", "Penta-Poly", "Tri-Poly", "Low-Poly"]:
        outputs.append(polygon_dither(image, palette, variant, 9))
    for out in outputs:
        assert out.shape == image.shape
        colors = {tuple(int(round(v)) for v in row) for row in np.unique(out.reshape(-1, 3), axis=0)}
        assert colors <= palette_set


def test_print_presets_are_editable_real_layers():
    ids = [
        "print-clean-cmyk", "print-vintage-screen", "print-2color-poster", "print-3color-riso",
        "print-newspaper-cmyk", "print-misregistered", "print-cheap-tshirt", "print-heavy-dot-gain",
    ]
    for preset_id in ids:
        settings = build_builtin_preset(preset_id)
        stack = normalize_effect_stack(settings.effect_stack, settings)
        layers = [step for step in stack if step.get("kind") == "Print Lab"]
        assert len(layers) == 1
        assert isinstance(layers[0].get("params"), dict)


def test_old_settings_without_print_lab_round_trip():
    old = ProcessingSettings.from_dict({"algorithm": "Bayer 4x4", "palette": ["#000000", "#FFFFFF"]})
    restored = ProcessingSettings.from_dict(old.to_dict())
    assert restored.algorithm == "Bayer 4x4"
    assert all(step.get("kind") != "Print Lab" for step in restored.effect_stack)
    layer = new_effect("Print Lab")
    old.effect_stack = [layer]
    restored2 = ProcessingSettings.from_dict(old.to_dict())
    assert restored2.effect_stack[0]["kind"] == "Print Lab"


def test_spot_colour_ink_limits_and_export(tmp_path: Path):
    image = _image(29, 23)
    for count in (1, 2, 4, 8):
        seps, _ = build_separations(image, {"mode": "Spot Colors", "ink_count": count, "cell_size": 5})
        assert len(seps) == count
    paths = export_print_separations(
        image,
        {"mode": "Spot Colors", "ink_count": 8, "cell_size": 6},
        tmp_path,
        stem="spots",
    )
    names = {p.name for p in paths}
    for index in range(1, 9):
        assert f"spots_spot_{index}.svg" in names
        assert f"spots_spot_{index}.png" in names
    assert "spots_composite.png" in names


def test_transparent_pixels_do_not_generate_print_ink():
    rgba = np.zeros((17, 19, 4), dtype=np.uint8)
    rgba[..., :3] = (0, 0, 0)
    rgba[..., 3] = 0
    rgba[5:12, 6:13, :3] = (30, 50, 70)
    rgba[5:12, 6:13, 3] = 255
    image = Image.fromarray(rgba, "RGBA")
    seps, _ = build_separations(image, {"mode": "CMYK"})
    for sep in seps:
        assert np.allclose(sep.coverage[:4], 0.0)
        assert np.allclose(sep.coverage[:, :5], 0.0)


def test_print_cell_size_extremes_and_vector_imperfections(tmp_path: Path):
    image = _image(31, 27)
    for size in (2, 128):
        rendered = render_print_lab(image, {"mode": "CMYK", "cell_size": size})
        assert rendered.size == image.size
    clean = export_print_separations(
        image, {"mode": "CMYK", "cell_size": 7, "seed": 4}, tmp_path / "clean", stem="p"
    )
    dirty = export_print_separations(
        image,
        {
            "mode": "CMYK", "cell_size": 7, "seed": 4, "dot_gain": 35,
            "roughness": .5, "missing_ink": .25, "ink_spread": .35,
            "paper_grain": .2, "squeegee": .3,
        },
        tmp_path / "dirty", stem="p",
    )
    clean_svg = next(p for p in clean if p.name == "p_cyan.svg").read_text(encoding="utf-8")
    dirty_svg = next(p for p in dirty if p.name == "p_cyan.svg").read_text(encoding="utf-8")
    assert clean_svg != dirty_svg


def test_print_lab_preset_and_project_serialization(tmp_path: Path):
    from rastermint.core.presets import load_preset, save_preset
    from rastermint.core.project import load_project_file, save_project_file

    settings = ProcessingSettings()
    layer = new_effect("Print Lab")
    layer["params"].update({
        "mode": "Spot Colors", "ink_count": 5, "dot_shape": "Ellipse",
        "cell_size": 13, "dot_gain": 22, "registration_error": 1.5,
        "paper_grain": .25, "ink1_color": "#123456", "ink5_angle": 33,
    })
    settings.effect_stack = [layer]

    preset_path = tmp_path / "print.json"
    save_preset(preset_path, settings, name="Print Test")
    restored = load_preset(preset_path)
    params = normalize_effect_stack(restored.effect_stack, restored)[0]["params"]
    assert params["mode"] == "Spot Colors"
    assert params["ink_count"] == 5
    assert params["dot_shape"] == "Ellipse"
    assert params["ink1_color"] == "#123456"
    assert float(params["ink5_angle"]) == 33

    project_path = save_project_file(tmp_path / "print-project", {"settings": settings.to_dict()})
    payload = load_project_file(project_path)
    restored_project = ProcessingSettings.from_dict(payload["settings"])
    project_params = normalize_effect_stack(restored_project.effect_stack, restored_project)[0]["params"]
    assert project_params["cell_size"] == 13
    assert float(project_params["registration_error"]) == 1.5
    assert float(project_params["paper_grain"]) == .25
