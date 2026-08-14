# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

DEFAULT_PALETTE = ["#0B1020", "#F3F7FF"]


@dataclass(slots=True)
class ProcessingSettings:
    # Legacy scalar fields are intentionally retained for old presets and the
    # CLI. New GUI projects use effect_stack as the authoritative pipeline.
    algorithm: str = "Floyd-Steinberg"
    brightness: int = 0
    contrast: int = 0
    saturation: int = 0
    gamma: float = 1.0
    grayscale: bool = False
    invert: bool = False
    blur_radius: float = 0.0
    sharpen: float = 1.0
    dither_strength: float = 1.0
    pixel_size: int = 1
    serpentine: bool = True
    output_divisor: int = 1
    palette: list[str] = field(default_factory=lambda: DEFAULT_PALETTE.copy())
    palette_locks: list[bool] = field(default_factory=list)
    palette_name: str = "Custom"
    palette_author: str = ""
    palette_source: str = ""
    effect_stack: list[dict[str, Any]] = field(default_factory=list)
    animation_duration: float = 4.0
    animation_fps: int = 12
    animation_tracks: list[dict[str, Any]] = field(default_factory=list)


    def __post_init__(self) -> None:
        # Keep direct construction and JSON loading canonical. In particular,
        # palette lock state always has one entry per swatch so preset
        # round-trips do not depend on which constructor path was used.
        if not isinstance(self.palette, list) or not self.palette:
            self.palette = DEFAULT_PALETTE.copy()
        self.palette = [str(c) for c in self.palette[:256]]
        if not isinstance(self.palette_locks, list):
            self.palette_locks = []
        self.palette_locks = [bool(x) for x in self.palette_locks[: len(self.palette)]]
        if len(self.palette_locks) < len(self.palette):
            self.palette_locks.extend([False] * (len(self.palette) - len(self.palette_locks)))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProcessingSettings":
        allowed = {
            "algorithm", "brightness", "contrast", "saturation", "gamma",
            "grayscale", "invert", "blur_radius", "sharpen",
            "dither_strength", "pixel_size", "serpentine", "output_divisor",
            "palette", "palette_locks", "palette_name", "palette_author",
            "palette_source", "effect_stack", "animation_duration",
            "animation_fps", "animation_tracks",
        }
        clean = {k: v for k, v in data.items() if k in allowed}
        obj = cls(**clean)
        obj.brightness = max(-100, min(100, int(obj.brightness)))
        obj.contrast = max(-100, min(100, int(obj.contrast)))
        obj.saturation = max(-100, min(100, int(obj.saturation)))
        obj.gamma = max(0.1, min(4.0, float(obj.gamma)))
        obj.grayscale = bool(obj.grayscale)
        obj.invert = bool(obj.invert)
        obj.blur_radius = max(0.0, min(20.0, float(obj.blur_radius)))
        obj.sharpen = max(0.0, min(4.0, float(obj.sharpen)))
        obj.dither_strength = max(0.0, min(2.0, float(obj.dither_strength)))
        obj.pixel_size = max(1, min(64, int(obj.pixel_size)))
        obj.output_divisor = max(1, min(16, int(obj.output_divisor)))
        obj.serpentine = bool(obj.serpentine)
        if not isinstance(obj.palette, list) or not obj.palette:
            obj.palette = DEFAULT_PALETTE.copy()
        obj.palette = [str(c) for c in obj.palette[:256]]
        if not isinstance(obj.palette_locks, list):
            obj.palette_locks = []
        obj.palette_locks = [bool(x) for x in obj.palette_locks[: len(obj.palette)]]
        if len(obj.palette_locks) < len(obj.palette):
            obj.palette_locks.extend([False] * (len(obj.palette) - len(obj.palette_locks)))
        obj.palette_name = str(obj.palette_name or "Custom")
        obj.palette_author = str(obj.palette_author or "")
        obj.palette_source = str(obj.palette_source or "")
        if not isinstance(obj.effect_stack, list):
            obj.effect_stack = []
        if not isinstance(obj.animation_tracks, list):
            obj.animation_tracks = []
        obj.animation_duration = max(0.1, min(600.0, float(obj.animation_duration)))
        obj.animation_fps = max(1, min(120, int(obj.animation_fps)))
        return obj
