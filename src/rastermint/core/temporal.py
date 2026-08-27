# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np
from PIL import Image


_FADE_FLOOR = 0.01


@dataclass(slots=True)
class _PersistenceHistory:
    buffer: np.ndarray
    last_time: float
    last_frame_index: int
    mode: str


class TemporalEffectState:
    """State carried across sequential frames for temporal layer effects.

    The state stores one float RGB history buffer per temporal effect instance.
    It never stores a frame queue, so a 60-second persistence setting does not
    grow memory with frame count. Rewinding/restarting automatically discards
    stale history for that effect.
    """

    def __init__(self) -> None:
        self._persistence: dict[str, _PersistenceHistory] = {}

    def reset(self) -> None:
        self._persistence.clear()

    def reset_effect(self, effect_id: str) -> None:
        self._persistence.pop(str(effect_id), None)

    @staticmethod
    def _decay_fraction(delta_seconds: float, persistence_seconds: float, decay_speed: float) -> float:
        """Return the retained fraction after ``delta_seconds``.

        ``persistence_seconds`` is defined as the approximate time for a ghost
        to fall to 1% at decay speed 1.0. Decay speed scales that falloff while
        preserving frame-rate-independent behaviour.
        """
        duration = max(1e-6, float(persistence_seconds))
        speed = max(0.1, min(4.0, float(decay_speed)))
        dt = max(0.0, float(delta_seconds))
        return float(math.exp(math.log(_FADE_FLOOR) * (dt / duration) * speed))

    def apply_display_persistence(
        self,
        effect_id: str,
        image: Image.Image,
        params: dict[str, Any],
        *,
        frame_time: float,
        frame_index: int,
    ) -> Image.Image:
        """Blend the current frame with retained display history.

        Modes intentionally model different classes of display persistence:
        Generic uses symmetric exponential frame memory; CRT accumulates bright
        phosphor afterglow with green lingering longest; LCD models asymmetric
        pixel response (fast rise, slower fall); OLED models temporary bright
        image retention with a longer luminance-weighted tail.
        """
        key = str(effect_id or "display-persistence")
        mode = str(params.get("display_type", "CRT") or "CRT")
        persistence = max(0.0, float(params.get("persistence_time", 0.35) or 0.0))
        strength = max(0.0, min(1.0, float(params.get("strength", 0.45) or 0.0)))
        decay_speed = max(0.1, min(4.0, float(params.get("decay", 1.0) or 1.0)))

        current = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0

        # Zero seconds is a true bypass and clears old history so enabling the
        # effect later cannot resurrect frames from before the disabled period.
        if persistence <= 1e-9:
            self.reset_effect(key)
            return image

        history = self._persistence.get(key)
        discontinuity = (
            history is None
            or history.buffer.shape != current.shape
            or history.mode != mode
            or float(frame_time) <= history.last_time + 1e-12
            or int(frame_index) < history.last_frame_index
        )
        if discontinuity:
            self._persistence[key] = _PersistenceHistory(
                buffer=current.copy(),
                last_time=float(frame_time),
                last_frame_index=int(frame_index),
                mode=mode,
            )
            return image

        dt = max(0.0, float(frame_time) - history.last_time)
        base_decay = self._decay_fraction(dt, persistence, decay_speed)
        old = history.buffer

        if mode == "CRT":
            # Classic phosphor-style bright afterglow. The channel exponents
            # give green a longer tail while blue decays fastest.
            channel_rates = np.asarray([1.05, 0.72, 1.35], dtype=np.float32)
            channel_decay = np.power(np.float32(base_decay), channel_rates)
            retained = old * channel_decay[None, None, :]
            luminance = (
                0.2126 * current[..., 0]
                + 0.7152 * current[..., 1]
                + 0.0722 * current[..., 2]
            )
            emission = current * (0.20 + 0.80 * np.power(luminance, 1.35))[..., None]
            next_buffer = np.maximum(retained, emission)
            ghost = np.clip(retained * strength, 0.0, 1.0)
            output = 1.0 - (1.0 - current) * (1.0 - ghost)

        elif mode == "LCD":
            # LCD ghosting is response lag rather than light emission. Brighter
            # transitions settle faster than falling/dark transitions.
            delta = current - old
            rise_decay = float(base_decay) ** 1.65
            fall_decay = float(base_decay) ** 0.72
            retention = np.where(delta >= 0.0, rise_decay, fall_decay).astype(np.float32)
            response = old * retention + current * (1.0 - retention)
            next_buffer = response
            output = current * (1.0 - strength) + response * strength

        elif mode == "OLED":
            # Temporary OLED retention is subtle but can linger much longer in
            # bright regions. Use a luminance-weighted retained image rather
            # than a queue of old frames.
            retained = old * (float(base_decay) ** 0.55)
            luminance = (
                0.2126 * current[..., 0]
                + 0.7152 * current[..., 1]
                + 0.0722 * current[..., 2]
            )
            emission = current * np.power(luminance, 1.6)[..., None]
            next_buffer = np.maximum(retained, emission)
            ghost = np.clip(retained * (0.72 * strength), 0.0, 1.0)
            output = 1.0 - (1.0 - current) * (1.0 - ghost)

        else:  # Generic
            # Frame-rate-independent exponential memory of all colours, useful
            # as a neutral motion-echo mode when no display model is desired.
            response = old * base_decay + current * (1.0 - base_decay)
            next_buffer = response
            ghost = np.clip(response * strength, 0.0, 1.0)
            output = 1.0 - (1.0 - current) * (1.0 - ghost)

        self._persistence[key] = _PersistenceHistory(
            buffer=np.asarray(next_buffer, dtype=np.float32),
            last_time=float(frame_time),
            last_frame_index=int(frame_index),
            mode=mode,
        )

        arr = np.clip(np.rint(output * 255.0), 0, 255).astype(np.uint8)
        return Image.fromarray(arr, "RGB")


def max_persistence_seconds(stack: list[dict[str, Any]] | None) -> float:
    """Return the longest enabled Display Persistence horizon in a stack."""
    longest = 0.0
    for step in stack or []:
        if not isinstance(step, dict) or not step.get("enabled", True):
            continue
        if str(step.get("kind", "")) != "Display Persistence":
            continue
        params = step.get("params") if isinstance(step.get("params"), dict) else {}
        try:
            longest = max(longest, max(0.0, float(params.get("persistence_time", 0.0) or 0.0)))
        except (TypeError, ValueError):
            continue
    return longest
