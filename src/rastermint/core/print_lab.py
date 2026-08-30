# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""AM halftone / screen-print simulation and separation export.

The ordinary RasterMint Halftone dither intentionally remains separate.  This
module builds real independent ink coverage maps, screens each separation at
its own angle/phase/registration, composites inks subtractively, and can emit
vector separation artwork without embedding raster images in SVG wrappers.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image

from .color_utils import hex_to_rgb

DEFAULT_ANGLES = (15.0, 75.0, 0.0, 45.0)
DEFAULT_CMYK_COLORS = ("#00AEEF", "#EC008C", "#FFF200", "#111111")
DEFAULT_RGB_COLORS = ("#F23B3B", "#35B85A", "#3978F6")
DEFAULT_SPOT_COLORS = (
    "#E63946", "#1D3557", "#F4A261", "#2A9D8F",
    "#6D597A", "#F2CC8F", "#457B9D", "#222222",
)

@dataclass(frozen=True)
class InkSeparation:
    name: str
    color: str
    angle: float
    offset_x: float
    offset_y: float
    phase_x: float
    phase_y: float
    opacity: float
    coverage: np.ndarray


def _clamp(value: Any, low: float, high: float, default: float) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return default


def _int(value: Any, low: int, high: int, default: int) -> int:
    try:
        return max(low, min(high, int(round(float(value)))))
    except (TypeError, ValueError):
        return default


def _color(value: Any, default: str) -> str:
    text = str(value or default).strip()
    try:
        hex_to_rgb(text)
        return text.upper()
    except Exception:
        return default


def _ink_param(params: dict[str, Any], index: int, key: str, default: Any) -> Any:
    return params.get(f"ink{index + 1}_{key}", default)


def normalize_print_params(params: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(params or {})
    mode = str(raw.get("mode", "CMYK") or "CMYK")
    if mode not in {"Monochrome", "CMYK", "RGB", "Spot Colors"}:
        mode = "CMYK"
    dot_shape = str(raw.get("dot_shape", "Round") or "Round")
    if dot_shape not in {"Round", "Ellipse", "Square", "Diamond", "Line"}:
        dot_shape = "Round"
    preview = str(raw.get("preview", "Composite") or "Composite")
    out: dict[str, Any] = {
        "mode": mode,
        "cell_size": _int(raw.get("cell_size", 8), 2, 128, 8),
        "dot_shape": dot_shape,
        "dot_gain": _clamp(raw.get("dot_gain", 0.0), -50.0, 100.0, 0.0),
        "black_mix": _clamp(raw.get("black_mix", 100.0), 0.0, 100.0, 100.0),
        "phase_offsets": bool(raw.get("phase_offsets", False)),
        "registration_error": _clamp(raw.get("registration_error", 0.0), 0.0, 64.0, 0.0),
        "roughness": _clamp(raw.get("roughness", 0.0), 0.0, 1.0, 0.0),
        "missing_ink": _clamp(raw.get("missing_ink", 0.0), 0.0, 1.0, 0.0),
        "ink_spread": _clamp(raw.get("ink_spread", 0.0), 0.0, 1.0, 0.0),
        "paper_grain": _clamp(raw.get("paper_grain", 0.0), 0.0, 1.0, 0.0),
        "squeegee": _clamp(raw.get("squeegee", 0.0), 0.0, 1.0, 0.0),
        "paper_color": _color(raw.get("paper_color"), "#F5F0E5"),
        "overprint": bool(raw.get("overprint", True)),
        "ink_count": _int(raw.get("ink_count", 4), 1, 8, 4),
        "preview": preview,
        "seed": _int(raw.get("seed", 1), 0, 999999, 1),
    }
    for index in range(8):
        if mode == "CMYK" and index < 4:
            default_color = DEFAULT_CMYK_COLORS[index]
            default_angle = DEFAULT_ANGLES[index]
        elif mode == "RGB" and index < 3:
            default_color = DEFAULT_RGB_COLORS[index]
            default_angle = (15.0, 75.0, 45.0)[index]
        else:
            default_color = DEFAULT_SPOT_COLORS[index]
            default_angle = DEFAULT_ANGLES[index % 4] + (index // 4) * 7.5
        out[f"ink{index + 1}_color"] = _color(_ink_param(raw, index, "color", default_color), default_color)
        out[f"ink{index + 1}_angle"] = _clamp(_ink_param(raw, index, "angle", default_angle), -180.0, 180.0, default_angle)
        out[f"ink{index + 1}_offset_x"] = _clamp(_ink_param(raw, index, "offset_x", 0.0), -128.0, 128.0, 0.0)
        out[f"ink{index + 1}_offset_y"] = _clamp(_ink_param(raw, index, "offset_y", 0.0), -128.0, 128.0, 0.0)
        out[f"ink{index + 1}_phase_x"] = _clamp(_ink_param(raw, index, "phase_x", 0.0), -1.0, 1.0, 0.0)
        out[f"ink{index + 1}_phase_y"] = _clamp(_ink_param(raw, index, "phase_y", 0.0), -1.0, 1.0, 0.0)
        out[f"ink{index + 1}_opacity"] = _clamp(_ink_param(raw, index, "opacity", 1.0), 0.0, 1.0, 1.0)
    return out


def _rgb_alpha_array(image: Image.Image | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return normalized RGB plus source coverage for transparent inputs.

    Transparent pixels must not create ink on exported stencils.  PIL's plain
    ``convert("RGB")`` drops alpha but keeps hidden RGB values, so separation
    coverage is explicitly multiplied by source alpha instead.
    """
    if isinstance(image, Image.Image):
        rgba = np.asarray(image.convert("RGBA"), dtype=np.float32)
        rgb = rgba[..., :3]
        alpha = rgba[..., 3] / 255.0
    else:
        arr = np.asarray(image, dtype=np.float32)
        if arr.ndim != 3 or arr.shape[2] < 3:
            raise ValueError("Print Lab requires an RGB or RGBA image")
        rgb = arr[..., :3]
        alpha = arr[..., 3] / 255.0 if arr.shape[2] >= 4 else np.ones(arr.shape[:2], dtype=np.float32)
    return np.clip(rgb / 255.0, 0.0, 1.0), np.clip(alpha, 0.0, 1.0).astype(np.float32)


def _rgb_array(image: Image.Image | np.ndarray) -> np.ndarray:
    # Kept as a small internal convenience for callers that only need colour.
    return _rgb_alpha_array(image)[0]


def _color_distance_weights(rgb: np.ndarray, colors: list[np.ndarray]) -> np.ndarray:
    # Soft colour assignment lets neighbouring spot inks overlap naturally.
    stack = np.stack(colors, axis=0).astype(np.float32) / 255.0
    diff = rgb[..., None, :] - stack[None, None, :, :]
    dist2 = np.sum(diff * diff, axis=-1)
    weights = np.exp(-dist2 * 8.0)
    darkness = np.clip(1.0 - (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]), 0.0, 1.0)
    weights *= (0.25 + 0.75 * darkness[..., None])
    total = np.maximum(np.sum(weights, axis=-1, keepdims=True), 1e-6)
    return np.clip(weights / total * np.minimum(1.0, darkness[..., None] * 1.35 + 0.15), 0.0, 1.0)


def build_separations(image: Image.Image | np.ndarray, params: dict[str, Any] | None) -> tuple[list[InkSeparation], dict[str, Any]]:
    p = normalize_print_params(params)
    rgb, source_alpha = _rgb_alpha_array(image)
    mode = p["mode"]
    specs: list[tuple[str, str, np.ndarray]] = []

    if mode == "Monochrome":
        lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
        specs = [("Black", p["ink1_color"], 1.0 - lum)]
    elif mode == "CMYK":
        c0, m0, y0 = 1.0 - rgb[..., 0], 1.0 - rgb[..., 1], 1.0 - rgb[..., 2]
        k_base = np.minimum(np.minimum(c0, m0), y0)
        k = np.clip(k_base * (p["black_mix"] / 100.0), 0.0, 1.0)
        # Under-colour removal: moving darkness into K genuinely changes the
        # chromatic separations rather than merely multiplying K afterwards.
        denom = np.maximum(1.0 - k, 1e-5)
        c = np.clip((c0 - k) / denom, 0.0, 1.0)
        m = np.clip((m0 - k) / denom, 0.0, 1.0)
        y = np.clip((y0 - k) / denom, 0.0, 1.0)
        specs = [
            ("Cyan", p["ink1_color"], c),
            ("Magenta", p["ink2_color"], m),
            ("Yellow", p["ink3_color"], y),
            ("Black", p["ink4_color"], k),
        ]
    elif mode == "RGB":
        # Additive source channels represented as physical coloured inks.
        specs = [
            ("Red", p["ink1_color"], rgb[..., 0]),
            ("Green", p["ink2_color"], rgb[..., 1]),
            ("Blue", p["ink3_color"], rgb[..., 2]),
        ]
    else:
        count = p["ink_count"]
        ink_colors = [np.asarray(hex_to_rgb(p[f"ink{i + 1}_color"]), dtype=np.float32) for i in range(count)]
        weights = _color_distance_weights(rgb, ink_colors)
        specs = [(f"Spot {i + 1}", p[f"ink{i + 1}_color"], weights[..., i]) for i in range(count)]

    # Transparent source regions are unprinted paper, regardless of hidden RGB.
    specs = [(name, color, np.asarray(coverage, dtype=np.float32) * source_alpha) for name, color, coverage in specs]

    separations: list[InkSeparation] = []
    reg = float(p["registration_error"])
    seed = int(p["seed"])
    for index, (name, color, coverage) in enumerate(specs):
        # Deterministic alternating registration error produces repeatable
        # vintage misregistration without requiring hidden random state.
        angle_seed = (seed * 0.017 + index * 1.618) * 2.0 * math.pi
        auto_x = math.sin(angle_seed) * reg
        auto_y = math.cos(angle_seed * 1.37) * reg
        separations.append(InkSeparation(
            name=name,
            color=color,
            angle=float(p[f"ink{index + 1}_angle"]),
            offset_x=float(p[f"ink{index + 1}_offset_x"]) + auto_x,
            offset_y=float(p[f"ink{index + 1}_offset_y"]) + auto_y,
            phase_x=float(p[f"ink{index + 1}_phase_x"]) if p["phase_offsets"] else 0.0,
            phase_y=float(p[f"ink{index + 1}_phase_y"]) if p["phase_offsets"] else 0.0,
            opacity=float(p[f"ink{index + 1}_opacity"]),
            coverage=np.asarray(coverage, dtype=np.float32),
        ))
    return separations, p


def _hash_noise(x: np.ndarray, y: np.ndarray, seed: float) -> np.ndarray:
    return np.mod(np.sin(x * 12.9898 + y * 78.233 + seed * 37.719) * 43758.5453, 1.0).astype(np.float32)


def _shape_rank(u: np.ndarray, v: np.ndarray, shape: str) -> np.ndarray:
    au = np.abs(u)
    av = np.abs(v)
    if shape == "Square":
        return np.clip((2.0 * np.maximum(au, av)) ** 2, 0.0, 1.0)
    if shape == "Diamond":
        return np.clip((au + av) ** 2 * 2.0, 0.0, 1.0)
    if shape == "Line":
        return np.clip(2.0 * av, 0.0, 1.0)
    if shape == "Ellipse":
        return np.clip(math.pi * (u * u * 0.58 + v * v * 1.55), 0.0, 1.0)
    return np.clip(math.pi * (u * u + v * v), 0.0, 1.0)


def screen_separation(sep: InkSeparation, p: dict[str, Any]) -> np.ndarray:
    coverage = np.asarray(sep.coverage, dtype=np.float32)
    h, w = coverage.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cell = float(p["cell_size"])
    theta = math.radians(sep.angle)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    cx, cy = (w - 1) * 0.5, (h - 1) * 0.5
    sx = xx - cx - sep.offset_x
    sy = yy - cy - sep.offset_y
    rx = cos_t * sx + sin_t * sy
    ry = -sin_t * sx + cos_t * sy
    rx = rx / cell + sep.phase_x
    ry = ry / cell + sep.phase_y
    u = np.mod(rx + 0.5, 1.0) - 0.5
    v = np.mod(ry + 0.5, 1.0) - 0.5
    rank = _shape_rank(u, v, p["dot_shape"])

    dot_gain = float(p["dot_gain"]) / 100.0
    adjusted = coverage + dot_gain * (0.25 + 0.75 * coverage) * (1.0 - coverage)

    rough = float(p["roughness"])
    spread = float(p["ink_spread"])
    grain = float(p["paper_grain"])
    missing = float(p["missing_ink"])
    squeegee = float(p["squeegee"])
    seed = float(p["seed"])
    if rough or spread or grain or missing or squeegee:
        fine = _hash_noise(xx, yy, seed + sep.angle * 0.01)
        coarse = _hash_noise(np.floor(xx / max(3.0, cell * 1.5)), np.floor(yy / max(3.0, cell * 1.5)), seed + 19.0)
        if rough:
            rank = np.clip(rank + (fine - 0.5) * rough * 0.22, 0.0, 1.0)
        if spread:
            adjusted += (fine - 0.35) * spread * 0.18
        if grain:
            adjusted -= (fine - 0.25) * grain * 0.16
        if missing:
            dropout = np.clip((coarse - (0.90 - missing * 0.55)) * 6.0, 0.0, 1.0)
            adjusted *= 1.0 - dropout
        if squeegee:
            bands = (0.5 + 0.5 * np.sin((yy / max(5.0, cell * 3.0)) * 2.0 * math.pi + seed))
            adjusted *= 1.0 - bands * squeegee * 0.20

    return (np.clip(adjusted, 0.0, 1.0) >= rank).astype(np.float32)


def _paper_rgb(p: dict[str, Any]) -> np.ndarray:
    return np.asarray(hex_to_rgb(p["paper_color"]), dtype=np.float32) / 255.0


def render_print_lab(image: Image.Image | np.ndarray, params: dict[str, Any] | None) -> Image.Image:
    separations, p = build_separations(image, params)
    screens = [screen_separation(sep, p) for sep in separations]
    preview = str(p.get("preview", "Composite"))

    if preview != "Composite":
        index = next((i for i, sep in enumerate(separations) if sep.name == preview), -1)
        if index < 0 and preview.startswith("Spot "):
            try:
                index = int(preview.split()[-1]) - 1
            except ValueError:
                index = -1
        if 0 <= index < len(screens):
            mask = screens[index]
            # Black-on-white separation proof is easier to inspect and maps
            # directly to stencil artwork exported by the vector path.
            gray = np.clip((1.0 - mask) * 255.0, 0, 255).astype(np.uint8)
            return Image.fromarray(np.repeat(gray[..., None], 3, axis=2), "RGB")

    h, w = screens[0].shape if screens else _rgb_array(image).shape[:2]
    paper = _paper_rgb(p)
    out = np.broadcast_to(paper, (h, w, 3)).copy().astype(np.float32)
    for sep, mask in zip(separations, screens):
        ink = np.asarray(hex_to_rgb(sep.color), dtype=np.float32) / 255.0
        a = np.clip(mask * sep.opacity, 0.0, 1.0)[..., None]
        if p["overprint"]:
            # Multiplicative transmittance: overprints darken naturally instead
            # of averaging RGB values and washing the intersection out.
            out *= (1.0 - a) + a * ink[None, None, :]
        else:
            out = out * (1.0 - a) + ink[None, None, :] * a
    return Image.fromarray(np.clip(np.rint(out * 255.0), 0, 255).astype(np.uint8), "RGB")


def _scalar_hash_noise(x: float, y: float, seed: float) -> float:
    value = math.sin(x * 12.9898 + y * 78.233 + seed * 37.719) * 43758.5453
    return value - math.floor(value)


def _vector_cell_coverage(coverage: float, x: float, y: float, sep: InkSeparation, p: dict[str, Any]) -> float:
    """Approximate the raster print imperfections at one vector cell.

    SVG separations stay true vector geometry, but their individual dots still
    need to reflect the same user-visible dot gain, roughness, weak ink, grain,
    spread and squeegee controls as the raster/composite preview.
    """
    cov = max(0.0, min(1.0, float(coverage)))
    gain = float(p["dot_gain"]) / 100.0
    cov += gain * (0.25 + 0.75 * cov) * (1.0 - cov)

    fine = _scalar_hash_noise(x, y, float(p["seed"]) + sep.angle * 0.01)
    coarse_cell = max(3.0, float(p["cell_size"]) * 1.5)
    coarse = _scalar_hash_noise(math.floor(x / coarse_cell), math.floor(y / coarse_cell), float(p["seed"]) + 19.0)

    rough = float(p["roughness"])
    spread = float(p["ink_spread"])
    grain = float(p["paper_grain"])
    missing = float(p["missing_ink"])
    squeegee = float(p["squeegee"])
    if rough:
        cov += (fine - 0.5) * rough * 0.16
    if spread:
        cov += (fine - 0.35) * spread * 0.18
    if grain:
        cov -= (fine - 0.25) * grain * 0.16
    if missing:
        dropout = max(0.0, min(1.0, (coarse - (0.90 - missing * 0.55)) * 6.0))
        cov *= 1.0 - dropout
    if squeegee:
        bands = 0.5 + 0.5 * math.sin((y / max(5.0, float(p["cell_size"]) * 3.0)) * 2.0 * math.pi + float(p["seed"]))
        cov *= 1.0 - bands * squeegee * 0.20
    return max(0.0, min(1.0, cov))


def _svg_shape(shape: str, x: float, y: float, cell: float, coverage: float, angle: float) -> str:
    coverage = max(0.0, min(1.0, float(coverage)))
    if coverage <= 0.001:
        return ""
    rotate = f' transform="rotate({angle:.4f} {x:.3f} {y:.3f})"'
    # Area-driven dimensions approximate the raster screen while preserving
    # actual vector geometry for cutters/RIP software.
    if shape == "Square":
        side = cell * math.sqrt(coverage)
        return f'<rect x="{x-side/2:.3f}" y="{y-side/2:.3f}" width="{side:.3f}" height="{side:.3f}"{rotate}/>'
    if shape == "Diamond":
        r = cell * math.sqrt(coverage / 2.0)
        pts = f"{x:.3f},{y-r:.3f} {x+r:.3f},{y:.3f} {x:.3f},{y+r:.3f} {x-r:.3f},{y:.3f}"
        return f'<polygon points="{pts}"{rotate}/>'
    if shape == "Line":
        height = max(0.15, cell * coverage)
        return f'<rect x="{x-cell/2:.3f}" y="{y-height/2:.3f}" width="{cell:.3f}" height="{height:.3f}"{rotate}/>'
    area = coverage * cell * cell
    if shape == "Ellipse":
        ratio = 1.65
        ry = math.sqrt(area / (math.pi * ratio))
        rx = ry * ratio
        return f'<ellipse cx="{x:.3f}" cy="{y:.3f}" rx="{rx:.3f}" ry="{ry:.3f}"{rotate}/>'
    radius = math.sqrt(area / math.pi)
    return f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{radius:.3f}"/>'


def separation_svg(sep: InkSeparation, p: dict[str, Any]) -> str:
    coverage = np.asarray(sep.coverage, dtype=np.float32)
    h, w = coverage.shape
    cell = float(p["cell_size"])
    cx, cy = (w - 1) * 0.5, (h - 1) * 0.5
    theta = math.radians(sep.angle)
    cos_t, sin_t = math.cos(theta), math.sin(theta)

    # The raster screen defines cells in rotated screen coordinates:
    #   rx / cell + phase_x = integer
    #   ry / cell + phase_y = integer
    # Solve those equations here so SVG dot centres align with the raster
    # preview instead of tracing a rasterized mask.
    # Bound grid indices by the inverse-transformed page corners. This avoids
    # scanning a huge diagonal square for high-resolution/fine-cell exports.
    corner_screen: list[tuple[float, float]] = []
    for px, py in ((-cell, -cell), (w - 1 + cell, -cell), (-cell, h - 1 + cell), (w - 1 + cell, h - 1 + cell)):
        sx = px - cx - sep.offset_x
        sy = py - cy - sep.offset_y
        corner_screen.append((cos_t * sx + sin_t * sy, -sin_t * sx + cos_t * sy))
    gx_values = [rx / cell + sep.phase_x for rx, _ in corner_screen]
    gy_values = [ry / cell + sep.phase_y for _, ry in corner_screen]
    gx0, gx1 = math.floor(min(gx_values)) - 1, math.ceil(max(gx_values)) + 1
    gy0, gy1 = math.floor(min(gy_values)) - 1, math.ceil(max(gy_values)) + 1

    shapes: list[str] = []
    for gy in range(gy0, gy1 + 1):
        ry = (gy - sep.phase_y) * cell
        for gx in range(gx0, gx1 + 1):
            rx = (gx - sep.phase_x) * cell
            x = cx + sep.offset_x + cos_t * rx - sin_t * ry
            y = cy + sep.offset_y + sin_t * rx + cos_t * ry
            if x < -cell or x > w - 1 + cell or y < -cell or y > h - 1 + cell:
                continue
            ix = max(0, min(w - 1, int(round(x))))
            iy = max(0, min(h - 1, int(round(y))))
            cov = _vector_cell_coverage(float(coverage[iy, ix]), x, y, sep, p)
            shape_markup = _svg_shape(p["dot_shape"], x, y, cell, cov, sep.angle)
            if shape_markup:
                shapes.append(shape_markup)

    ink = escape(sep.color)
    body = "\n".join(shapes)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
        f'<defs><clipPath id="page"><rect width="{w}" height="{h}"/></clipPath></defs>\n'
        f'<g clip-path="url(#page)" fill="{ink}" fill-opacity="{sep.opacity:.5f}">\n'
        f'{body}\n</g>\n</svg>\n'
    )


def export_print_separations(
    image: Image.Image,
    params: dict[str, Any] | None,
    folder: str | Path,
    *,
    stem: str = "image",
    raster_separations: bool = True,
) -> list[Path]:
    target = Path(folder)
    target.mkdir(parents=True, exist_ok=True)
    separations, p = build_separations(image, params)
    paths: list[Path] = []
    safe_stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(stem or "image")).strip("_") or "image"
    for sep in separations:
        slug = sep.name.lower().replace(" ", "_")
        svg_path = target / f"{safe_stem}_{slug}.svg"
        svg_path.write_text(separation_svg(sep, p), encoding="utf-8")
        paths.append(svg_path)
        if raster_separations:
            mask = screen_separation(sep, p)
            png = np.clip((1.0 - mask) * 255.0, 0, 255).astype(np.uint8)
            png_path = target / f"{safe_stem}_{slug}.png"
            Image.fromarray(png, "L").save(png_path)
            paths.append(png_path)
    composite_params = dict(p)
    composite_params["preview"] = "Composite"
    composite_path = target / f"{safe_stem}_composite.png"
    render_print_lab(image, composite_params).save(composite_path)
    paths.append(composite_path)
    return paths
