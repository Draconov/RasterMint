# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .effect_stack import EFFECT_DEFINITIONS, normalize_effect_stack
from .settings import ProcessingSettings

EASINGS = ("Linear", "Ease In", "Ease Out", "Ease In Out", "Smoothstep")


def ease_value(t: float, easing: str) -> float:
    t = max(0.0, min(1.0, float(t)))
    if easing == "Ease In":
        return t * t
    if easing == "Ease Out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if easing == "Ease In Out":
        return 2 * t * t if t < 0.5 else 1.0 - ((-2 * t + 2) ** 2) / 2
    if easing == "Smoothstep":
        return t * t * (3.0 - 2.0 * t)
    return t


def normalize_tracks(tracks: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in tracks or []:
        if not isinstance(raw, dict):
            continue
        target = str(raw.get("target", ""))
        if not target.startswith("effect:"):
            continue
        try:
            start = float(raw.get("from", 0.0))
            end = float(raw.get("to", start))
            start_time = max(0.0, float(raw.get("start", 0.0)))
            end_time = max(start_time, float(raw.get("end", 1.0)))
        except (TypeError, ValueError):
            continue
        easing = str(raw.get("easing", "Linear"))
        if easing not in EASINGS:
            easing = "Linear"
        out.append({
            "target": target,
            "from": start,
            "to": end,
            "start": start_time,
            "end": end_time,
            "easing": easing,
            "enabled": bool(raw.get("enabled", True)),
        })
    return out


def _track_value(track: dict[str, Any], time_seconds: float) -> float:
    start_t = float(track["start"])
    end_t = float(track["end"])
    if end_t <= start_t:
        progress = 1.0 if time_seconds >= end_t else 0.0
    else:
        progress = (time_seconds - start_t) / (end_t - start_t)
    progress = ease_value(progress, str(track["easing"]))
    return float(track["from"]) + (float(track["to"]) - float(track["from"])) * progress


def _value_for_target(tracks: list[dict[str, Any]], time_seconds: float) -> float:
    """Evaluate sequential tracks for one parameter without later tracks overriding early ones.

    Before the first segment begins, its ``from`` value is used. Between segments,
    the preceding segment holds its ``to`` value. This makes presets such as
    Dither In → Dither Out possible with two tracks targeting the same parameter.
    """
    ordered = sorted(tracks, key=lambda item: (float(item["start"]), float(item["end"])))
    if not ordered:
        return 0.0
    if time_seconds < float(ordered[0]["start"]):
        return float(ordered[0]["from"])

    chosen = ordered[0]
    for candidate in ordered:
        if float(candidate["start"]) <= time_seconds:
            chosen = candidate
        else:
            break
    if time_seconds > float(chosen["end"]):
        return float(chosen["to"])
    return _track_value(chosen, time_seconds)


def settings_at_time(settings: ProcessingSettings, time_seconds: float) -> ProcessingSettings:
    clone = ProcessingSettings.from_dict(settings.to_dict())
    clone.effect_stack = normalize_effect_stack(deepcopy(clone.effect_stack), clone)
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
        if step is None or param not in step.get("params", {}):
            continue

        value = _value_for_target(target_tracks, time_seconds)
        definition = EFFECT_DEFINITIONS.get(str(step.get("kind", "")), {})
        spec = definition.get("params", {}).get(param, {})
        if spec.get("type") in {"int", "float"}:
            if "min" in spec:
                value = max(float(spec["min"]), value)
            if "max" in spec:
                value = min(float(spec["max"]), value)

        original = step["params"][param]
        if isinstance(original, int) and not isinstance(original, bool):
            value = int(round(value))
        step["params"][param] = value
    return clone
