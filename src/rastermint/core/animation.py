# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .effect_stack import normalize_effect_stack
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


def settings_at_time(settings: ProcessingSettings, time_seconds: float) -> ProcessingSettings:
    clone = ProcessingSettings.from_dict(settings.to_dict())
    clone.effect_stack = normalize_effect_stack(deepcopy(clone.effect_stack), clone)
    tracks = normalize_tracks(clone.animation_tracks)
    time_seconds = max(0.0, float(time_seconds))

    by_id = {step["id"]: step for step in clone.effect_stack}
    for track in tracks:
        if not track["enabled"]:
            continue
        parts = track["target"].split(":", 2)
        if len(parts) != 3:
            continue
        _, effect_id, param = parts
        step = by_id.get(effect_id)
        if step is None or param not in step.get("params", {}):
            continue
        start_t = track["start"]
        end_t = track["end"]
        if end_t <= start_t:
            progress = 1.0 if time_seconds >= end_t else 0.0
        else:
            progress = (time_seconds - start_t) / (end_t - start_t)
        progress = ease_value(progress, track["easing"])
        value = track["from"] + (track["to"] - track["from"]) * progress
        original = step["params"][param]
        if isinstance(original, int) and not isinstance(original, bool):
            value = int(round(value))
        step["params"][param] = value
    return clone
