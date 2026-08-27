# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import math
from typing import Any

from .effect_schema import EFFECT_DEFINITIONS, normalize_effect_stack
from .settings import ProcessingSettings

EASINGS = ("Linear", "Ease In", "Ease Out", "Ease In Out", "Smoothstep", "Bezier")
MODULATORS = ("None", "Sine", "Triangle", "Saw", "Noise", "Random", "Pulse", "BPM", "Audio amplitude")
_DEFAULT_BEZIER = [0.25, 0.1, 0.25, 1.0]


def _cubic(a: float, b: float, c: float, d: float, t: float) -> float:
    mt = 1.0 - t
    return mt * mt * mt * a + 3.0 * mt * mt * t * b + 3.0 * mt * t * t * c + t * t * t * d


def _bezier_value(x: float, control: list[float] | tuple[float, ...] | None) -> float:
    try:
        x1, y1, x2, y2 = [float(v) for v in (control or _DEFAULT_BEZIER)[:4]]
    except (TypeError, ValueError):
        x1, y1, x2, y2 = _DEFAULT_BEZIER
    x1, x2 = max(0.0, min(1.0, x1)), max(0.0, min(1.0, x2))
    x = max(0.0, min(1.0, float(x)))
    lo, hi = 0.0, 1.0
    t = x
    for _ in range(16):
        current = _cubic(0.0, x1, x2, 1.0, t)
        if abs(current - x) < 1e-5:
            break
        if current < x:
            lo = t
        else:
            hi = t
        t = (lo + hi) * 0.5
    return max(0.0, min(1.0, _cubic(0.0, y1, y2, 1.0, t)))


def ease_value(t: float, easing: str, bezier: list[float] | None = None) -> float:
    t = max(0.0, min(1.0, float(t)))
    if easing == "Ease In":
        return t * t
    if easing == "Ease Out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if easing == "Ease In Out":
        return 2 * t * t if t < 0.5 else 1.0 - ((-2 * t + 2) ** 2) / 2
    if easing == "Smoothstep":
        return t * t * (3.0 - 2.0 * t)
    if easing == "Bezier":
        return _bezier_value(t, bezier)
    return t


def _normalize_keyframe(raw: object, *, fallback_time: float = 0.0, fallback_value: float = 0.0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    try:
        time = max(0.0, float(raw.get("time", fallback_time)))
        value = float(raw.get("value", fallback_value))
    except (TypeError, ValueError):
        return None
    easing = str(raw.get("easing", "Linear"))
    if easing not in EASINGS:
        easing = "Linear"
    control = raw.get("bezier", _DEFAULT_BEZIER)
    if not isinstance(control, (list, tuple)) or len(control) < 4:
        control = _DEFAULT_BEZIER
    bezier = []
    for default, component in zip(_DEFAULT_BEZIER, control[:4], strict=False):
        try:
            bezier.append(float(component))
        except (TypeError, ValueError):
            bezier.append(default)
    return {"time": time, "value": value, "easing": easing, "bezier": bezier}


def _normalize_modulator(raw: object) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    kind = str(raw.get("type", "None"))
    if kind not in MODULATORS:
        kind = "None"
    def number(key: str, default: float) -> float:
        try:
            return float(raw.get(key, default))
        except (TypeError, ValueError):
            return default
    try:
        seed = int(raw.get("seed", 1))
    except (TypeError, ValueError):
        seed = 1
    return {
        "type": kind,
        "amount": number("amount", 0.0),
        "frequency": max(0.0, number("frequency", 1.0)),
        "phase": number("phase", 0.0),
        "bpm": max(1.0, number("bpm", 120.0)),
        "seed": seed,
    }


def normalize_tracks(tracks: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Normalize legacy From→To segments and Motion Studio keyframe tracks.

    Legacy projects remain byte-semantically compatible: a classic track is
    represented as two keyframes while convenience fields are kept in the
    normalized result so old QML/presets continue to work.
    """
    out: list[dict[str, Any]] = []
    for raw in tracks or []:
        if not isinstance(raw, dict):
            continue
        target = str(raw.get("target", ""))
        if not target.startswith("effect:"):
            continue

        keyframes: list[dict[str, Any]] = []
        if isinstance(raw.get("keyframes"), list):
            for item in raw["keyframes"]:
                normalized = _normalize_keyframe(item)
                if normalized is not None:
                    keyframes.append(normalized)
        if not keyframes:
            try:
                start_value = float(raw.get("from", 0.0))
                end_value = float(raw.get("to", start_value))
                start_time = max(0.0, float(raw.get("start", 0.0)))
                end_time = max(start_time, float(raw.get("end", 1.0)))
            except (TypeError, ValueError):
                continue
            easing = str(raw.get("easing", "Linear"))
            if easing not in EASINGS:
                easing = "Linear"
            keyframes = [
                {"time": start_time, "value": start_value, "easing": easing, "bezier": list(_DEFAULT_BEZIER)},
                {"time": end_time, "value": end_value, "easing": "Linear", "bezier": list(_DEFAULT_BEZIER)},
            ]

        # Same-time keys use the last authored value.
        by_time: dict[float, dict[str, Any]] = {}
        for key in keyframes:
            by_time[float(key["time"])] = key
        keyframes = [by_time[t] for t in sorted(by_time)]
        if not keyframes:
            continue
        if len(keyframes) == 1:
            duplicate = dict(keyframes[0])
            duplicate["time"] = float(keyframes[0]["time"]) + 1e-6
            keyframes.append(duplicate)

        first, last = keyframes[0], keyframes[-1]
        out.append({
            "target": target,
            "from": float(first["value"]),
            "to": float(last["value"]),
            "start": float(first["time"]),
            "end": float(last["time"]),
            "easing": str(first["easing"]),
            "enabled": bool(raw.get("enabled", True)),
            "keyframes": keyframes,
            "modulator": _normalize_modulator(raw.get("modulator")),
        })
    return out


def _keyframe_value(track: dict[str, Any], time_seconds: float) -> float:
    keys = list(track.get("keyframes") or [])
    if not keys:
        return float(track.get("from", 0.0))
    t = max(0.0, float(time_seconds))
    if t <= float(keys[0]["time"]):
        return float(keys[0]["value"])
    if t >= float(keys[-1]["time"]):
        return float(keys[-1]["value"])
    left = keys[0]
    right = keys[-1]
    for index in range(len(keys) - 1):
        if float(keys[index]["time"]) <= t <= float(keys[index + 1]["time"]):
            left, right = keys[index], keys[index + 1]
            break
    span = max(1e-12, float(right["time"]) - float(left["time"]))
    progress = (t - float(left["time"])) / span
    progress = ease_value(progress, str(left.get("easing", "Linear")), list(left.get("bezier") or _DEFAULT_BEZIER))
    return float(left["value"]) + (float(right["value"]) - float(left["value"])) * progress


def _hash_noise(value: float, seed: int) -> float:
    return math.sin(value * 12.9898 + seed * 78.233) * 43758.5453 % 1.0


def _modulator_value(mod: dict[str, Any], t: float, settings: ProcessingSettings) -> float:
    kind = str(mod.get("type", "None"))
    amount = float(mod.get("amount", 0.0))
    if kind == "None" or abs(amount) <= 1e-12:
        return 0.0
    frequency = max(0.0, float(mod.get("frequency", 1.0)))
    phase = float(mod.get("phase", 0.0))
    seed = int(mod.get("seed", 1))
    cycle = t * frequency + phase
    frac = cycle - math.floor(cycle)
    if kind == "Sine":
        signal = math.sin(2.0 * math.pi * cycle)
    elif kind == "Triangle":
        signal = 1.0 - 4.0 * abs(frac - 0.5)
    elif kind == "Saw":
        signal = 2.0 * frac - 1.0
    elif kind == "Pulse":
        signal = 1.0 if frac < 0.5 else -1.0
    elif kind == "Noise":
        left = math.floor(cycle)
        blend = frac * frac * (3.0 - 2.0 * frac)
        a = _hash_noise(left, seed) * 2.0 - 1.0
        b = _hash_noise(left + 1.0, seed) * 2.0 - 1.0
        signal = a + (b - a) * blend
    elif kind == "Random":
        signal = _hash_noise(math.floor(cycle), seed) * 2.0 - 1.0
    elif kind == "BPM":
        bpm = max(1.0, float(mod.get("bpm", 120.0)))
        beat = (t * bpm / 60.0 + phase) % 1.0
        signal = math.exp(-beat * 8.0) * 2.0 - 1.0
    elif kind == "Audio amplitude":
        envelope = list(getattr(settings, "audio_envelope", []) or [])
        rate = max(1e-6, float(getattr(settings, "audio_envelope_rate", 30.0) or 30.0))
        if not envelope:
            signal = 0.0
        else:
            position = max(0.0, t * rate)
            i0 = min(len(envelope) - 1, int(math.floor(position)))
            i1 = min(len(envelope) - 1, i0 + 1)
            mix = position - i0
            signal = (float(envelope[i0]) * (1.0 - mix) + float(envelope[i1]) * mix) * 2.0 - 1.0
    else:
        signal = 0.0
    return signal * amount


def _value_for_target(tracks: list[dict[str, Any]], time_seconds: float, settings: ProcessingSettings) -> float:
    """Evaluate one or more clips targeting a parameter, preserving legacy sequencing."""
    ordered = sorted(tracks, key=lambda item: (float(item["start"]), float(item["end"])))
    if not ordered:
        return 0.0
    if time_seconds < float(ordered[0]["start"]):
        chosen = ordered[0]
    else:
        chosen = ordered[0]
        for candidate in ordered:
            if float(candidate["start"]) <= time_seconds:
                chosen = candidate
            else:
                break
    value = _keyframe_value(chosen, time_seconds)
    value += _modulator_value(dict(chosen.get("modulator") or {}), time_seconds, settings)
    return value


def settings_at_time(settings: ProcessingSettings, time_seconds: float) -> ProcessingSettings:
    clone = settings.clone()
    clone.effect_stack = normalize_effect_stack(clone.effect_stack, clone)
    tracks = normalize_tracks(clone.animation_tracks)
    time_seconds = max(0.0, float(time_seconds))

    by_id = {step["id"]: step for step in clone.effect_stack}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for track in tracks:
        if track["enabled"]:
            grouped.setdefault(str(track["target"]), []).append(track)

    for target, target_tracks in grouped.items():
        parts = target.split(":", 2)
        if len(parts) != 3:
            continue
        _, effect_id, param = parts
        step = by_id.get(effect_id)
        if step is None:
            continue
        value = _value_for_target(target_tracks, time_seconds, clone)

        if param == "__opacity__":
            step["opacity"] = max(0.0, min(1.0, float(value)))
            continue
        if param not in step.get("params", {}):
            continue

        definition = EFFECT_DEFINITIONS.get(str(step.get("kind", "")), {})
        spec = definition.get("params", {}).get(param, {})
        if spec.get("type") in {"int", "float", "duration"}:
            if "min" in spec:
                value = max(float(spec["min"]), value)
            if "max" in spec:
                value = min(float(spec["max"]), value)

        original = step["params"][param]
        if isinstance(original, int) and not isinstance(original, bool):
            value = int(round(value))
        step["params"][param] = value
    return clone
