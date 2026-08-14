# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from typing import Any
from uuid import uuid4

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from .dither import ALGORITHMS, apply_dither
from .palette import palette_array


# The UI consumes this schema directly. Keeping effect metadata in the core means
# adding a new effect does not require hard-coding another form in main_window.py.
EFFECT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "Adjustments": {
        "params": {
            "brightness": {"type": "int", "label": "Brightness", "default": 0, "min": -100, "max": 100, "step": 1, "animatable": True},
            "contrast": {"type": "int", "label": "Contrast", "default": 0, "min": -100, "max": 100, "step": 1, "animatable": True},
            "saturation": {"type": "int", "label": "Saturation", "default": 0, "min": -100, "max": 100, "step": 1, "animatable": True},
            "gamma": {"type": "float", "label": "Gamma", "default": 1.0, "min": 0.1, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
        }
    },
    "Hue Rotate": {
        "params": {
            "degrees": {"type": "int", "label": "Degrees", "default": 0, "min": -180, "max": 180, "step": 1, "animatable": True},
        }
    },
    "Grayscale": {"params": {}},
    "Invert": {"params": {}},
    "Gaussian Blur": {
        "params": {
            "radius": {"type": "float", "label": "Radius", "default": 2.0, "min": 0.0, "max": 30.0, "step": 0.25, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        }
    },
    "Median Denoise": {
        "params": {
            "radius": {"type": "int", "label": "Radius", "default": 1, "min": 1, "max": 5, "step": 1, "pixel_scaled": True},
        }
    },
    "Sharpen": {
        "params": {
            "amount": {"type": "float", "label": "Amount", "default": 1.5, "min": 0.0, "max": 5.0, "step": 0.1, "decimals": 2, "animatable": True},
        }
    },
    "Glow": {
        "params": {
            "radius": {"type": "float", "label": "Radius", "default": 5.0, "min": 0.0, "max": 40.0, "step": 0.5, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
            "intensity": {"type": "float", "label": "Intensity", "default": 0.35, "min": 0.0, "max": 2.0, "step": 0.05, "decimals": 2, "animatable": True},
        }
    },
    "JPEG Compression": {
        "params": {
            "quality": {"type": "int", "label": "Quality", "default": 35, "min": 5, "max": 95, "step": 1, "animatable": True},
        }
    },
    "Chromatic Shift": {
        "params": {
            "amount": {"type": "int", "label": "Offset", "default": 3, "min": -40, "max": 40, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        }
    },
    "Posterize": {
        "params": {
            "levels": {"type": "int", "label": "Levels", "default": 6, "min": 2, "max": 64, "step": 1, "animatable": True},
        }
    },
    "Scanlines": {
        "params": {
            "spacing": {"type": "int", "label": "Spacing", "default": 3, "min": 2, "max": 16, "step": 1, "pixel_scaled": True},
            "strength": {"type": "float", "label": "Darken", "default": 0.25, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
        }
    },
    "Noise": {
        "params": {
            "amount": {"type": "float", "label": "Amount", "default": 12.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "animatable": True},
            "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
            "temporal": {"type": "bool", "label": "Animate seed", "default": False},
        }
    },
    "Temporal Flicker": {
        "params": {
            "amount": {"type": "float", "label": "Amount", "default": 0.08, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
            "speed": {"type": "float", "label": "Speed", "default": 4.0, "min": 0.1, "max": 30.0, "step": 0.1, "decimals": 1, "suffix": " Hz", "animatable": True},
        }
    },
    "Pixelate": {
        "params": {
            "size": {"type": "int", "label": "Pixel size", "default": 2, "min": 1, "max": 64, "step": 1, "animatable": True, "pixel_scaled": True},
        }
    },
    "Dither": {
        "params": {
            "algorithm": {"type": "choice", "label": "Algorithm", "default": "Floyd-Steinberg", "options": ALGORITHMS},
            "strength": {"type": "float", "label": "Strength", "default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05, "decimals": 2, "animatable": True},
            "threshold": {"type": "float", "label": "Threshold", "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
            "serpentine": {"type": "bool", "label": "Serpentine", "default": True},
        }
    },
}


def new_effect(kind: str, *, enabled: bool = True, effect_id: str | None = None) -> dict[str, Any]:
    if kind not in EFFECT_DEFINITIONS:
        raise ValueError(f"Unknown effect type: {kind}")
    params = {
        key: deepcopy(spec.get("default"))
        for key, spec in EFFECT_DEFINITIONS[kind]["params"].items()
    }
    return {
        "id": effect_id or uuid4().hex[:12],
        "kind": kind,
        "enabled": bool(enabled),
        "params": params,
    }


def default_effect_stack(settings: Any | None = None) -> list[dict[str, Any]]:
    """Build a useful stack, optionally preserving legacy ProcessingSettings."""
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
                    value = int(round(float(value)))
                    value = max(int(spec["min"]), min(int(spec["max"]), value))
                elif ptype == "float":
                    value = float(value)
                    value = max(float(spec["min"]), min(float(spec["max"]), value))
                elif ptype == "bool":
                    value = bool(value)
                elif ptype == "choice":
                    options = list(spec.get("options", []))
                    value = str(value)
                    if options and value not in options:
                        value = spec.get("default", options[0])
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
                label = f"{step['kind']} · {spec.get('label', key)}"
                targets.append((f"effect:{step['id']}:{key}", label, float(value)))
    return targets


def _hue_rotate(image: Image.Image, degrees: int) -> Image.Image:
    if degrees % 360 == 0:
        return image
    hsv = np.asarray(image.convert("HSV"), dtype=np.uint8).copy()
    shift = int(round((degrees % 360) / 360.0 * 255.0))
    hsv[..., 0] = (hsv[..., 0].astype(np.uint16) + shift) % 256
    return Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")


def _glow(image: Image.Image, radius: float, intensity: float) -> Image.Image:
    if radius <= 0.0 or intensity <= 0.0:
        return image
    base = np.asarray(image.convert("RGB"), dtype=np.float32)
    blurred = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=radius)), dtype=np.float32)
    glow = np.clip(blurred * intensity, 0.0, 255.0)
    out = base + glow - (base * glow / 255.0)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _jpeg_compression(image: Image.Image, quality: int) -> Image.Image:
    quality = max(5, min(95, int(quality)))
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality, subsampling=2, optimize=False)
    buffer.seek(0)
    with Image.open(buffer) as decoded:
        decoded.load()
        return decoded.convert("RGB")


def _chromatic_shift(image: Image.Image, amount: int) -> Image.Image:
    amount = int(amount)
    if amount == 0:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out = arr.copy()
    out[..., 0] = np.roll(arr[..., 0], amount, axis=1)
    out[..., 2] = np.roll(arr[..., 2], -amount, axis=1)
    return Image.fromarray(out, "RGB")


def _posterize(image: Image.Image, levels: int) -> Image.Image:
    levels = max(2, min(64, int(levels)))
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    step = 255.0 / (levels - 1)
    out = np.rint(arr / step) * step
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _scanlines(image: Image.Image, spacing: int, strength: float) -> Image.Image:
    spacing = max(2, int(spacing))
    strength = max(0.0, min(1.0, float(strength)))
    if strength <= 0:
        return image
    arr = np.asarray(image.convert("RGB"), dtype=np.float32).copy()
    arr[::spacing] *= 1.0 - strength
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
    factor = max(0.0, 1.0 + amount * phase)
    return ImageEnhance.Brightness(image).enhance(factor)


def _pixelate(image: Image.Image, size: int) -> Image.Image:
    size = max(1, int(size))
    if size <= 1:
        return image
    w, h = image.size
    small = image.resize((max(1, w // size), max(1, h // size)), Image.Resampling.BOX)
    return small.resize((w, h), Image.Resampling.NEAREST)


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
            brightness = int(p.get("brightness", 0))
            contrast = int(p.get("contrast", 0))
            saturation = int(p.get("saturation", 0))
            gamma = float(p.get("gamma", 1.0))
            if brightness:
                img = ImageEnhance.Brightness(img).enhance(max(0.0, 1.0 + brightness / 100.0))
            if contrast:
                img = ImageEnhance.Contrast(img).enhance(max(0.0, 1.0 + contrast / 100.0))
            if saturation:
                img = ImageEnhance.Color(img).enhance(max(0.0, 1.0 + saturation / 100.0))
            if abs(gamma - 1.0) > 1e-6:
                inv_gamma = 1.0 / max(0.1, gamma)
                lut = [round(255 * ((i / 255) ** inv_gamma)) for i in range(256)]
                img = img.point(lut * 3)
        elif kind == "Hue Rotate":
            img = _hue_rotate(img, int(p.get("degrees", 0)))
        elif kind == "Grayscale":
            img = ImageOps.grayscale(img).convert("RGB")
        elif kind == "Invert":
            img = ImageOps.invert(img.convert("RGB"))
        elif kind == "Gaussian Blur":
            radius = float(p.get("radius", 0.0))
            if radius > 0:
                img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        elif kind == "Median Denoise":
            radius = max(1, int(p.get("radius", 1)))
            img = img.filter(ImageFilter.MedianFilter(size=radius * 2 + 1))
        elif kind == "Sharpen":
            img = ImageEnhance.Sharpness(img).enhance(float(p.get("amount", 1.0)))
        elif kind == "Glow":
            img = _glow(img, float(p.get("radius", 5.0)), float(p.get("intensity", 0.35)))
        elif kind == "JPEG Compression":
            img = _jpeg_compression(img, int(p.get("quality", 35)))
        elif kind == "Chromatic Shift":
            img = _chromatic_shift(img, int(p.get("amount", 0)))
        elif kind == "Posterize":
            img = _posterize(img, int(p.get("levels", 6)))
        elif kind == "Scanlines":
            img = _scanlines(img, int(p.get("spacing", 3)), float(p.get("strength", 0.25)))
        elif kind == "Noise":
            seed = int(p.get("seed", 1))
            if bool(p.get("temporal", False)):
                seed += int(frame_index) * 1009
            img = _noise(img, float(p.get("amount", 12.0)), seed)
        elif kind == "Temporal Flicker":
            img = _flicker(img, float(p.get("amount", 0.08)), float(p.get("speed", 4.0)), frame_time)
        elif kind == "Pixelate":
            img = _pixelate(img, int(round(float(p.get("size", 1)))))
        elif kind == "Dither":
            arr = np.asarray(img.convert("RGB"), dtype=np.float32)
            result = apply_dither(
                arr,
                palette_np,
                str(p.get("algorithm", "Floyd-Steinberg")),
                strength=float(p.get("strength", 1.0)),
                serpentine=bool(p.get("serpentine", True)),
                threshold=float(p.get("threshold", 0.5)),
            )
            img = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), "RGB")

    return img
