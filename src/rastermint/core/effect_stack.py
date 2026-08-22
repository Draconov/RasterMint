# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from .dither import ALGORITHMS, apply_dither
from .palette import hex_to_rgb, palette_array


# The UI consumes this schema directly. Keeping effect metadata in the core means
# adding a new effect does not require hard-coding another form in the QML UI.
EFFECT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "Adjustments": {"params": {
        "brightness": {"type": "int", "label": "Brightness", "default": 0, "min": -100, "max": 100, "step": 1, "animatable": True},
        "contrast": {"type": "int", "label": "Contrast", "default": 0, "min": -100, "max": 100, "step": 1, "animatable": True},
        "saturation": {"type": "int", "label": "Saturation", "default": 0, "min": -100, "max": 100, "step": 1, "animatable": True},
        "gamma": {"type": "float", "label": "Gamma", "default": 1.0, "min": 0.1, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
    }},
    "Local Contrast": {"params": {
        "amount": {"type": "int", "label": "Amount", "default": 120, "min": 0, "max": 400, "step": 5, "suffix": "%", "animatable": True},
        "radius": {"type": "float", "label": "Radius", "default": 2.0, "min": 0.1, "max": 30.0, "step": 0.25, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "threshold": {"type": "int", "label": "Threshold", "default": 2, "min": 0, "max": 50, "step": 1},
    }},
    "Hue Rotate": {"params": {
        "degrees": {"type": "int", "label": "Degrees", "default": 0, "min": -180, "max": 180, "step": 1, "animatable": True},
    }},
    "Grayscale": {"params": {}},
    "Invert": {"params": {}},
    "Gaussian Blur": {"params": {
        "radius": {"type": "float", "label": "Radius", "default": 2.0, "min": 0.0, "max": 30.0, "step": 0.25, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
    }},
    "Median Denoise": {"params": {
        "radius": {"type": "int", "label": "Radius", "default": 1, "min": 1, "max": 5, "step": 1, "pixel_scaled": True},
    }},
    "Sharpen": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 1.5, "min": 0.0, "max": 5.0, "step": 0.1, "decimals": 2, "animatable": True},
    }},
    "Glow": {"params": {
        "radius": {"type": "float", "label": "Radius", "default": 5.0, "min": 0.0, "max": 40.0, "step": 0.5, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "intensity": {"type": "float", "label": "Intensity", "default": 0.35, "min": 0.0, "max": 2.0, "step": 0.05, "decimals": 2, "animatable": True},
    }},
    "Bloom": {"params": {
        "threshold": {"type": "float", "label": "Threshold", "default": 0.65, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "soft_knee": {"type": "float", "label": "Soft knee", "default": 0.20, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "radius": {"type": "float", "label": "Radius", "default": 10.0, "min": 0.0, "max": 80.0, "step": 0.5, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "intensity": {"type": "float", "label": "Intensity", "default": 0.80, "min": 0.0, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
        "blend": {"type": "choice", "label": "Blend", "default": "Screen", "options": ["Screen", "Add"]},
    }},
    "JPEG Compression": {"params": {
        "quality": {"type": "int", "label": "Quality", "default": 35, "min": 5, "max": 95, "step": 1, "animatable": True},
    }},
    "Chromatic Shift": {"params": {
        "amount": {"type": "int", "label": "Offset", "default": 3, "min": -40, "max": 40, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
    }},
    "RGB Split": {"params": {
        "x": {"type": "int", "label": "X offset", "default": 3, "min": -64, "max": 64, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "y": {"type": "int", "label": "Y offset", "default": 0, "min": -64, "max": 64, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
    }},
    "Posterize": {"params": {
        "levels": {"type": "int", "label": "Levels", "default": 6, "min": 2, "max": 64, "step": 1, "animatable": True},
    }},
    "Scanlines": {"params": {
        "spacing": {"type": "int", "label": "Spacing", "default": 3, "min": 2, "max": 16, "step": 1, "pixel_scaled": True},
        "strength": {"type": "float", "label": "Darken", "default": 0.25, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
    }},
    "Interlace": {"params": {
        "offset": {"type": "int", "label": "Odd-line shift", "default": 2, "min": -32, "max": 32, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "darken": {"type": "float", "label": "Odd-line darken", "default": 0.12, "min": 0.0, "max": 1.0, "step": 0.02, "decimals": 2, "animatable": True},
    }},
    "Noise": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 12.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Temporal Flicker": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 0.08, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "speed": {"type": "float", "label": "Speed", "default": 4.0, "min": 0.1, "max": 30.0, "step": 0.1, "decimals": 1, "suffix": " Hz", "animatable": True},
    }},
    "Temporal Pattern": {"params": {
        "pattern": {"type": "choice", "label": "Pattern", "default": "Wave X", "options": ["Pulse", "Wave X", "Wave Y", "Diagonal Wave", "Checker Phase", "Scan Sweep", "Noise Drift", "Alternating", "Radial Pulse"]},
        "amount": {"type": "float", "label": "Amount", "default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "speed": {"type": "float", "label": "Speed", "default": 1.0, "min": 0.0, "max": 30.0, "step": 0.1, "decimals": 1, "suffix": " Hz", "animatable": True},
        "scale": {"type": "float", "label": "Scale", "default": 32.0, "min": 2.0, "max": 256.0, "step": 1.0, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "phase": {"type": "float", "label": "Phase", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "Pixel Aspect Ratio": {"params": {
        "x": {"type": "float", "label": "Pixel width", "default": 1.0, "min": 0.25, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
        "y": {"type": "float", "label": "Pixel height", "default": 1.0, "min": 0.25, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
        "resample": {"type": "choice", "label": "Resample", "default": "Nearest", "options": ["Nearest", "Bilinear", "Bicubic", "Lanczos"]},
    }},
    "Pixelate": {"params": {
        "size": {"type": "int", "label": "Pixel size", "default": 2, "min": 1, "max": 64, "step": 1, "animatable": True, "pixel_scaled": True},
    }},
    "Pixel Sort": {"params": {
        "threshold": {"type": "float", "label": "Threshold", "default": 0.45, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "direction": {"type": "choice", "label": "Direction", "default": "Horizontal", "options": ["Horizontal", "Vertical"]},
        "reverse": {"type": "bool", "label": "Reverse", "default": False},
    }},
    "Screen Melt": {"params": {
        "amount": {"type": "int", "label": "Max drop", "default": 24, "min": 0, "max": 256, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "column_width": {"type": "int", "label": "Column width", "default": 6, "min": 1, "max": 64, "step": 1, "pixel_scaled": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Block Shuffle": {"params": {
        "block": {"type": "int", "label": "Block size", "default": 16, "min": 2, "max": 128, "step": 1, "suffix": " px", "pixel_scaled": True},
        "amount": {"type": "float", "label": "Fraction", "default": 0.35, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Pixel Scatter": {"params": {
        "distance": {"type": "int", "label": "Distance", "default": 8, "min": 0, "max": 128, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "density": {"type": "float", "label": "Density", "default": 0.15, "min": 0.0, "max": 1.0, "step": 0.02, "decimals": 2, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Data Shift": {"params": {
        "amount": {"type": "int", "label": "Horizontal shift", "default": 24, "min": 0, "max": 256, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "band_height": {"type": "int", "label": "Band height", "default": 8, "min": 1, "max": 64, "step": 1, "suffix": " px", "pixel_scaled": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Row Shift": {"params": {
        "amount": {"type": "int", "label": "Max shift", "default": 12, "min": 0, "max": 128, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "period": {"type": "int", "label": "Row period", "default": 4, "min": 1, "max": 64, "step": 1, "pixel_scaled": True},
    }},
    "Column Shift": {"params": {
        "amount": {"type": "int", "label": "Max shift", "default": 12, "min": 0, "max": 128, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "period": {"type": "int", "label": "Column period", "default": 4, "min": 1, "max": 64, "step": 1, "pixel_scaled": True},
    }},
    "Cellular Automata": {"params": {
        "threshold": {"type": "float", "label": "Threshold", "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "steps": {"type": "int", "label": "Steps", "default": 2, "min": 1, "max": 12, "step": 1},
        "blend": {"type": "float", "label": "Blend", "default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
    }},
    "Databend": {"params": {
        "quality": {"type": "int", "label": "JPEG quality", "default": 25, "min": 5, "max": 90, "step": 1},
        "shift": {"type": "int", "label": "Band shift", "default": 28, "min": 0, "max": 256, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Channel Swap": {"params": {
        "order": {"type": "choice", "label": "Order", "default": "GBR", "options": ["RGB", "RBG", "GRB", "GBR", "BRG", "BGR"]},
    }},
    "Pixel Material": {"params": {
        "style": {"type": "choice", "label": "Style", "default": "Flat", "options": ["Flat", "Round Dots", "CRT Phosphor", "LED", "LCD", "Fuse Bead", "Cross Stitch", "Brick", "Mosaic", "Halftone Dot", "ASCII Tile", "Custom Sprite"]},
        "cell_size": {"type": "int", "label": "Cell size", "default": 8, "min": 2, "max": 64, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "gap": {"type": "int", "label": "Gap", "default": 1, "min": 0, "max": 12, "step": 1, "suffix": " px", "pixel_scaled": True},
        "background": {"type": "color", "label": "Background", "default": "#101217"},
        "sprite_path": {"type": "file", "label": "Custom sprite", "default": "", "file_filter": "Images (*.png *.webp *.bmp *.gif);;All files (*.*)"},
    }},
    "Text Overlay": {"params": {
        "text": {"type": "text", "label": "Text", "default": "GAME OVER"},
        "x": {"type": "float", "label": "X", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "y": {"type": "float", "label": "Y", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "size": {"type": "int", "label": "Size", "default": 18, "min": 6, "max": 128, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "color": {"type": "color", "label": "Color", "default": "#FFFFFF"},
        "outline": {"type": "int", "label": "Outline", "default": 1, "min": 0, "max": 8, "step": 1, "suffix": " px", "pixel_scaled": True},
        "shadow": {"type": "int", "label": "Shadow", "default": 0, "min": 0, "max": 16, "step": 1, "suffix": " px", "pixel_scaled": True},
    }},
    "Dither": {"params": {
        "algorithm": {"type": "choice", "label": "Algorithm", "default": "Floyd-Steinberg", "options": ALGORITHMS},
        "mix": {"type": "float", "label": "Mix", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
        "strength": {"type": "float", "label": "Strength", "default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05, "decimals": 2, "animatable": True},
        "threshold": {"type": "float", "label": "Threshold", "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "serpentine": {"type": "bool", "label": "Serpentine", "default": True},
    }},
}

EFFECT_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Color & Tone", (
        "Adjustments", "Local Contrast", "Hue Rotate", "Grayscale", "Invert", "Posterize",
    )),
    ("Detail & Light", (
        "Gaussian Blur", "Median Denoise", "Sharpen", "Glow", "Bloom",
    )),
    ("Pixel & Dither", (
        "Pixelate", "Dither", "Pixel Material",
    )),
    ("Display & Analog", (
        "Pixel Aspect Ratio", "Scanlines", "Interlace", "JPEG Compression",
    )),
    ("Glitch & Channels", (
        "Chromatic Shift", "RGB Split", "Pixel Sort", "Screen Melt", "Block Shuffle",
        "Pixel Scatter", "Data Shift", "Row Shift", "Column Shift", "Databend", "Channel Swap",
    )),
    ("Noise & Motion", (
        "Noise", "Temporal Flicker", "Temporal Pattern", "Cellular Automata",
    )),
    ("Text & Overlay", (
        "Text Overlay",
    )),
)


def effect_categories() -> list[dict[str, object]]:
    """Return effect categories for the add-layer UI.

    Any future effect that has not been assigned yet is kept reachable in an
    automatic Other category instead of silently disappearing from the UI.
    """
    grouped: list[dict[str, object]] = []
    seen: set[str] = set()
    for name, kinds in EFFECT_CATEGORIES:
        available = [kind for kind in kinds if kind in EFFECT_DEFINITIONS]
        if available:
            grouped.append({"name": name, "effects": available})
            seen.update(available)
    uncategorized = [kind for kind in EFFECT_DEFINITIONS if kind not in seen]
    if uncategorized:
        grouped.append({"name": "Other", "effects": uncategorized})
    return grouped


# Numeric effect controls are animatable unless they are identity/random seeds.
# This keeps the timeline capability aligned with the effect schema without
# requiring a second hand-maintained list of motion-capable parameters.
for _definition in EFFECT_DEFINITIONS.values():
    for _param_name, _spec in _definition.get("params", {}).items():
        if _spec.get("type") in {"int", "float"} and _param_name != "seed":
            _spec.setdefault("animatable", True)


def new_effect(kind: str, *, enabled: bool = True, effect_id: str | None = None) -> dict[str, Any]:
    if kind not in EFFECT_DEFINITIONS:
        raise ValueError(f"Unknown effect type: {kind}")
    params = {key: deepcopy(spec.get("default")) for key, spec in EFFECT_DEFINITIONS[kind]["params"].items()}
    return {"id": effect_id or uuid4().hex[:12], "kind": kind, "enabled": bool(enabled), "params": params}


def default_effect_stack(settings: Any | None = None) -> list[dict[str, Any]]:
    adjustments = new_effect("Adjustments", effect_id="adjustments")
    grayscale = new_effect("Grayscale", enabled=False, effect_id="grayscale")
    invert = new_effect("Invert", enabled=False, effect_id="invert")
    blur = new_effect("Gaussian Blur", enabled=False, effect_id="blur")
    sharpen = new_effect("Sharpen", enabled=False, effect_id="sharpen")
    pixelate = new_effect("Pixelate", effect_id="pixelate")
    dither = new_effect("Dither", effect_id="dither")
    if settings is not None:
        adjustments["params"].update(
            brightness=int(getattr(settings, "brightness", 0)),
            contrast=int(getattr(settings, "contrast", 0)),
            saturation=int(getattr(settings, "saturation", 0)),
            gamma=float(getattr(settings, "gamma", 1.0)),
        )
        grayscale["enabled"] = bool(getattr(settings, "grayscale", False))
        invert["enabled"] = bool(getattr(settings, "invert", False))
        blur["params"]["radius"] = float(getattr(settings, "blur_radius", 0.0))
        blur["enabled"] = blur["params"]["radius"] > 0.0
        sharpen["params"]["amount"] = float(getattr(settings, "sharpen", 1.0))
        sharpen["enabled"] = abs(sharpen["params"]["amount"] - 1.0) > 1e-6
        pixelate["params"]["size"] = int(getattr(settings, "pixel_size", 1))
        pixelate["enabled"] = pixelate["params"]["size"] > 1
        dither["params"].update(
            algorithm=str(getattr(settings, "algorithm", "Floyd-Steinberg")),
            strength=float(getattr(settings, "dither_strength", 1.0)),
            serpentine=bool(getattr(settings, "serpentine", True)),
        )
    return [adjustments, grayscale, invert, blur, sharpen, pixelate, dither]


def normalize_effect_stack(stack: list[dict[str, Any]] | None, settings: Any | None = None) -> list[dict[str, Any]]:
    if not stack:
        return default_effect_stack(settings)
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in stack:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind", ""))
        if kind not in EFFECT_DEFINITIONS:
            continue
        effect_id = str(raw.get("id") or uuid4().hex[:12])
        if effect_id in seen_ids:
            effect_id = uuid4().hex[:12]
        seen_ids.add(effect_id)
        step = new_effect(kind, enabled=bool(raw.get("enabled", True)), effect_id=effect_id)
        raw_params = raw.get("params", {}) if isinstance(raw.get("params"), dict) else {}
        for key, spec in EFFECT_DEFINITIONS[kind]["params"].items():
            if key not in raw_params:
                continue
            value = raw_params[key]
            ptype = spec.get("type")
            try:
                if ptype == "int":
                    value = max(int(spec["min"]), min(int(spec["max"]), int(round(float(value)))))
                elif ptype == "float":
                    value = max(float(spec["min"]), min(float(spec["max"]), float(value)))
                elif ptype == "bool":
                    value = bool(value)
                elif ptype == "choice":
                    options = [str(v) for v in spec.get("options", [])]
                    value = str(value)
                    if options and value not in options:
                        value = str(spec.get("default", options[0]))
                elif ptype in {"text", "file"}:
                    value = str(value)
                elif ptype == "color":
                    text = str(value).strip().upper()
                    hex_to_rgb(text)
                    value = text if text.startswith("#") else f"#{text}"
            except (TypeError, ValueError):
                value = deepcopy(spec.get("default"))
            step["params"][key] = value
        normalized.append(step)
    return normalized or default_effect_stack(settings)


def scale_stack_for_preview(stack: list[dict[str, Any]], scale: float) -> list[dict[str, Any]]:
    result = normalize_effect_stack(deepcopy(stack))
    if scale >= 1.0:
        return result
    for step in result:
        definition = EFFECT_DEFINITIONS.get(step["kind"], {})
        params = step["params"]
        for key, spec in definition.get("params", {}).items():
            if not spec.get("pixel_scaled") or key not in params:
                continue
            value = params[key]
            if spec.get("type") == "int":
                params[key] = max(int(spec.get("min", 1)), int(round(float(value) * scale)))
            else:
                params[key] = max(float(spec.get("min", 0.0)), float(value) * scale)
    return result


def animatable_targets(stack: list[dict[str, Any]]) -> list[tuple[str, str, float]]:
    targets: list[tuple[str, str, float]] = []
    for step in normalize_effect_stack(stack):
        definition = EFFECT_DEFINITIONS.get(step["kind"], {})
        for key, spec in definition.get("params", {}).items():
            if not spec.get("animatable"):
                continue
            value = step["params"].get(key, spec.get("default", 0.0))
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                targets.append((f"effect:{step['id']}:{key}", f"{step['kind']} · {spec.get('label', key)}", float(value)))
    return targets


def _temporal_pattern(
    image: Image.Image,
    pattern: str,
    amount: float,
    speed: float,
    scale: float,
    phase: float,
    frame_time: float,
    seed: int,
) -> Image.Image:
    amount = max(0.0, min(1.0, float(amount)))
    if amount <= 0.0:
        return image

    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    scale = max(1.0, float(scale))
    theta = 2.0 * np.pi * (max(0.0, float(speed)) * float(frame_time) + float(phase))

    if pattern == "Pulse":
        field = np.full((h, w), np.sin(theta), dtype=np.float32)
    elif pattern == "Wave Y":
        field = np.sin((yy / scale) * 2.0 * np.pi + theta)
    elif pattern == "Diagonal Wave":
        field = np.sin(((xx + yy) / scale) * 2.0 * np.pi + theta)
    elif pattern == "Checker Phase":
        offset = theta / (2.0 * np.pi) * scale
        cells = (np.floor((xx + offset) / scale) + np.floor((yy + offset) / scale)).astype(np.int32)
        field = np.where((cells & 1) == 0, 1.0, -1.0).astype(np.float32)
    elif pattern == "Scan Sweep":
        center = ((float(frame_time) * max(0.0, float(speed)) + float(phase)) % 1.0) * max(1.0, float(h))
        distance = np.abs(yy - center)
        distance = np.minimum(distance, max(1.0, float(h)) - distance)
        field = np.clip(1.0 - distance / max(1.0, scale), 0.0, 1.0) * 2.0 - 1.0
    elif pattern == "Noise Drift":
        # Smooth deterministic pseudo-noise; no per-frame random allocation is
        # required, so scrubbing to the same time reproduces the same frame.
        base = xx * 12.9898 + yy * 78.233 + float(seed) * 0.12345
        field = np.sin(base + theta + np.sin(base * 0.17 + theta * 0.37))
    elif pattern == "Alternating":
        field = np.full((h, w), 1.0 if int(np.floor(max(0.0, speed) * frame_time + phase)) % 2 == 0 else -1.0, dtype=np.float32)
    elif pattern == "Radial Pulse":
        cx = (w - 1) * 0.5
        cy = (h - 1) * 0.5
        radius = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        field = np.sin((radius / scale) * 2.0 * np.pi - theta)
    else:  # Wave X
        field = np.sin((xx / scale) * 2.0 * np.pi + theta)

    gain = 1.0 + field[..., None] * (amount * 0.5)
    out = np.clip(arr * gain, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")


def _seed(params: dict[str, Any], frame_index: int) -> int:
    seed = int(params.get("seed", 1))
    if bool(params.get("temporal", False)):
        seed += int(frame_index) * 1009
    return seed & 0xFFFFFFFF


def _hue_rotate(image: Image.Image, degrees: int) -> Image.Image:
    if degrees % 360 == 0:
        return image
    hsv = np.asarray(image.convert("HSV"), dtype=np.uint8).copy()
    shift = int(round((degrees % 360) / 360.0 * 255.0))
    hsv[..., 0] = (hsv[..., 0].astype(np.uint16) + shift) % 256
    return Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")


def _local_contrast(image: Image.Image, amount: int, radius: float, threshold: int) -> Image.Image:
    if amount <= 0:
        return image
    return image.filter(ImageFilter.UnsharpMask(radius=max(0.1, radius), percent=max(0, amount), threshold=max(0, threshold)))


def _glow(image: Image.Image, radius: float, intensity: float) -> Image.Image:
    if radius <= 0.0 or intensity <= 0.0:
        return image
    base = np.asarray(image.convert("RGB"), dtype=np.float32)
    blurred = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=radius)), dtype=np.float32)
    glow = np.clip(blurred * intensity, 0.0, 255.0)
    out = base + glow - (base * glow / 255.0)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _bloom(
    image: Image.Image,
    threshold: float,
    soft_knee: float,
    radius: float,
    intensity: float,
    blend: str,
) -> Image.Image:
    """Bloom bright image regions and blend the result over the source.

    Unlike Glow, Bloom first extracts highlights using a luminance threshold.
    ``soft_knee`` controls how gradually pixels enter the bloom around that
    threshold, which avoids a harsh visible cutoff on gradients and photos.
    """
    radius = max(0.0, float(radius))
    intensity = max(0.0, float(intensity))
    if radius <= 0.0 or intensity <= 0.0:
        return image

    threshold = max(0.0, min(1.0, float(threshold)))
    soft_knee = max(0.0, min(1.0, float(soft_knee)))

    base = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    luminance = 0.2126 * base[..., 0] + 0.7152 * base[..., 1] + 0.0722 * base[..., 2]

    # Smoothstep around the threshold. At knee=0 this becomes a hard cutoff.
    knee = max(1e-6, soft_knee * 0.5)
    if soft_knee <= 1e-6:
        weight = (luminance >= threshold).astype(np.float32)
    else:
        lo = threshold - knee
        hi = threshold + knee
        t = np.clip((luminance - lo) / max(1e-6, hi - lo), 0.0, 1.0)
        weight = t * t * (3.0 - 2.0 * t)

    highlights = np.clip(base * weight[..., None] * 255.0, 0.0, 255.0).astype(np.uint8)
    highlight_image = Image.fromarray(highlights, "RGB")
    blurred = np.asarray(
        highlight_image.filter(ImageFilter.GaussianBlur(radius=radius)),
        dtype=np.float32,
    ) / 255.0

    bloom = np.clip(blurred * intensity, 0.0, 1.0)
    if str(blend) == "Add":
        out = np.clip(base + bloom, 0.0, 1.0)
    else:  # Screen is the safer/default photographic blend.
        out = 1.0 - (1.0 - base) * (1.0 - bloom)

    return Image.fromarray(np.clip(np.rint(out * 255.0), 0, 255).astype(np.uint8), "RGB")


def _jpeg_compression(image: Image.Image, quality: int) -> Image.Image:
    quality = max(5, min(95, int(quality)))
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality, subsampling=2, optimize=False)
    buffer.seek(0)
    with Image.open(buffer) as decoded:
        decoded.load()
        return decoded.convert("RGB")


def _chromatic_shift(image: Image.Image, amount: int) -> Image.Image:
    return _rgb_split(image, amount, 0)


def _rgb_split(image: Image.Image, x: int, y: int) -> Image.Image:
    x, y = int(x), int(y)
    if x == 0 and y == 0:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    out[..., 0] = np.roll(np.roll(arr[..., 0], y, axis=0), x, axis=1)
    out[..., 2] = np.roll(np.roll(arr[..., 2], -y, axis=0), -x, axis=1)
    return Image.fromarray(out, "RGB")


def _posterize(image: Image.Image, levels: int) -> Image.Image:
    levels = max(2, min(64, int(levels)))
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    step = 255.0 / (levels - 1)
    return Image.fromarray(np.clip(np.rint(arr / step) * step, 0, 255).astype(np.uint8), "RGB")


def _scanlines(image: Image.Image, spacing: int, strength: float) -> Image.Image:
    spacing = max(2, int(spacing))
    strength = max(0.0, min(1.0, float(strength)))
    if strength <= 0:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32).copy()
    arr[::spacing] *= 1.0 - strength
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _interlace(image: Image.Image, offset: int, darken: float) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.float32).copy()
    arr[1::2] = np.roll(arr[1::2], int(offset), axis=1)
    arr[1::2] *= 1.0 - max(0.0, min(1.0, float(darken)))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _noise(image: Image.Image, amount: float, seed: int) -> Image.Image:
    amount = max(0.0, float(amount))
    if amount <= 0.0:
        return image
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    noise = rng.normal(0.0, amount, size=arr.shape[:2])[:, :, None]
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8), "RGB")


def _flicker(image: Image.Image, amount: float, speed: float, time_seconds: float) -> Image.Image:
    amount = max(0.0, min(1.0, float(amount)))
    if amount <= 0:
        return image
    phase = np.sin(2.0 * np.pi * max(0.0, float(speed)) * max(0.0, float(time_seconds)))
    return ImageEnhance.Brightness(image).enhance(max(0.0, 1.0 + amount * phase))


def _pixel_aspect_ratio(image: Image.Image, x: float, y: float, resample: str) -> Image.Image:
    """Stretch pixel width at this point in the layer stack.

    This is intentionally an image-space layer, separate from RasterMint's
    framebuffer/display PAR metadata. Its position therefore participates in
    layer ordering just like blur, dither, or chromatic shift.
    """
    x = max(0.25, min(4.0, float(x)))
    y = max(0.25, min(4.0, float(y)))
    ratio = x / y
    target_width = max(1, round(image.width * ratio))
    if target_width == image.width:
        return image
    methods = {
        "Nearest": Image.Resampling.NEAREST,
        "Bilinear": Image.Resampling.BILINEAR,
        "Bicubic": Image.Resampling.BICUBIC,
        "Lanczos": Image.Resampling.LANCZOS,
    }
    method = methods.get(str(resample), Image.Resampling.NEAREST)
    return image.resize((target_width, image.height), method)


def _pixelate(image: Image.Image, size: int) -> Image.Image:
    size = max(1, int(size))
    if size <= 1:
        return image
    w, h = image.size
    small = image.resize((max(1, w // size), max(1, h // size)), Image.Resampling.BOX)
    return small.resize((w, h), Image.Resampling.NEAREST)


def _pixel_sort(image: Image.Image, threshold: float, direction: str, reverse: bool) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    if direction == "Vertical":
        arr = np.transpose(arr, (1, 0, 2))
    lum = (0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]) / 255.0
    for y in range(arr.shape[0]):
        mask = lum[y] >= float(threshold)
        starts = np.flatnonzero(mask & np.r_[True, ~mask[:-1]])
        ends = np.flatnonzero(mask & np.r_[~mask[1:], True]) + 1
        for start, end in zip(starts, ends, strict=False):
            if end - start < 2:
                continue
            segment = arr[y, start:end]
            key = 0.2126 * segment[:, 0] + 0.7152 * segment[:, 1] + 0.0722 * segment[:, 2]
            order = np.argsort(key)
            if reverse:
                order = order[::-1]
            arr[y, start:end] = segment[order]
    if direction == "Vertical":
        arr = np.transpose(arr, (1, 0, 2))
    return Image.fromarray(arr, "RGB")


def _screen_melt(image: Image.Image, amount: int, column_width: int, seed: int) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    rng = np.random.default_rng(seed)
    width = max(1, int(column_width))
    max_drop = max(0, int(amount))
    if max_drop == 0:
        return image
    for x in range(0, arr.shape[1], width):
        drop = int(rng.integers(0, max_drop + 1))
        if drop:
            out[:, x:x + width] = np.roll(arr[:, x:x + width], drop, axis=0)
    return Image.fromarray(out, "RGB")


def _block_shuffle(image: Image.Image, block: int, amount: float, seed: int) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    b = max(2, int(block))
    coords = [(y, x) for y in range(0, arr.shape[0], b) for x in range(0, arr.shape[1], b)]
    if len(coords) < 2:
        return image
    rng = np.random.default_rng(seed)
    count = max(0, min(len(coords), round(len(coords) * max(0.0, min(1.0, amount)))))
    selected = list(rng.choice(len(coords), size=count, replace=False)) if count else []
    shuffled = selected.copy()
    rng.shuffle(shuffled)
    for dst_i, src_i in zip(selected, shuffled, strict=False):
        dy, dx = coords[dst_i]
        sy, sx = coords[src_i]
        h = min(b, arr.shape[0] - dy, arr.shape[0] - sy)
        w = min(b, arr.shape[1] - dx, arr.shape[1] - sx)
        out[dy:dy + h, dx:dx + w] = arr[sy:sy + h, sx:sx + w]
    return Image.fromarray(out, "RGB")


def _pixel_scatter(image: Image.Image, distance: int, density: float, seed: int) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    rng = np.random.default_rng(seed)
    h, w = arr.shape[:2]
    mask = rng.random((h, w)) < max(0.0, min(1.0, density))
    ys, xs = np.nonzero(mask)
    d = max(0, int(distance))
    if d == 0 or not len(xs):
        return image
    dx = rng.integers(-d, d + 1, size=len(xs))
    dy = rng.integers(-d, d + 1, size=len(xs))
    tx = np.clip(xs + dx, 0, w - 1)
    ty = np.clip(ys + dy, 0, h - 1)
    out[ty, tx] = arr[ys, xs]
    return Image.fromarray(out, "RGB")


def _data_shift(image: Image.Image, amount: int, band_height: int, seed: int) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    rng = np.random.default_rng(seed)
    band = max(1, int(band_height))
    amount = max(0, int(amount))
    for y in range(0, arr.shape[0], band):
        shift = int(rng.integers(-amount, amount + 1)) if amount else 0
        arr[y:y + band] = np.roll(arr[y:y + band], shift, axis=1)
    return Image.fromarray(arr, "RGB")


def _periodic_shift(image: Image.Image, amount: int, period: int, axis: int) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    amount = max(0, int(amount))
    period = max(1, int(period))
    if axis == 0:  # rows shifted horizontally
        for y in range(arr.shape[0]):
            shift = round(np.sin(y / period * np.pi) * amount)
            arr[y] = np.roll(arr[y], shift, axis=0)
    else:  # columns shifted vertically
        for x in range(arr.shape[1]):
            shift = round(np.sin(x / period * np.pi) * amount)
            arr[:, x] = np.roll(arr[:, x], shift, axis=0)
    return Image.fromarray(arr, "RGB")


def _cellular_automata(image: Image.Image, threshold: float, steps: int, blend: float) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    lum = (0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]) / 255.0
    cells = lum >= float(threshold)
    for _ in range(max(1, int(steps))):
        neighbors = np.zeros_like(cells, dtype=np.uint8)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                neighbors += np.roll(np.roll(cells, dy, axis=0), dx, axis=1)
        cells = (neighbors == 3) | (cells & (neighbors == 2))
    bw = np.where(cells[..., None], 255.0, 0.0)
    alpha = max(0.0, min(1.0, float(blend)))
    out = arr * (1.0 - alpha) + bw * alpha
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _databend(image: Image.Image, quality: int, shift: int, seed: int) -> Image.Image:
    compressed = _jpeg_compression(image, quality)
    return _data_shift(compressed, shift, max(2, compressed.height // 24), seed)


def _channel_swap(image: Image.Image, order: str) -> Image.Image:
    order = order if order in {"RGB", "RBG", "GRB", "GBR", "BRG", "BGR"} else "RGB"
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    index = {"R": 0, "G": 1, "B": 2}
    return Image.fromarray(arr[..., [index[c] for c in order]], "RGB")


def _material_sample(arr: np.ndarray, x: int, y: int, cell: int) -> tuple[int, int, int]:
    region = arr[y:min(arr.shape[0], y + cell), x:min(arr.shape[1], x + cell)]
    mean = np.mean(region.reshape(-1, 3), axis=0) if region.size else np.array([0, 0, 0])
    return tuple(int(v) for v in mean)


def _pixel_material(image: Image.Image, style: str, cell_size: int, gap: int, background: str, sprite_path: str) -> Image.Image:
    cell = max(2, int(cell_size))
    gap = max(0, min(cell // 2, int(gap)))
    bg = hex_to_rgb(background)
    source = np.asarray(image.convert("RGB"), dtype=np.uint8)
    canvas = Image.new("RGB", image.size, bg)
    draw = ImageDraw.Draw(canvas)
    sprite_mask: Image.Image | None = None
    if style == "Custom Sprite" and sprite_path:
        try:
            with Image.open(Path(sprite_path).expanduser()) as sprite:
                sprite_mask = sprite.convert("RGBA")
        except Exception:
            sprite_mask = None
    try:
        ascii_font = ImageFont.load_default(size=max(6, cell - gap * 2))
    except TypeError:  # Pillow fallback on older installations
        ascii_font = ImageFont.load_default()
    chars = " .:-=+*#%@"

    for y in range(0, image.height, cell):
        for x in range(0, image.width, cell):
            color = _material_sample(source, x, y, cell)
            x0, y0 = x + gap, y + gap
            x1, y1 = min(image.width - 1, x + cell - gap - 1), min(image.height - 1, y + cell - gap - 1)
            if x1 < x0 or y1 < y0:
                continue
            if style == "Flat":
                draw.rectangle((x0, y0, x1, y1), fill=color)
            elif style in {"Round Dots", "LED"}:
                draw.ellipse((x0, y0, x1, y1), fill=color)
                if style == "LED":
                    hi = tuple(min(255, c + 60) for c in color)
                    r = max(1, (x1 - x0) // 5)
                    draw.ellipse((x0 + r, y0 + r, x0 + r * 2, y0 + r * 2), fill=hi)
            elif style == "LCD":
                dark = tuple(max(0, int(c * 0.72)) for c in color)
                draw.rounded_rectangle((x0, y0, x1, y1), radius=max(1, cell // 8), fill=color, outline=dark)
            elif style == "Fuse Bead":
                draw.ellipse((x0, y0, x1, y1), fill=color)
                hole = max(1, cell // 6)
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                draw.ellipse((cx - hole, cy - hole, cx + hole, cy + hole), fill=bg)
            elif style == "Cross Stitch":
                width = max(1, cell // 6)
                draw.line((x0, y0, x1, y1), fill=color, width=width)
                draw.line((x1, y0, x0, y1), fill=color, width=width)
            elif style == "Brick":
                dark = tuple(max(0, int(c * 0.65)) for c in color)
                light = tuple(min(255, c + 35) for c in color)
                draw.rounded_rectangle((x0, y0, x1, y1), radius=max(1, cell // 8), fill=color, outline=dark)
                draw.line((x0 + 1, y0 + 1, x1 - 1, y0 + 1), fill=light, width=1)
            elif style == "Mosaic":
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                draw.polygon([(cx, y0), (x1, cy), (cx, y1), (x0, cy)], fill=color)
            elif style == "Halftone Dot":
                lum = (0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]) / 255.0
                radius = max(1, round((1.0 - lum * 0.55) * (x1 - x0 + 1) / 2))
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)
            elif style == "CRT Phosphor":
                width = max(1, (x1 - x0 + 1) // 3)
                channels = [(color[0], 0, 0), (0, color[1], 0), (0, 0, color[2])]
                for i, c in enumerate(channels):
                    sx0 = x0 + i * width
                    if sx0 > x1:
                        continue
                    sx1 = x1 if i == 2 else min(x1, sx0 + width - 1)
                    if sx1 >= sx0:
                        draw.rectangle((sx0, y0, sx1, y1), fill=c)
            elif style == "ASCII Tile":
                lum = (0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]) / 255.0
                char = chars[min(len(chars) - 1, round(lum * (len(chars) - 1)))]
                draw.text((x0, y0), char, font=ascii_font, fill=color)
            elif style == "Custom Sprite" and sprite_mask is not None:
                tile = sprite_mask.resize((max(1, x1 - x0 + 1), max(1, y1 - y0 + 1)), Image.Resampling.NEAREST)
                alpha = tile.getchannel("A")
                tint = Image.new("RGB", tile.size, color)
                canvas.paste(tint, (x0, y0), alpha)
            else:
                draw.rectangle((x0, y0, x1, y1), fill=color)
    return canvas


def _text_overlay(image: Image.Image, text: str, x: float, y: float, size: int, color: str, outline: int, shadow: int) -> Image.Image:
    img = image.convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    size = max(6, int(size))
    try:
        font = ImageFont.load_default(size=size)
    except TypeError:
        font = ImageFont.load_default()
    fill = hex_to_rgb(color)
    px = round(img.width * max(0.0, min(100.0, x)) / 100.0)
    py = round(img.height * max(0.0, min(100.0, y)) / 100.0)
    bbox = draw.multiline_textbbox((0, 0), str(text), font=font, align="center", stroke_width=max(0, int(outline)))
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = (px - tw // 2, py - th // 2)
    if shadow > 0:
        draw.multiline_text((pos[0] + shadow, pos[1] + shadow), str(text), font=font, fill=(0, 0, 0), align="center", stroke_width=max(0, int(outline)), stroke_fill=(0, 0, 0))
    draw.multiline_text(pos, str(text), font=font, fill=fill, align="center", stroke_width=max(0, int(outline)), stroke_fill=(0, 0, 0))
    return img


def effect_stack_output_size(size: tuple[int, int], stack: list[dict[str, Any]]) -> tuple[int, int]:
    """Return image dimensions after size-changing processing layers."""
    width, height = max(1, int(size[0])), max(1, int(size[1]))
    for step in normalize_effect_stack(stack):
        if not step.get("enabled", True) or step.get("kind") != "Pixel Aspect Ratio":
            continue
        params = step.get("params", {})
        x = max(0.25, min(4.0, float(params.get("x", 1.0))))
        y = max(0.25, min(4.0, float(params.get("y", 1.0))))
        width = max(1, round(width * x / y))
    return width, height


def apply_effect_stack(
    image: Image.Image,
    stack: list[dict[str, Any]],
    palette: list[str],
    *,
    frame_time: float = 0.0,
    frame_index: int = 0,
) -> Image.Image:
    img = image if image.mode == "RGB" else image.convert("RGB")
    palette_np = palette_array(palette)

    for step in normalize_effect_stack(stack):
        if not step.get("enabled", True):
            continue
        kind = step["kind"]
        p = step["params"]

        if kind == "Adjustments":
            brightness = int(p.get("brightness", 0)); contrast = int(p.get("contrast", 0)); saturation = int(p.get("saturation", 0)); gamma = float(p.get("gamma", 1.0))
            if brightness: img = ImageEnhance.Brightness(img).enhance(max(0.0, 1.0 + brightness / 100.0))
            if contrast: img = ImageEnhance.Contrast(img).enhance(max(0.0, 1.0 + contrast / 100.0))
            if saturation: img = ImageEnhance.Color(img).enhance(max(0.0, 1.0 + saturation / 100.0))
            if abs(gamma - 1.0) > 1e-6:
                inv_gamma = 1.0 / max(0.1, gamma)
                img = img.point([round(255 * ((i / 255) ** inv_gamma)) for i in range(256)] * 3)
        elif kind == "Local Contrast": img = _local_contrast(img, int(p["amount"]), float(p["radius"]), int(p["threshold"]))
        elif kind == "Hue Rotate": img = _hue_rotate(img, int(p["degrees"]))
        elif kind == "Grayscale": img = ImageOps.grayscale(img).convert("RGB")
        elif kind == "Invert": img = ImageOps.invert(img.convert("RGB"))
        elif kind == "Gaussian Blur":
            radius = float(p["radius"])
            if radius > 0: img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        elif kind == "Median Denoise": img = img.filter(ImageFilter.MedianFilter(size=max(1, int(p["radius"])) * 2 + 1))
        elif kind == "Sharpen": img = ImageEnhance.Sharpness(img).enhance(float(p["amount"]))
        elif kind == "Glow": img = _glow(img, float(p["radius"]), float(p["intensity"]))
        elif kind == "Bloom": img = _bloom(img, float(p["threshold"]), float(p["soft_knee"]), float(p["radius"]), float(p["intensity"]), str(p["blend"]))
        elif kind == "JPEG Compression": img = _jpeg_compression(img, int(p["quality"]))
        elif kind == "Chromatic Shift": img = _chromatic_shift(img, int(p["amount"]))
        elif kind == "RGB Split": img = _rgb_split(img, int(p["x"]), int(p["y"]))
        elif kind == "Posterize": img = _posterize(img, int(p["levels"]))
        elif kind == "Scanlines": img = _scanlines(img, int(p["spacing"]), float(p["strength"]))
        elif kind == "Interlace": img = _interlace(img, int(p["offset"]), float(p["darken"]))
        elif kind == "Noise": img = _noise(img, float(p["amount"]), _seed(p, frame_index))
        elif kind == "Temporal Flicker": img = _flicker(img, float(p["amount"]), float(p["speed"]), frame_time)
        elif kind == "Temporal Pattern": img = _temporal_pattern(img, str(p["pattern"]), float(p["amount"]), float(p["speed"]), float(p["scale"]), float(p["phase"]), frame_time, int(p["seed"]))
        elif kind == "Pixel Aspect Ratio": img = _pixel_aspect_ratio(img, float(p["x"]), float(p["y"]), str(p["resample"]))
        elif kind == "Pixelate": img = _pixelate(img, int(round(float(p["size"]))))
        elif kind == "Pixel Sort": img = _pixel_sort(img, float(p["threshold"]), str(p["direction"]), bool(p["reverse"]))
        elif kind == "Screen Melt": img = _screen_melt(img, int(p["amount"]), int(p["column_width"]), _seed(p, frame_index))
        elif kind == "Block Shuffle": img = _block_shuffle(img, int(p["block"]), float(p["amount"]), _seed(p, frame_index))
        elif kind == "Pixel Scatter": img = _pixel_scatter(img, int(p["distance"]), float(p["density"]), _seed(p, frame_index))
        elif kind == "Data Shift": img = _data_shift(img, int(p["amount"]), int(p["band_height"]), _seed(p, frame_index))
        elif kind == "Row Shift": img = _periodic_shift(img, int(p["amount"]), int(p["period"]), 0)
        elif kind == "Column Shift": img = _periodic_shift(img, int(p["amount"]), int(p["period"]), 1)
        elif kind == "Cellular Automata": img = _cellular_automata(img, float(p["threshold"]), int(p["steps"]), float(p["blend"]))
        elif kind == "Databend": img = _databend(img, int(p["quality"]), int(p["shift"]), _seed(p, frame_index))
        elif kind == "Channel Swap": img = _channel_swap(img, str(p["order"]))
        elif kind == "Pixel Material": img = _pixel_material(img, str(p["style"]), int(p["cell_size"]), int(p["gap"]), str(p["background"]), str(p["sprite_path"]))
        elif kind == "Text Overlay": img = _text_overlay(img, str(p["text"]), float(p["x"]), float(p["y"]), int(p["size"]), str(p["color"]), int(p["outline"]), int(p["shadow"]))
        elif kind == "Dither":
            mix = max(0.0, min(1.0, float(p.get("mix", 1.0))))
            if mix <= 0.0:
                continue
            before = img.convert("RGB")
            arr = np.asarray(before, dtype=np.float32)
            result = apply_dither(
                arr, palette_np, str(p["algorithm"]), strength=float(p["strength"]),
                serpentine=bool(p["serpentine"]), threshold=float(p["threshold"]),
            )
            dithered = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), "RGB")
            img = dithered if mix >= 1.0 else Image.blend(before, dithered, mix)
    return img
