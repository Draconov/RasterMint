# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy
import colorsys
import random
from typing import Any

from .effect_schema import EFFECT_DEFINITIONS


_SKIP_PARAM_TOKENS = (
    "seed", "json", "profile", "preview", "path", "font", "count",
    "bits", "group", "sprite", "text", "character", "custom_matrix",
)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _mutate_hex(color: str, rng: random.Random, amount: float) -> str:
    text = str(color or "#000000").strip().lstrip("#")
    if len(text) != 6:
        return str(color)
    try:
        r, g, b = (int(text[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return str(color)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h = (h + rng.uniform(-0.075, 0.075) * amount) % 1.0
    s = _clamp(s + rng.uniform(-0.18, 0.18) * amount, 0.0, 1.0)
    v = _clamp(v + rng.uniform(-0.16, 0.16) * amount, 0.0, 1.0)
    rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
    return f"#{round(rr * 255):02X}{round(gg * 255):02X}{round(bb * 255):02X}"


def _mutate_number(value: Any, spec: dict[str, Any], rng: random.Random, amount: float) -> Any:
    typ = str(spec.get("type", "float"))
    try:
        current = float(value)
        lo = float(spec.get("min", current))
        hi = float(spec.get("max", current))
    except (TypeError, ValueError):
        return value
    if hi <= lo:
        return value

    # At the default amount (0.35), values move roughly ±8% of their legal
    # range. That is enough to create visible relatives without turning a
    # carefully-built preset into Creative Randomize.
    radius = (hi - lo) * (0.02 + 0.18 * amount)
    candidate = _clamp(current + rng.uniform(-radius, radius), lo, hi)
    step = float(spec.get("step", 0) or 0)
    if step > 0:
        candidate = lo + round((candidate - lo) / step) * step
        candidate = _clamp(candidate, lo, hi)
    if typ == "int":
        return int(round(candidate))
    decimals = int(spec.get("decimals", 3))
    return round(float(candidate), max(0, min(6, decimals)))


def _safe_numeric_param(key: str, spec: dict[str, Any]) -> bool:
    lower = str(key).casefold()
    if any(token in lower for token in _SKIP_PARAM_TOKENS):
        return False
    if bool(spec.get("hidden", False)):
        return False
    return str(spec.get("type", "")) in {"int", "float", "duration"}


def generate_preset_mutations(
    settings_data: dict[str, Any],
    *,
    count: int = 8,
    amount: float = 0.35,
    seed: int = 1,
) -> list[dict[str, Any]]:
    """Return controlled preset relatives while preserving stack structure.

    Layer count/order/kinds/IDs, masks, animation tracks, raster settings and
    other structural data are left untouched. Numeric effect parameters,
    layer opacity and unlocked palette colors receive small deterministic
    perturbations. The returned settings remain ordinary RasterMint settings
    and are fully editable after a mutation is applied.
    """
    count = max(6, min(12, int(count)))
    amount = max(0.05, min(1.0, float(amount)))
    source = deepcopy(dict(settings_data or {}))
    result: list[dict[str, Any]] = []

    for variant_index in range(count):
        rng = random.Random((int(seed) & 0x7FFFFFFF) + variant_index * 104729)
        data = deepcopy(source)
        changes: list[str] = []

        palette = list(data.get("palette") or [])
        locks = list(data.get("palette_locks") or [False] * len(palette))
        if len(locks) < len(palette):
            locks.extend([False] * (len(palette) - len(locks)))
        palette_changes = 0
        for index, color in enumerate(palette):
            if bool(locks[index]):
                continue
            # Keep most colors anchored on lower mutation amounts so the
            # family identity survives. Higher amounts progressively touch more.
            if rng.random() <= 0.30 + 0.55 * amount:
                mutated = _mutate_hex(str(color), rng, amount)
                if mutated != color:
                    palette[index] = mutated
                    palette_changes += 1
        if palette_changes:
            data["palette"] = palette
            data["palette_name"] = f"{data.get('palette_name') or 'Palette'} variation"
            changes.append(f"palette {palette_changes}")

        stack = data.get("effect_stack")
        if isinstance(stack, list):
            for step_index, step in enumerate(stack):
                if not isinstance(step, dict):
                    continue
                kind = str(step.get("kind", ""))
                definition = EFFECT_DEFINITIONS.get(kind, {})
                params = step.get("params")
                if not isinstance(params, dict):
                    continue

                local_changes = 0
                for key, spec in dict(definition.get("params", {})).items():
                    if key not in params or not _safe_numeric_param(str(key), dict(spec)):
                        continue
                    # Mutate a subset per layer. Different variants therefore
                    # explore different nearby directions instead of changing
                    # every slider at once.
                    if rng.random() > 0.42 + 0.36 * amount:
                        continue
                    before = params[key]
                    after = _mutate_number(before, dict(spec), rng, amount)
                    if after != before:
                        params[key] = after
                        local_changes += 1

                # Layer compositing is part of the look but not its structure.
                if "opacity" in step and rng.random() < 0.22 + amount * 0.20:
                    try:
                        before_opacity = float(step.get("opacity", 1.0))
                        after_opacity = round(_clamp(before_opacity + rng.uniform(-0.12, 0.12) * amount, 0.0, 1.0), 3)
                        if after_opacity != before_opacity:
                            step["opacity"] = after_opacity
                            local_changes += 1
                    except (TypeError, ValueError):
                        pass

                if local_changes:
                    changes.append(f"{kind} {local_changes}")

        # Guarantee that every card is a real variation even for extremely
        # sparse presets where random selection happened to touch nothing.
        if not changes and isinstance(data.get("effect_stack"), list):
            for step in data["effect_stack"]:
                if not isinstance(step, dict):
                    continue
                kind = str(step.get("kind", ""))
                definition = EFFECT_DEFINITIONS.get(kind, {})
                params = step.get("params")
                if not isinstance(params, dict):
                    continue
                for key, spec in dict(definition.get("params", {})).items():
                    if key in params and _safe_numeric_param(str(key), dict(spec)):
                        before = params[key]
                        after = _mutate_number(before, dict(spec), rng, max(amount, 0.25))
                        if after == before:
                            lo = float(spec.get("min", 0)); hi = float(spec.get("max", 1)); step_size = float(spec.get("step", 0) or 0)
                            if step_size > 0 and hi > lo:
                                after = _clamp(float(before) + step_size, lo, hi)
                                if str(spec.get("type")) == "int":
                                    after = int(round(after))
                        if after != before:
                            params[key] = after
                            changes.append(f"{kind} 1")
                        break
                if changes:
                    break

        # A preset can legally contain only zero-parameter layers and a fully
        # locked palette. In that sparse case, use layer opacity as the final
        # safe visual degree of freedom so every generated card is a genuine
        # editable variation rather than an identical clone.
        if not changes and isinstance(data.get("effect_stack"), list):
            for step in data["effect_stack"]:
                if not isinstance(step, dict) or "opacity" not in step:
                    continue
                try:
                    before = float(step.get("opacity", 1.0))
                except (TypeError, ValueError):
                    continue
                delta = max(0.02, 0.10 * amount)
                after = _clamp(before - delta if before >= 0.5 else before + delta, 0.0, 1.0)
                after = round(after, 3)
                if after != before:
                    step["opacity"] = after
                    changes.append(f"{step.get('kind', 'Layer')} opacity")
                    break

        result.append({
            "settings": data,
            "summary": " · ".join(changes[:4]) if changes else "Subtle palette-relative variation",
            "variant": variant_index + 1,
        })
    return result


__all__ = ["generate_preset_mutations"]
