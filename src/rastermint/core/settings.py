# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

DEFAULT_PALETTE = ["#0B1020", "#F3F7FF"]


@dataclass(slots=True)
class ProcessingSettings:
    algorithm: str = "Floyd-Steinberg"
    brightness: int = 0
    contrast: int = 0
    saturation: int = 0
    gamma: float = 1.0
    dither_strength: float = 1.0
    pixel_size: int = 1
    serpentine: bool = True
    output_divisor: int = 1
    palette: list[str] = field(default_factory=lambda: DEFAULT_PALETTE.copy())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProcessingSettings":
        allowed = {
            "algorithm",
            "brightness",
            "contrast",
            "saturation",
            "gamma",
            "dither_strength",
            "pixel_size",
            "serpentine",
            "output_divisor",
            "palette",
        }
        clean = {k: v for k, v in data.items() if k in allowed}
        obj = cls(**clean)
        obj.brightness = max(-100, min(100, int(obj.brightness)))
        obj.contrast = max(-100, min(100, int(obj.contrast)))
        obj.saturation = max(-100, min(100, int(obj.saturation)))
        obj.gamma = max(0.1, min(4.0, float(obj.gamma)))
        obj.dither_strength = max(0.0, min(2.0, float(obj.dither_strength)))
        obj.pixel_size = max(1, min(32, int(obj.pixel_size)))
        obj.output_divisor = max(1, min(16, int(obj.output_divisor)))
        obj.serpentine = bool(obj.serpentine)
        if not obj.palette:
            obj.palette = DEFAULT_PALETTE.copy()
        return obj
