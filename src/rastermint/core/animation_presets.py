# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from dataclasses import dataclass

from .effect_stack import new_effect, normalize_effect_stack
from .settings import ProcessingSettings


@dataclass(frozen=True, slots=True)
class AnimationPreset:
    id: str
    name: str
    description: str


ANIMATION_PRESETS: tuple[AnimationPreset, ...] = (
    AnimationPreset("dither-in", "Dither In", "Fade clean pixels into the active dither using the Dither Mix control."),
    AnimationPreset("dither-out", "Dither Out", "Fade the active dither back to the clean pre-dither image."),
    AnimationPreset("dither-in-out", "Dither In / Out", "Dither in during the first half, then return to the clean image."),
    AnimationPreset("glow-pulse", "Glow Pulse", "Add/enable Glow and pulse its intensity."),
    AnimationPreset("hue-sweep", "Hue Sweep", "Rotate hue smoothly across a full color sweep."),
    AnimationPreset("crt-flicker", "CRT Flicker", "Add scanlines plus subtle animated flicker."),
    AnimationPreset("pixelate-in", "Pixelate In", "Animate the Pixelate cell size from 1px to a chunky pixel look."),
    AnimationPreset("chromatic-pulse", "Chromatic Pulse", "Animate RGB/chromatic separation outwards."),
    AnimationPreset("temporal-wave", "Temporal Wave", "Add a moving spatial luminance wave for living dither/pixel textures."),
)


def _ensure_effect(stack: list[dict], kind: str, *, preferred_id: str | None = None) -> dict:
    for step in stack:
        if step.get("kind") == kind:
            step["enabled"] = True
            return step
    step = new_effect(kind, effect_id=preferred_id)
    stack.append(step)
    return step


def _track(step: dict, param: str, start: float, end: float, t0: float, t1: float, easing: str = "Ease In Out") -> dict:
    return {
        "target": f"effect:{step['id']}:{param}",
        "from": float(start),
        "to": float(end),
        "start": float(t0),
        "end": float(t1),
        "easing": easing,
        "enabled": True,
    }


def apply_animation_preset(settings: ProcessingSettings, preset_id: str) -> ProcessingSettings:
    """Return a cloned project with a motion preset applied.

    Missing effects are added automatically. Existing image/palette/hardware state is
    preserved, so motion presets behave like animation recipes rather than full
    image presets.
    """
    result = ProcessingSettings.from_dict(settings.to_dict())
    stack = normalize_effect_stack(result.effect_stack, result)
    duration = max(0.1, float(result.animation_duration))
    half = duration * 0.5
    tracks: list[dict] = []

    if preset_id in {"dither-in", "dither-out", "dither-in-out"}:
        dither = _ensure_effect(stack, "Dither", preferred_id="dither")
        dither["params"]["mix"] = 1.0
        if preset_id == "dither-in":
            tracks = [_track(dither, "mix", 0.0, 1.0, 0.0, duration)]
        elif preset_id == "dither-out":
            tracks = [_track(dither, "mix", 1.0, 0.0, 0.0, duration)]
        else:
            tracks = [
                _track(dither, "mix", 0.0, 1.0, 0.0, half),
                _track(dither, "mix", 1.0, 0.0, half, duration),
            ]
    elif preset_id == "glow-pulse":
        glow = _ensure_effect(stack, "Glow")
        glow["params"].update(radius=max(5.0, float(glow["params"].get("radius", 5.0))), intensity=0.15)
        tracks = [
            _track(glow, "intensity", 0.05, 1.0, 0.0, half),
            _track(glow, "intensity", 1.0, 0.05, half, duration),
        ]
    elif preset_id == "hue-sweep":
        hue = _ensure_effect(stack, "Hue Rotate")
        tracks = [_track(hue, "degrees", -180.0, 180.0, 0.0, duration, "Linear")]
    elif preset_id == "crt-flicker":
        scan = _ensure_effect(stack, "Scanlines")
        flicker = _ensure_effect(stack, "Temporal Flicker")
        scan["params"]["strength"] = max(0.2, float(scan["params"].get("strength", 0.25)))
        flicker["params"].update(amount=0.04, speed=8.0)
        tracks = [
            _track(flicker, "amount", 0.02, 0.10, 0.0, half),
            _track(flicker, "amount", 0.10, 0.02, half, duration),
        ]
    elif preset_id == "pixelate-in":
        pix = _ensure_effect(stack, "Pixelate", preferred_id="pixelate")
        tracks = [_track(pix, "size", 1.0, 16.0, 0.0, duration)]
    elif preset_id == "chromatic-pulse":
        chroma = _ensure_effect(stack, "Chromatic Shift")
        tracks = [
            _track(chroma, "amount", 0.0, 16.0, 0.0, half),
            _track(chroma, "amount", 16.0, 0.0, half, duration),
        ]
    elif preset_id == "temporal-wave":
        temporal = _ensure_effect(stack, "Temporal Pattern")
        temporal["params"].update(pattern="Wave X", amount=0.3, speed=1.0, scale=32.0, phase=0.0)
        tracks = [_track(temporal, "phase", 0.0, 1.0, 0.0, duration, "Linear")]
    else:
        raise ValueError(f"Unknown animation preset: {preset_id}")

    result.effect_stack = stack
    result.animation_tracks = tracks
    return ProcessingSettings.from_dict(result.to_dict())
