# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import copy, deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

DEFAULT_PALETTE = ["#0B1020", "#F3F7FF"]


def _default_random_locks() -> dict[str, bool]:
    return {
        "palette": False,
        "dither": False,
        "effects": False,
        "resolution": True,
        "parameters": False,
    }


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

    # Source transform / target raster. A target of 0x0 means "use transformed
    # source size". output_divisor is still honoured for older presets/CLI.
    target_width: int = 0
    target_height: int = 0
    target_enabled: bool = False
    keep_aspect: bool = True
    fit_mode: str = "fit"  # fit / fill / stretch
    position_x: float = 0.0  # -1..1, used by fill cropping
    position_y: float = 0.0
    rotation: int = 0  # 0/90/180/270 clockwise
    flip_horizontal: bool = False
    flip_vertical: bool = False
    # Interactive mirror axes. Horizontal mirroring uses a vertical axis and
    # vertical mirroring uses a horizontal axis.
    mirror_horizontal: bool = False
    mirror_vertical: bool = False
    mirror_horizontal_axis: float = 0.5
    mirror_vertical_axis: float = 0.5
    crop_left: float = 0.0   # source-relative fractions 0..0.49
    crop_top: float = 0.0
    crop_right: float = 0.0
    crop_bottom: float = 0.0

    # Framebuffer pixel geometry and display view. pixel_aspect_x/y describe
    # pixel width:height. The framebuffer itself is never distorted; display
    # correction is a separate final view/export step.
    pixel_aspect_x: float = 1.0
    pixel_aspect_y: float = 1.0
    display_mode: str = "corrected"  # raw / corrected / display
    display_export: bool = False
    display_profile: dict[str, Any] = field(default_factory=dict)

    # Optional grid overlay. Preview/export toggles are independent.
    grid_enabled: bool = False
    grid_preview: bool = True
    grid_export: bool = False
    grid_spacing: int = 1
    grid_major_spacing: int = 8
    grid_opacity: float = 0.35

    # Hardware profile identity. Editable strict/display processing now lives
    # entirely in the visible Hardware Limits / Hardware Display layers.
    hardware_profile_id: str = "custom"
    hardware_mode: str = "visual"  # visual / strict

    palette: list[str] = field(default_factory=lambda: DEFAULT_PALETTE.copy())
    palette_locks: list[bool] = field(default_factory=list)
    palette_name: str = "Custom"
    palette_author: str = ""
    palette_source: str = ""
    effect_stack: list[dict[str, Any]] = field(default_factory=list)
    # Layer groups are organizational metadata. Effects remain a flat ordered
    # pipeline so old projects/presets retain identical processing semantics.
    layer_groups: list[dict[str, Any]] = field(default_factory=list)
    solo_layer_id: str = ""

    animation_duration: float = 4.0
    animation_fps: int = 12
    animation_loop: bool = True
    animation_tracks: list[dict[str, Any]] = field(default_factory=list)
    # Optional normalized audio envelope used by the Audio amplitude modulator.
    # It is deliberately lightweight (typically 30 samples/second) and can be
    # saved inside .rastermint projects for deterministic playback/export.
    audio_envelope: list[float] = field(default_factory=list)
    audio_envelope_rate: float = 30.0

    random_locks: dict[str, bool] = field(default_factory=_default_random_locks)

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
        if not isinstance(self.random_locks, dict):
            self.random_locks = _default_random_locks()
        else:
            merged = _default_random_locks()
            merged.update({str(k): bool(v) for k, v in self.random_locks.items()})
            self.random_locks = merged
        if not isinstance(self.display_profile, dict):
            self.display_profile = {}
        if not isinstance(self.layer_groups, list):
            self.layer_groups = []
        self.solo_layer_id = str(self.solo_layer_id or "")
        normalized_groups: list[dict[str, Any]] = []
        seen_group_ids: set[str] = set()
        for raw in self.layer_groups:
            if not isinstance(raw, dict):
                continue
            group_id = str(raw.get("id", "") or "").strip()
            if not group_id or group_id in seen_group_ids:
                continue
            seen_group_ids.add(group_id)
            normalized_groups.append({
                "id": group_id,
                "name": str(raw.get("name", "Layer Group") or "Layer Group"),
                "collapsed": bool(raw.get("collapsed", False)),
                "enabled": bool(raw.get("enabled", True)),
            })
        self.layer_groups = normalized_groups
        if not isinstance(self.audio_envelope, list):
            self.audio_envelope = []
        cleaned_envelope: list[float] = []
        for value in self.audio_envelope[:180000]:
            try:
                cleaned_envelope.append(max(0.0, min(1.0, float(value))))
            except (TypeError, ValueError):
                continue
        self.audio_envelope = cleaned_envelope
        try:
            self.audio_envelope_rate = max(1.0, min(240.0, float(self.audio_envelope_rate)))
        except (TypeError, ValueError):
            self.audio_envelope_rate = 30.0

    def clone(self) -> "ProcessingSettings":
        """Fast independent copy for preview/frame evaluation.

        Avoids the expensive ``asdict -> from_dict`` serialization round-trip
        when the source object is already canonical. Mutable containers are
        copied so callers can safely edit the clone without touching the live
        settings object.
        """
        cloned = copy(self)
        cloned.display_profile = deepcopy(self.display_profile)
        cloned.palette = list(self.palette)
        cloned.palette_locks = list(self.palette_locks)
        cloned.effect_stack = deepcopy(self.effect_stack)
        cloned.layer_groups = deepcopy(self.layer_groups)
        cloned.animation_tracks = deepcopy(self.animation_tracks)
        cloned.audio_envelope = list(self.audio_envelope)
        cloned.random_locks = dict(self.random_locks)
        return cloned

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProcessingSettings":
        allowed = {
            "algorithm", "brightness", "contrast", "saturation", "gamma",
            "grayscale", "invert", "blur_radius", "sharpen",
            "dither_strength", "pixel_size", "serpentine", "output_divisor",
            "target_width", "target_height", "target_enabled", "keep_aspect",
            "fit_mode", "position_x", "position_y", "rotation",
            "flip_horizontal", "flip_vertical", "mirror_horizontal", "mirror_vertical",
            "mirror_horizontal_axis", "mirror_vertical_axis", "crop_left", "crop_top",
            "crop_right", "crop_bottom", "pixel_aspect_x", "pixel_aspect_y",
            "display_mode", "display_export", "display_profile",
            "grid_enabled", "grid_preview", "grid_export", "grid_spacing",
            "grid_major_spacing", "grid_opacity", "hardware_profile_id",
            "hardware_mode", "palette", "palette_locks", "palette_name",
            "palette_author", "palette_source", "effect_stack", "layer_groups", "solo_layer_id",
            "animation_duration", "animation_fps", "animation_loop", "animation_tracks",
            "audio_envelope", "audio_envelope_rate", "random_locks",
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

        obj.target_width = max(0, min(16384, int(obj.target_width)))
        obj.target_height = max(0, min(16384, int(obj.target_height)))
        obj.target_enabled = bool(obj.target_enabled)
        obj.keep_aspect = bool(obj.keep_aspect)
        obj.fit_mode = str(obj.fit_mode or "fit").lower()
        if obj.fit_mode not in {"fit", "fill", "stretch"}:
            obj.fit_mode = "fit"
        obj.position_x = max(-1.0, min(1.0, float(obj.position_x)))
        obj.position_y = max(-1.0, min(1.0, float(obj.position_y)))
        rotation = int(obj.rotation) % 360
        obj.rotation = min((0, 90, 180, 270), key=lambda value: abs(value - rotation))
        obj.flip_horizontal = bool(obj.flip_horizontal)
        obj.flip_vertical = bool(obj.flip_vertical)
        obj.mirror_horizontal = bool(obj.mirror_horizontal)
        obj.mirror_vertical = bool(obj.mirror_vertical)
        obj.mirror_horizontal_axis = max(0.0, min(1.0, float(obj.mirror_horizontal_axis)))
        obj.mirror_vertical_axis = max(0.0, min(1.0, float(obj.mirror_vertical_axis)))
        obj.crop_left = max(0.0, min(0.49, float(obj.crop_left)))
        obj.crop_top = max(0.0, min(0.49, float(obj.crop_top)))
        obj.crop_right = max(0.0, min(0.49, float(obj.crop_right)))
        obj.crop_bottom = max(0.0, min(0.49, float(obj.crop_bottom)))
        # Keep at least ~2% of each axis even if a malformed preset requests
        # overlapping crop margins.
        if obj.crop_left + obj.crop_right > 0.98:
            obj.crop_right = max(0.0, 0.98 - obj.crop_left)
        if obj.crop_top + obj.crop_bottom > 0.98:
            obj.crop_bottom = max(0.0, 0.98 - obj.crop_top)

        obj.pixel_aspect_x = max(0.05, min(20.0, float(obj.pixel_aspect_x)))
        obj.pixel_aspect_y = max(0.05, min(20.0, float(obj.pixel_aspect_y)))
        obj.display_mode = str(obj.display_mode or "corrected").lower()
        if obj.display_mode not in {"raw", "corrected", "display"}:
            obj.display_mode = "corrected"
        obj.display_export = bool(obj.display_export)
        if not isinstance(obj.display_profile, dict):
            obj.display_profile = {}

        obj.grid_enabled = bool(obj.grid_enabled)
        obj.grid_preview = bool(obj.grid_preview)
        obj.grid_export = bool(obj.grid_export)
        obj.grid_spacing = max(1, min(256, int(obj.grid_spacing)))
        obj.grid_major_spacing = max(0, min(1024, int(obj.grid_major_spacing)))
        obj.grid_opacity = max(0.0, min(1.0, float(obj.grid_opacity)))

        obj.hardware_profile_id = str(obj.hardware_profile_id or "custom")
        obj.hardware_mode = str(obj.hardware_mode or "visual").lower()
        if obj.hardware_mode not in {"visual", "strict"}:
            obj.hardware_mode = "visual"
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
        if not isinstance(obj.layer_groups, list):
            obj.layer_groups = []
        obj.solo_layer_id = str(obj.solo_layer_id or "")
        normalized_groups: list[dict[str, Any]] = []
        seen_group_ids: set[str] = set()
        for raw in obj.layer_groups:
            if not isinstance(raw, dict):
                continue
            group_id = str(raw.get("id", "") or "").strip()
            if not group_id or group_id in seen_group_ids:
                continue
            seen_group_ids.add(group_id)
            normalized_groups.append({
                "id": group_id,
                "name": str(raw.get("name", "Layer Group") or "Layer Group"),
                "collapsed": bool(raw.get("collapsed", False)),
                "enabled": bool(raw.get("enabled", True)),
            })
        obj.layer_groups = normalized_groups
        if not isinstance(obj.animation_tracks, list):
            obj.animation_tracks = []
        if not isinstance(obj.audio_envelope, list):
            obj.audio_envelope = []
        cleaned_envelope: list[float] = []
        for value in obj.audio_envelope[:180000]:
            try:
                cleaned_envelope.append(max(0.0, min(1.0, float(value))))
            except (TypeError, ValueError):
                continue
        obj.audio_envelope = cleaned_envelope
        try:
            obj.audio_envelope_rate = max(1.0, min(240.0, float(obj.audio_envelope_rate)))
        except (TypeError, ValueError):
            obj.audio_envelope_rate = 30.0
        obj.animation_duration = max(0.1, min(600.0, float(obj.animation_duration)))
        obj.animation_fps = max(1, min(120, int(obj.animation_fps)))
        obj.animation_loop = bool(obj.animation_loop)

        if not isinstance(obj.random_locks, dict):
            obj.random_locks = _default_random_locks()
        else:
            merged = _default_random_locks()
            merged.update({str(k): bool(v) for k, v in obj.random_locks.items()})
            obj.random_locks = merged
        return obj
