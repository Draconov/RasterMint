# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from .color_utils import hex_to_rgb
from .dither_metadata import ALGORITHMS, MODULATION_MODES

# The UI consumes this schema directly. Keeping effect metadata in the core means
# adding a new effect does not require hard-coding another form in the QML UI.

BLEND_MODES: tuple[str, ...] = (
    "Normal", "Multiply", "Screen", "Overlay", "Soft Light", "Hard Light",
    "Add", "Difference", "Darken", "Lighten",
)
MASK_TYPES: tuple[str, ...] = (
    "None", "Luminance", "Shadows", "Highlights", "Alpha",
    "Radial", "Linear Horizontal", "Linear Vertical",
)

def default_layer_mask() -> dict[str, Any]:
    return {"type": "None", "invert": False, "feather": 0.0, "strength": 1.0}

EFFECT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "Adjustments": {"params": {
        "brightness": {"type": "int", "label": "Brightness", "default": 0, "min": -100, "max": 100, "step": 1, "animatable": True},
        "contrast": {"type": "int", "label": "Contrast", "default": 0, "min": -100, "max": 100, "step": 1, "animatable": True},
        "saturation": {"type": "int", "label": "Saturation", "default": 0, "min": -100, "max": 100, "step": 1, "animatable": True},
        "gamma": {"type": "float", "label": "Gamma", "default": 1.0, "min": 0.1, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
    }},
    "Levels": {"params": {
        "black_point": {"type": "int", "label": "Black point", "default": 0, "min": 0, "max": 254, "step": 1, "animatable": True},
        "white_point": {"type": "int", "label": "White point", "default": 255, "min": 1, "max": 255, "step": 1, "animatable": True},
        "gamma": {"type": "float", "label": "Midtone gamma", "default": 1.0, "min": 0.1, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
    }},
    "Local Contrast": {"params": {
        "amount": {"type": "int", "label": "Amount", "default": 120, "min": 0, "max": 400, "step": 5, "suffix": "%", "animatable": True},
        "radius": {"type": "float", "label": "Radius", "default": 2.0, "min": 0.1, "max": 30.0, "step": 0.25, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "threshold": {"type": "int", "label": "Threshold", "default": 2, "min": 0, "max": 50, "step": 1},
    }},
    "Hue Rotate": {"params": {
        "degrees": {"type": "int", "label": "Degrees", "default": 0, "min": -180, "max": 180, "step": 1, "animatable": True},
    }},
    "Tonal Map": {"params": {
        "mode": {"type": "choice", "label": "Mode", "default": "Tritone", "options": ["Mono", "Duotone", "Tritone", "Gradient"]},
        "shadow_color": {"type": "color", "label": "Shadow", "default": "#000000"},
        "midtone_color": {"type": "color", "label": "Midtone", "default": "#808080"},
        "highlight_color": {"type": "color", "label": "Highlight", "default": "#FFFFFF"},
        "background_color": {"type": "color", "label": "Background", "default": "#000000"},
        "shadow_point": {"type": "float", "label": "Shadow point", "default": 0.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "midpoint": {"type": "float", "label": "Midpoint", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "highlight_point": {"type": "float", "label": "Highlight point", "default": 100.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "blend_softness": {"type": "float", "label": "Blend softness", "default": 100.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "preserve_alpha": {"type": "bool", "label": "Preserve alpha", "default": True},
    }},
    "Grayscale": {"params": {}},
    "Invert": {"params": {}},
    "Gaussian Blur": {"params": {
        "radius": {"type": "float", "label": "Radius", "default": 2.0, "min": 0.0, "max": 30.0, "step": 0.25, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
    }},
    "Median Denoise": {"params": {
        "radius": {"type": "int", "label": "Radius", "default": 1, "min": 1, "max": 5, "step": 1, "pixel_scaled": True},
    }},
    "Sharpen": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 1.5, "min": 0.0, "max": 5.0, "step": 0.1, "decimals": 2, "animatable": True},
    }},
    "Glow": {"params": {
        "radius": {"type": "float", "label": "Radius", "default": 5.0, "min": 0.0, "max": 40.0, "step": 0.5, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "intensity": {"type": "float", "label": "Intensity", "default": 0.35, "min": 0.0, "max": 2.0, "step": 0.05, "decimals": 2, "animatable": True},
    }},
    "Bloom": {"params": {
        "threshold": {"type": "float", "label": "Threshold", "default": 0.65, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "soft_knee": {"type": "float", "label": "Soft knee", "default": 0.20, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "radius": {"type": "float", "label": "Radius", "default": 10.0, "min": 0.0, "max": 80.0, "step": 0.5, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "intensity": {"type": "float", "label": "Intensity", "default": 0.80, "min": 0.0, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
        "blend": {"type": "choice", "label": "Blend", "default": "Screen", "options": ["Screen", "Add"]},
    }},
    "Vignette": {"params": {
        "strength": {"type": "float", "label": "Strength", "default": 0.45, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "size": {"type": "float", "label": "Size", "default": 0.62, "min": 0.05, "max": 1.5, "step": 0.01, "decimals": 2, "animatable": True},
        "softness": {"type": "float", "label": "Softness", "default": 0.45, "min": 0.01, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "roundness": {"type": "float", "label": "Roundness", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "center_x": {"type": "float", "label": "Center X", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "center_y": {"type": "float", "label": "Center Y", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "color": {"type": "color", "label": "Color", "default": "#000000"},
    }},
    "JPEG Compression": {"params": {
        "quality": {"type": "int", "label": "Quality", "default": 35, "min": 5, "max": 95, "step": 1, "animatable": True},
    }},
    "Chromatic Shift": {"params": {
        "amount": {"type": "int", "label": "Offset", "default": 3, "min": -40, "max": 40, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
    }},
    "RGB Split": {"params": {
        "x": {"type": "int", "label": "X offset", "default": 3, "min": -64, "max": 64, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "y": {"type": "int", "label": "Y offset", "default": 0, "min": -64, "max": 64, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
    }},
    "Posterize": {"params": {
        "levels": {"type": "int", "label": "Levels", "default": 6, "min": 2, "max": 64, "step": 1, "animatable": True},
    }},
    "Scanlines": {"params": {
        "spacing": {"type": "int", "label": "Spacing", "default": 3, "min": 2, "max": 16, "step": 1, "pixel_scaled": True},
        "strength": {"type": "float", "label": "Darken", "default": 0.25, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
    }},
    "Interlace": {"params": {
        "offset": {"type": "int", "label": "Odd-line shift", "default": 2, "min": -32, "max": 32, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "darken": {"type": "float", "label": "Odd-line darken", "default": 0.12, "min": 0.0, "max": 1.0, "step": 0.02, "decimals": 2, "animatable": True},
    }},
    "Display Persistence": {"params": {
        "display_type": {"type": "choice", "label": "Display type", "default": "CRT", "options": ["Generic", "CRT", "LCD", "OLED"]},
        "persistence_time": {"type": "duration", "label": "Persistence time", "default": 0.35, "min": 0.0, "max": 300.0, "slider_max": 60.0, "step": 0.05, "decimals": 2, "suffix": " s", "animatable": True},
        "strength": {"type": "float", "label": "Strength", "default": 0.45, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "decay": {"type": "float", "label": "Decay speed", "default": 1.0, "min": 0.1, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
    }},
    "Chroma Bleed": {"params": {
        "bleed": {"type": "float", "label": "Bleed", "default": 3.0, "min": 0.0, "max": 24.0, "step": 0.25, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "delay": {"type": "int", "label": "Delay", "default": 1, "min": -16, "max": 16, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "strength": {"type": "float", "label": "Strength", "default": 0.75, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
    }},
    "Tracking Error": {"params": {
        "amount": {"type": "int", "label": "Shift", "default": 10, "min": 0, "max": 128, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "band_height": {"type": "int", "label": "Band height", "default": 6, "min": 1, "max": 64, "step": 1, "suffix": " px", "pixel_scaled": True},
        "instability": {"type": "float", "label": "Instability", "default": 0.55, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "speed": {"type": "float", "label": "Speed", "default": 4.0, "min": 0.0, "max": 30.0, "step": 0.1, "decimals": 1, "suffix": " Hz", "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "Tape Dropout": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 0.18, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "length": {"type": "int", "label": "Max streak length", "default": 48, "min": 2, "max": 256, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "thickness": {"type": "int", "label": "Max streak thickness", "default": 2, "min": 1, "max": 12, "step": 1, "suffix": " px", "pixel_scaled": True},
        "strength": {"type": "float", "label": "Strength", "default": 0.65, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "Temporal Jitter": {"params": {
        "x": {"type": "float", "label": "Horizontal jitter", "default": 2.0, "min": 0.0, "max": 32.0, "step": 0.1, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "y": {"type": "float", "label": "Vertical jitter", "default": 1.0, "min": 0.0, "max": 32.0, "step": 0.1, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "speed": {"type": "float", "label": "Speed", "default": 6.0, "min": 0.0, "max": 30.0, "step": 0.1, "decimals": 1, "suffix": " Hz", "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "Head Switching Noise": {"params": {
        "height": {"type": "int", "label": "Band height", "default": 18, "min": 1, "max": 96, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "shift": {"type": "int", "label": "Shift", "default": 20, "min": 0, "max": 256, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "noise": {"type": "float", "label": "Noise", "default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "strength": {"type": "float", "label": "Strength", "default": 0.75, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "RGB Convergence": {"params": {
        "red_x": {"type": "float", "label": "Red X", "default": 1.0, "min": -12.0, "max": 12.0, "step": 0.1, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "red_y": {"type": "float", "label": "Red Y", "default": 0.0, "min": -12.0, "max": 12.0, "step": 0.1, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "blue_x": {"type": "float", "label": "Blue X", "default": -1.0, "min": -12.0, "max": 12.0, "step": 0.1, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "blue_y": {"type": "float", "label": "Blue Y", "default": 0.0, "min": -12.0, "max": 12.0, "step": 0.1, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "strength": {"type": "float", "label": "Strength", "default": 0.7, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
    }},
    "CRT Mask": {"params": {
        "mask_type": {"type": "choice", "label": "Mask type", "default": "Aperture Grille", "options": ["Aperture Grille", "Shadow Mask", "Slot Mask"]},
        "scale": {"type": "int", "label": "Cell size", "default": 3, "min": 1, "max": 16, "step": 1, "suffix": " px", "pixel_scaled": True},
        "strength": {"type": "float", "label": "Mask strength", "default": 0.32, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "brightness": {"type": "float", "label": "Brightness compensation", "default": 0.12, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
    }},
    "Phosphor Glow": {"params": {
        "threshold": {"type": "float", "label": "Threshold", "default": 0.55, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "radius": {"type": "float", "label": "Radius", "default": 2.2, "min": 0.0, "max": 24.0, "step": 0.1, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "intensity": {"type": "float", "label": "Intensity", "default": 0.35, "min": 0.0, "max": 2.0, "step": 0.01, "decimals": 2, "animatable": True},
    }},
    "Beam Width": {"params": {
        "spacing": {"type": "int", "label": "Spacing", "default": 3, "min": 2, "max": 16, "step": 1, "pixel_scaled": True},
        "width": {"type": "float", "label": "Beam width", "default": 0.65, "min": 0.1, "max": 1.5, "step": 0.01, "decimals": 2, "animatable": True},
        "strength": {"type": "float", "label": "Strength", "default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
    }},
    "Horizontal Bloom": {"params": {
        "threshold": {"type": "float", "label": "Threshold", "default": 0.7, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "radius": {"type": "float", "label": "Horizontal radius", "default": 5.0, "min": 0.0, "max": 64.0, "step": 0.25, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "intensity": {"type": "float", "label": "Intensity", "default": 0.4, "min": 0.0, "max": 2.0, "step": 0.01, "decimals": 2, "animatable": True},
    }},
    "Scanline Variation": {"params": {
        "spacing": {"type": "int", "label": "Spacing", "default": 3, "min": 2, "max": 16, "step": 1, "pixel_scaled": True},
        "strength": {"type": "float", "label": "Darken", "default": 0.18, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "variation": {"type": "float", "label": "Variation", "default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "speed": {"type": "float", "label": "Speed", "default": 1.5, "min": 0.0, "max": 20.0, "step": 0.1, "decimals": 1, "suffix": " Hz", "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "CRT Curvature": {"params": {
        "curvature": {"type": "float", "label": "Curvature", "default": 0.12, "min": 0.0, "max": 0.5, "step": 0.005, "decimals": 3, "animatable": True},
        "zoom": {"type": "float", "label": "Overscan", "default": 1.03, "min": 1.0, "max": 1.3, "step": 0.005, "decimals": 3, "animatable": True},
        "edge_fade": {"type": "float", "label": "Edge fade", "default": 0.08, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "border_fill": {"type": "choice", "label": "Border Fill", "default": "Solid Color", "options": ["Solid Color", "Auto", "Transparent"]},
        "border_color": {"type": "color", "label": "Border Color", "default": "#000000"},
    }},
    "Edge Distortion": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 2.0, "min": 0.0, "max": 32.0, "step": 0.1, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "frequency": {"type": "float", "label": "Frequency", "default": 2.0, "min": 0.1, "max": 16.0, "step": 0.1, "decimals": 1, "animatable": True},
        "falloff": {"type": "float", "label": "Edge falloff", "default": 0.35, "min": 0.05, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
    }},
    "Vertical Sync Roll": {"params": {
        "amount": {"type": "int", "label": "Roll amount", "default": 24, "min": 0, "max": 256, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "speed": {"type": "float", "label": "Speed", "default": 0.35, "min": -5.0, "max": 5.0, "step": 0.05, "decimals": 2, "suffix": " Hz", "animatable": True},
        "softness": {"type": "float", "label": "Band softness", "default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
    }},
    "Field Flicker": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 0.06, "min": 0.0, "max": 0.5, "step": 0.005, "decimals": 3, "animatable": True},
        "field_rate": {"type": "choice", "label": "Field rate", "default": "60 Hz", "options": ["50 Hz", "60 Hz"]},
        "interlaced": {"type": "bool", "label": "Alternate fields", "default": True},
    }},
    "LCD Inversion": {"params": {
        "pattern": {"type": "choice", "label": "Pattern", "default": "Columns", "options": ["Columns", "Rows", "Checker"]},
        "amount": {"type": "float", "label": "Amount", "default": 0.08, "min": 0.0, "max": 0.5, "step": 0.005, "decimals": 3, "animatable": True},
        "scale": {"type": "int", "label": "Cell size", "default": 1, "min": 1, "max": 8, "step": 1, "pixel_scaled": True},
        "phase": {"type": "int", "label": "Phase", "default": 0, "min": 0, "max": 1, "step": 1, "animatable": True},
    }},
    "Dot Crawl": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 0.18, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "scale": {"type": "float", "label": "Scale", "default": 2.0, "min": 1.0, "max": 16.0, "step": 0.25, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "speed": {"type": "float", "label": "Speed", "default": 3.58, "min": 0.0, "max": 20.0, "step": 0.01, "decimals": 2, "animatable": True},
    }},
    "Composite Noise": {"params": {
        "luma": {"type": "float", "label": "Luma noise", "default": 0.06, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "chroma": {"type": "float", "label": "Chroma noise", "default": 0.08, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "RF Interference": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "bands": {"type": "int", "label": "Bands", "default": 3, "min": 1, "max": 16, "step": 1},
        "speed": {"type": "float", "label": "Speed", "default": 2.0, "min": 0.0, "max": 20.0, "step": 0.1, "decimals": 1, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "Horizontal Tear": {"params": {
        "amount": {"type": "int", "label": "Shift", "default": 20, "min": 0, "max": 256, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "bands": {"type": "int", "label": "Bands", "default": 2, "min": 1, "max": 16, "step": 1},
        "height": {"type": "int", "label": "Band height", "default": 6, "min": 1, "max": 64, "step": 1, "suffix": " px", "pixel_scaled": True},
        "speed": {"type": "float", "label": "Speed", "default": 3.0, "min": 0.0, "max": 20.0, "step": 0.1, "decimals": 1, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "Noise": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 12.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "animatable": True},
        "chroma": {"type": "bool", "label": "Chroma noise", "default": False},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Temporal Flicker": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 0.08, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "speed": {"type": "float", "label": "Speed", "default": 4.0, "min": 0.1, "max": 30.0, "step": 0.1, "decimals": 1, "suffix": " Hz", "animatable": True},
    }},
    "Temporal Pattern": {"params": {
        "pattern": {"type": "choice", "label": "Pattern", "default": "Wave X", "options": ["Pulse", "Wave X", "Wave Y", "Diagonal Wave", "Checker Phase", "Scan Sweep", "Noise Drift", "Alternating", "Radial Pulse"]},
        "amount": {"type": "float", "label": "Amount", "default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "speed": {"type": "float", "label": "Speed", "default": 1.0, "min": 0.0, "max": 30.0, "step": 0.1, "decimals": 1, "suffix": " Hz", "animatable": True},
        "scale": {"type": "float", "label": "Scale", "default": 32.0, "min": 2.0, "max": 256.0, "step": 1.0, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "phase": {"type": "float", "label": "Phase", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "Pixel Aspect Ratio": {"params": {
        "x": {"type": "float", "label": "Pixel width", "default": 1.0, "min": 0.25, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
        "y": {"type": "float", "label": "Pixel height", "default": 1.0, "min": 0.25, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
        "resample": {"type": "choice", "label": "Resample", "default": "Nearest", "options": ["Nearest", "Bilinear", "Bicubic", "Lanczos"]},
    }},
    "Pixelate": {"params": {
        "size": {"type": "int", "label": "Pixel size", "default": 2, "min": 1, "max": 64, "step": 1, "animatable": True, "pixel_scaled": True},
    }},
    "Pixel Art Cleanup": {"params": {
        "orphan_removal": {"type": "int", "label": "Orphan-pixel removal", "default": 75, "min": 0, "max": 100, "step": 1, "suffix": "%"},
        "cluster_cleanup": {"type": "int", "label": "Cluster cleanup", "default": 35, "min": 0, "max": 100, "step": 1, "suffix": "%"},
        "line_cleanup": {"type": "int", "label": "Line cleanup", "default": 50, "min": 0, "max": 100, "step": 1, "suffix": "%"},
        "staircase_correction": {"type": "int", "label": "Staircase correction", "default": 45, "min": 0, "max": 100, "step": 1, "suffix": "%"},
        "tiny_island_size": {"type": "int", "label": "Tiny-island maximum", "default": 4, "min": 0, "max": 64, "step": 1, "suffix": " px"},
        "edge_preservation": {"type": "int", "label": "Edge preservation", "default": 80, "min": 0, "max": 100, "step": 1, "suffix": "%"},
        "passes": {"type": "int", "label": "Cleanup passes", "default": 2, "min": 1, "max": 4, "step": 1},
        "connectivity": {"type": "choice", "label": "Cluster connectivity", "default": "8-neighbour", "options": ["4-neighbour", "8-neighbour"]},
        "analysis_view": {"type": "choice", "label": "Visualization", "default": "Clean Result", "options": ["Clean Result", "Issue Overlay", "Cluster Map"]},
    }},
    "Pixel Sort": {"params": {
        "threshold": {"type": "float", "label": "Threshold", "default": 0.45, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "direction": {"type": "choice", "label": "Direction", "default": "Horizontal", "options": ["Horizontal", "Vertical"]},
        "reverse": {"type": "bool", "label": "Reverse", "default": False},
    }},
    "Screen Melt": {"params": {
        "amount": {"type": "int", "label": "Max drop", "default": 24, "min": 0, "max": 256, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "column_width": {"type": "int", "label": "Column width", "default": 6, "min": 1, "max": 64, "step": 1, "pixel_scaled": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Block Shuffle": {"params": {
        "block": {"type": "int", "label": "Block size", "default": 16, "min": 2, "max": 128, "step": 1, "suffix": " px", "pixel_scaled": True},
        "amount": {"type": "float", "label": "Fraction", "default": 0.35, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Pixel Scatter": {"params": {
        "distance": {"type": "int", "label": "Distance", "default": 8, "min": 0, "max": 128, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "density": {"type": "float", "label": "Density", "default": 0.15, "min": 0.0, "max": 1.0, "step": 0.02, "decimals": 2, "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Data Shift": {"params": {
        "amount": {"type": "int", "label": "Horizontal shift", "default": 24, "min": 0, "max": 256, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "band_height": {"type": "int", "label": "Band height", "default": 8, "min": 1, "max": 64, "step": 1, "suffix": " px", "pixel_scaled": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Row Shift": {"params": {
        "amount": {"type": "int", "label": "Max shift", "default": 12, "min": 0, "max": 128, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "period": {"type": "int", "label": "Row period", "default": 4, "min": 1, "max": 64, "step": 1, "pixel_scaled": True},
    }},
    "Column Shift": {"params": {
        "amount": {"type": "int", "label": "Max shift", "default": 12, "min": 0, "max": 128, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "period": {"type": "int", "label": "Column period", "default": 4, "min": 1, "max": 64, "step": 1, "pixel_scaled": True},
    }},
    "Cellular Automata": {"params": {
        "threshold": {"type": "float", "label": "Threshold", "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "steps": {"type": "int", "label": "Steps", "default": 2, "min": 1, "max": 12, "step": 1},
        "blend": {"type": "float", "label": "Blend", "default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
    }},
    "Databend": {"params": {
        "quality": {"type": "int", "label": "JPEG quality", "default": 25, "min": 5, "max": 90, "step": 1},
        "shift": {"type": "int", "label": "Band shift", "default": 28, "min": 0, "max": 256, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "temporal": {"type": "bool", "label": "Animate seed", "default": False},
    }},
    "Channel Swap": {"params": {
        "order": {"type": "choice", "label": "Order", "default": "GBR", "options": ["RGB", "RBG", "GRB", "GBR", "BRG", "BGR"]},
    }},
    "Pixel Material": {"params": {
        "style": {"type": "choice", "label": "Style", "default": "Flat", "options": ["Flat", "Round Dots", "CRT Phosphor", "LED", "LCD", "Fuse Bead", "Cross Stitch", "Brick", "Mosaic", "Halftone Dot", "ASCII Tile", "Custom Sprite"]},
        "cell_size": {"type": "int", "label": "Cell size", "default": 8, "min": 2, "max": 64, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "gap": {"type": "int", "label": "Gap", "default": 1, "min": 0, "max": 12, "step": 1, "suffix": " px", "pixel_scaled": True},
        "background": {"type": "color", "label": "Background", "default": "#101217"},
        "sprite_path": {"type": "file", "label": "Custom sprite", "default": "", "file_filter": "Images (*.png *.webp *.bmp *.gif);;All files (*.*)"},
    }},
    "Text Overlay": {"params": {
        "text": {"type": "text", "label": "Text", "default": "RasterMint"},
        "x": {"type": "float", "label": "X", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "y": {"type": "float", "label": "Y", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "size": {"type": "int", "label": "Size", "default": 18, "min": 6, "max": 512, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "color": {"type": "color", "label": "Color", "default": "#FFFFFF"},
        "outline": {"type": "int", "label": "Outline", "default": 1, "min": 0, "max": 8, "step": 1, "suffix": " px", "pixel_scaled": True},
        "shadow": {"type": "int", "label": "Shadow", "default": 0, "min": 0, "max": 16, "step": 1, "suffix": " px", "pixel_scaled": True},
    }},
    "ASCII / Glyph": {"params": {
        "character_set": {"type": "glyph_set", "label": "Character set", "default": "Classic ASCII"},
        "custom_chars": {"type": "text", "label": "Custom characters", "default": " .:-=+*#%@"},
        "inject_chars": {"type": "text", "label": "Inject characters", "default": ""},
        "symbol_randomization": {"type": "float", "label": "Symbol Randomization", "default": 0.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 0, "suffix": "%", "animatable": True},
        "mapping": {"type": "choice", "label": "Mapping", "default": "Density", "options": ["Density", "Structure Match"]},
        "auto_density": {"type": "bool", "label": "Auto-sort by visual density", "default": True},
        "structure": {"type": "float", "label": "Structure", "default": 75.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 0, "suffix": "%", "animatable": True},
        "density_influence": {"type": "float", "label": "Density influence", "default": 25.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 0, "suffix": "%", "animatable": True},
        "local_detail": {"type": "float", "label": "Local detail", "default": 35.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 0, "suffix": "%", "animatable": True},
        "auto_cell_aspect": {"type": "bool", "label": "Auto cell aspect", "default": True},
        "supersampling": {"type": "choice", "label": "Supersampling", "default": "4×", "options": ["1×", "2×", "4×"]},
        "color_sampling": {"type": "choice", "label": "Colour sampling", "default": "Glyph Weighted", "options": ["Cell Average", "Glyph Weighted"]},
        "cell_size": {"type": "int", "label": "Cell size", "default": 10, "min": 4, "max": 64, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "spacing_x": {"type": "int", "label": "Horizontal spacing", "default": 0, "min": -8, "max": 32, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "spacing_y": {"type": "int", "label": "Vertical spacing", "default": 0, "min": -8, "max": 32, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "depth": {"type": "int", "label": "Character depth", "default": 9, "min": 2, "max": 256, "step": 1, "animatable": True},
        "offset": {"type": "int", "label": "Character offset", "default": 0, "min": -64, "max": 64, "step": 1, "animatable": True},
        "invert": {"type": "bool", "label": "Invert mapping", "default": False},
        "color_mode": {"type": "choice", "label": "Colour mode", "default": "Source", "options": ["Source", "Palette", "Single Colour"]},
        "foreground": {"type": "color", "label": "Foreground", "default": "#FFFFFF"},
        "background_mode": {"type": "choice", "label": "Background mode", "default": "Solid Colour", "options": ["Solid Colour", "Transparent", "Source Image"]},
        "background": {"type": "color", "label": "Background colour", "default": "#101217"},
        "font": {"type": "choice", "label": "Font", "default": "Mono", "options": ["Pixel", "Mono", "Sans", "Serif"]},
        "font_scale": {"type": "float", "label": "Glyph scale", "default": 0.9, "min": 0.4, "max": 1.5, "step": 0.05, "decimals": 2, "suffix": "×", "animatable": True},
        "cell_mode": {"type": "choice", "label": "Cell Mode", "default": "Normal", "options": ["Normal", "1:1 Pixel Symbols"]},
    }},
    "Pixel Text": {"params": {
        "text": {"type": "text", "label": "Text", "default": "RasterMint"},
        "x": {"type": "float", "label": "X", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "y": {"type": "float", "label": "Y", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "size": {"type": "int", "label": "Size", "default": 24, "min": 6, "max": 512, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "color": {"type": "color", "label": "Color", "default": "#FFFFFF"},
        "font": {"type": "choice", "label": "Font", "default": "Pixel", "options": ["Pixel", "Mono", "Sans", "Serif"]},
        "alignment": {"type": "choice", "label": "Alignment", "default": "Center", "options": ["Left", "Center", "Right"]},
        "wrap_width": {"type": "float", "label": "Wrap width", "default": 80.0, "min": 10.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "letter_spacing": {"type": "int", "label": "Letter spacing", "default": 1, "min": -4, "max": 32, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "line_spacing": {"type": "int", "label": "Line spacing", "default": 2, "min": 0, "max": 64, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "rotation": {"type": "float", "label": "Rotation", "default": 0.0, "min": -180.0, "max": 180.0, "step": 1.0, "decimals": 1, "suffix": "°", "animatable": True},
        "outline": {"type": "int", "label": "Outline", "default": 0, "min": 0, "max": 8, "step": 1, "suffix": " px", "pixel_scaled": True},
        "shadow": {"type": "int", "label": "Shadow", "default": 0, "min": 0, "max": 16, "step": 1, "suffix": " px", "pixel_scaled": True},
    }},
    "Text Pattern": {"params": {
        "text": {"type": "text", "label": "Text", "default": "RasterMint"},
        "size": {"type": "int", "label": "Size", "default": 16, "min": 6, "max": 512, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "color": {"type": "color", "label": "Color", "default": "#FFFFFF"},
        "font": {"type": "choice", "label": "Font", "default": "Mono", "options": ["Pixel", "Mono", "Sans", "Serif"]},
        "spacing_x": {"type": "int", "label": "Horizontal spacing", "default": 120, "min": 12, "max": 1024, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "spacing_y": {"type": "int", "label": "Vertical spacing", "default": 56, "min": 12, "max": 1024, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "offset_x": {"type": "int", "label": "Row offset", "default": 36, "min": -512, "max": 512, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "rotation": {"type": "float", "label": "Rotation", "default": -15.0, "min": -180.0, "max": 180.0, "step": 1.0, "decimals": 1, "suffix": "°", "animatable": True},
        "opacity": {"type": "float", "label": "Opacity", "default": 0.55, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
    }},
    "Text Mask": {"params": {
        "text": {"type": "text", "label": "Text", "default": "RasterMint"},
        "x": {"type": "float", "label": "X", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "y": {"type": "float", "label": "Y", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "size": {"type": "int", "label": "Size", "default": 72, "min": 8, "max": 512, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "font": {"type": "choice", "label": "Font", "default": "Sans", "options": ["Pixel", "Mono", "Sans", "Serif"]},
        "mode": {"type": "choice", "label": "Mode", "default": "Keep Inside", "options": ["Keep Inside", "Cut Out"]},
        "background_mode": {"type": "choice", "label": "Background", "default": "Solid Colour", "options": ["Transparent", "Solid Colour"]},
        "background": {"type": "color", "label": "Background colour", "default": "#000000"},
        "threshold": {"type": "float", "label": "Threshold", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "feather": {"type": "float", "label": "Feather", "default": 0.0, "min": 0.0, "max": 32.0, "step": 0.5, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "invert": {"type": "bool", "label": "Invert mask", "default": False},
        "rotation": {"type": "float", "label": "Rotation", "default": 0.0, "min": -180.0, "max": 180.0, "step": 1.0, "decimals": 1, "suffix": "°", "animatable": True},
    }},
    "Wave / Jitter Text": {"params": {
        "text": {"type": "text", "label": "Text", "default": "RasterMint"},
        "x": {"type": "float", "label": "X", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "y": {"type": "float", "label": "Y", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "size": {"type": "int", "label": "Size", "default": 28, "min": 6, "max": 512, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "color": {"type": "color", "label": "Color", "default": "#FFFFFF"},
        "font": {"type": "choice", "label": "Font", "default": "Pixel", "options": ["Pixel", "Mono", "Sans", "Serif"]},
        "amplitude": {"type": "float", "label": "Wave amplitude", "default": 8.0, "min": 0.0, "max": 128.0, "step": 1.0, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "wavelength": {"type": "float", "label": "Wavelength", "default": 5.0, "min": 1.0, "max": 32.0, "step": 0.5, "decimals": 1, "animatable": True},
        "jitter": {"type": "float", "label": "Jitter", "default": 2.0, "min": 0.0, "max": 64.0, "step": 0.5, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "speed": {"type": "float", "label": "Speed", "default": 1.0, "min": 0.0, "max": 20.0, "step": 0.1, "decimals": 1, "suffix": " Hz", "animatable": True},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "Typewriter Text": {"params": {
        "text": {"type": "text", "label": "Text", "default": "RasterMint"},
        "x": {"type": "float", "label": "X", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "y": {"type": "float", "label": "Y", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "size": {"type": "int", "label": "Size", "default": 24, "min": 6, "max": 512, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "color": {"type": "color", "label": "Color", "default": "#FFFFFF"},
        "font": {"type": "choice", "label": "Font", "default": "Mono", "options": ["Pixel", "Mono", "Sans", "Serif"]},
        "progress": {"type": "float", "label": "Reveal", "default": 100.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "reveal_mode": {"type": "choice", "label": "Reveal by", "default": "Characters", "options": ["Characters", "Words", "Lines"]},
        "cursor": {"type": "bool", "label": "Show cursor", "default": True},
        "cursor_char": {"type": "text", "label": "Cursor", "default": "_"},
        "cursor_blink": {"type": "bool", "label": "Blink cursor", "default": True},
        "cursor_blink_speed": {"type": "float", "label": "Cursor blink speed", "default": 2.0, "min": 0.1, "max": 20.0, "step": 0.1, "decimals": 1, "suffix": " Hz", "animatable": True},
    }},
    "Text Glitch": {"params": {
        "text": {"type": "text", "label": "Text", "default": "RasterMint"},
        "x": {"type": "float", "label": "X", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "y": {"type": "float", "label": "Y", "default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "size": {"type": "int", "label": "Size", "default": 36, "min": 6, "max": 512, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "color": {"type": "color", "label": "Color", "default": "#FFFFFF"},
        "font": {"type": "choice", "label": "Font", "default": "Pixel", "options": ["Pixel", "Mono", "Sans", "Serif"]},
        "rgb_offset": {"type": "int", "label": "RGB offset", "default": 3, "min": 0, "max": 64, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "slice_shift": {"type": "int", "label": "Slice shift", "default": 8, "min": 0, "max": 128, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "slice_height": {"type": "int", "label": "Slice height", "default": 4, "min": 1, "max": 32, "step": 1, "suffix": " px", "pixel_scaled": True},
        "vertical_jitter": {"type": "int", "label": "Vertical jitter", "default": 0, "min": 0, "max": 64, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "dropout": {"type": "float", "label": "Slice dropout", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
        "opacity": {"type": "float", "label": "Opacity", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
        "temporal": {"type": "bool", "label": "Animate glitch", "default": False},
        "seed": {"type": "int", "label": "Seed", "default": 1, "min": 0, "max": 999999, "step": 1},
    }},
    "Dither Glow": {"params": {
        "threshold": {"type": "float", "label": "Threshold", "default": 0.72, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "softness": {"type": "float", "label": "Softness", "default": 0.18, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "radius": {"type": "float", "label": "Radius", "default": 5.0, "min": 0.0, "max": 64.0, "step": 0.25, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "spread": {"type": "int", "label": "Spread", "default": 1, "min": 0, "max": 12, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "intensity": {"type": "float", "label": "Intensity", "default": 1.25, "min": 0.0, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
        "blend": {"type": "choice", "label": "Blend", "default": "Screen", "options": ["Screen", "Add"]},
        "glow_color_mode": {"type": "choice", "label": "Glow colour", "default": "Source", "options": ["Source", "Custom Tint"]},
        "glow_color": {"type": "color", "label": "Tint colour", "default": "#9EF7FF"},
        "preserve_core": {"type": "bool", "label": "Preserve source highlights", "default": True},
    }},
    "Hardware Limits": {"params": {
        "palette_source": {"type": "choice", "label": "Palette enforcement", "default": "Active Palette", "options": ["Active Palette", "Profile Palette"]},
        "channel_r_bits": {"type": "int", "label": "Red channel bits", "default": 8, "min": 1, "max": 8, "step": 1},
        "channel_g_bits": {"type": "int", "label": "Green channel bits", "default": 8, "min": 1, "max": 8, "step": 1},
        "channel_b_bits": {"type": "int", "label": "Blue channel bits", "default": 8, "min": 1, "max": 8, "step": 1},
        "max_colors_global": {"type": "int", "label": "Maximum global colours", "default": 0, "min": 0, "max": 256, "step": 1},
        "tile_max_colors": {"type": "int", "label": "Maximum colours per tile", "default": 0, "min": 0, "max": 256, "step": 1},
        "tile_width": {"type": "int", "label": "Tile width", "default": 8, "min": 1, "max": 128, "step": 1, "suffix": " px", "pixel_scaled": True},
        "tile_height": {"type": "int", "label": "Tile height", "default": 8, "min": 1, "max": 128, "step": 1, "suffix": " px", "pixel_scaled": True},
        "use_profile_groups": {"type": "bool", "label": "Use profile palette groups", "default": False},
        "profile_palette_json": {"type": "text", "label": "Profile palette data", "default": "[]", "hidden": True},
        "profile_group_indices_json": {"type": "text", "label": "Profile palette groups", "default": "[]", "hidden": True},
    }},
    "Hardware Display": {"params": {
        "gamma": {"type": "float", "label": "Display gamma", "default": 1.0, "min": 0.1, "max": 4.0, "step": 0.05, "decimals": 2, "animatable": True},
        "color_bleed": {"type": "float", "label": "Colour bleed", "default": 0.0, "min": 0.0, "max": 8.0, "step": 0.1, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "blur": {"type": "float", "label": "Display blur", "default": 0.0, "min": 0.0, "max": 8.0, "step": 0.05, "decimals": 2, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "scanlines": {"type": "float", "label": "Scanlines", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "lcd_grid": {"type": "float", "label": "LCD grid", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
    }},
    "Pop Tone": {"params": {
        "scale": {"type": "int", "label": "Scale / DPI", "default": 8, "min": 2, "max": 64, "step": 1, "suffix": " px", "pixel_scaled": True},
        "density": {"type": "float", "label": "Density", "default": 0.72, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2},
        "variation": {"type": "float", "label": "Variation", "default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2},
    }},
    "Polygon Dither": {"params": {
        "variant": {"type": "choice", "label": "Polygon style", "default": "Hexa-Poly", "options": ["Hexa-Poly", "Penta-Poly", "Tri-Poly", "Low-Poly"]},
        "cell_size": {"type": "int", "label": "Cell size", "default": 12, "min": 3, "max": 128, "step": 1, "suffix": " px", "pixel_scaled": True},
    }},
    "Beehive": {"params": {
        "scale": {"type": "int", "label": "Scale / DPI", "default": 10, "min": 2, "max": 64, "step": 1},
        "luminance_threshold": {"type": "float", "label": "Luminance threshold", "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2},
        "cell_size": {"type": "int", "label": "Cell size", "default": 10, "min": 3, "max": 128, "step": 1, "suffix": " px", "pixel_scaled": True},
    }},
    "Print Lab": {"params": {
        "mode": {"type": "choice", "label": "Print mode", "default": "CMYK", "options": ["Monochrome", "CMYK", "RGB", "Spot Colors"]},
        "cell_size": {"type": "int", "label": "Cell size", "default": 8, "min": 2, "max": 128, "step": 1, "suffix": " px", "pixel_scaled": True},
        "dot_shape": {"type": "choice", "label": "Dot shape", "default": "Round", "options": ["Round", "Ellipse", "Square", "Diamond", "Line"]},
        "paper_color": {"type": "color", "label": "Paper colour", "default": "#F5F0E5"},
        "dot_gain": {"type": "float", "label": "Dot gain", "default": 0.0, "min": -50.0, "max": 100.0, "step": 1.0, "decimals": 0, "suffix": "%"},
        "black_mix": {"type": "float", "label": "Black mix", "default": 100.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 0, "suffix": "%"},
        "phase_offsets": {"type": "bool", "label": "Custom phase offsets", "default": False},
        "registration_error": {"type": "float", "label": "Registration error", "default": 0.0, "min": 0.0, "max": 64.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True},
        "roughness": {"type": "float", "label": "Screen roughness", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2},
        "missing_ink": {"type": "float", "label": "Missing / weak ink", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2},
        "ink_spread": {"type": "float", "label": "Ink spread", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2},
        "paper_grain": {"type": "float", "label": "Paper grain interaction", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2},
        "squeegee": {"type": "float", "label": "Squeegee / coverage artifacts", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2},
        "overprint": {"type": "bool", "label": "Subtractive overprint", "default": True},
        "ink_count": {"type": "int", "label": "Spot ink count", "default": 4, "min": 1, "max": 8, "step": 1},
        "preview": {"type": "choice", "label": "Separation preview", "default": "Composite", "options": ["Composite", "Cyan", "Magenta", "Yellow", "Black", "Red", "Green", "Blue", "Spot 1", "Spot 2", "Spot 3", "Spot 4", "Spot 5", "Spot 6", "Spot 7", "Spot 8"]},
        "seed": {"type": "int", "label": "Imperfection seed", "default": 1, "min": 0, "max": 999999, "step": 1},
        "ink1_color": {"type": "color", "label": "Ink 1 colour", "default": "#00AEEF", "hidden": True},
        "ink1_angle": {"type": "float", "label": "Ink 1 angle", "default": 15, "min": -180.0, "max": 180.0, "step": 1.0, "decimals": 1, "suffix": "°", "hidden": True},
        "ink1_offset_x": {"type": "float", "label": "Ink 1 X registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink1_offset_y": {"type": "float", "label": "Ink 1 Y registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink1_phase_x": {"type": "float", "label": "Ink 1 phase X", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink1_phase_y": {"type": "float", "label": "Ink 1 phase Y", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink1_opacity": {"type": "float", "label": "Ink 1 opacity", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "hidden": True},
        "ink2_color": {"type": "color", "label": "Ink 2 colour", "default": "#EC008C", "hidden": True},
        "ink2_angle": {"type": "float", "label": "Ink 2 angle", "default": 75, "min": -180.0, "max": 180.0, "step": 1.0, "decimals": 1, "suffix": "°", "hidden": True},
        "ink2_offset_x": {"type": "float", "label": "Ink 2 X registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink2_offset_y": {"type": "float", "label": "Ink 2 Y registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink2_phase_x": {"type": "float", "label": "Ink 2 phase X", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink2_phase_y": {"type": "float", "label": "Ink 2 phase Y", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink2_opacity": {"type": "float", "label": "Ink 2 opacity", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "hidden": True},
        "ink3_color": {"type": "color", "label": "Ink 3 colour", "default": "#FFF200", "hidden": True},
        "ink3_angle": {"type": "float", "label": "Ink 3 angle", "default": 0, "min": -180.0, "max": 180.0, "step": 1.0, "decimals": 1, "suffix": "°", "hidden": True},
        "ink3_offset_x": {"type": "float", "label": "Ink 3 X registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink3_offset_y": {"type": "float", "label": "Ink 3 Y registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink3_phase_x": {"type": "float", "label": "Ink 3 phase X", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink3_phase_y": {"type": "float", "label": "Ink 3 phase Y", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink3_opacity": {"type": "float", "label": "Ink 3 opacity", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "hidden": True},
        "ink4_color": {"type": "color", "label": "Ink 4 colour", "default": "#111111", "hidden": True},
        "ink4_angle": {"type": "float", "label": "Ink 4 angle", "default": 45, "min": -180.0, "max": 180.0, "step": 1.0, "decimals": 1, "suffix": "°", "hidden": True},
        "ink4_offset_x": {"type": "float", "label": "Ink 4 X registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink4_offset_y": {"type": "float", "label": "Ink 4 Y registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink4_phase_x": {"type": "float", "label": "Ink 4 phase X", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink4_phase_y": {"type": "float", "label": "Ink 4 phase Y", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink4_opacity": {"type": "float", "label": "Ink 4 opacity", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "hidden": True},
        "ink5_color": {"type": "color", "label": "Ink 5 colour", "default": "#6D597A", "hidden": True},
        "ink5_angle": {"type": "float", "label": "Ink 5 angle", "default": 22.5, "min": -180.0, "max": 180.0, "step": 1.0, "decimals": 1, "suffix": "°", "hidden": True},
        "ink5_offset_x": {"type": "float", "label": "Ink 5 X registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink5_offset_y": {"type": "float", "label": "Ink 5 Y registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink5_phase_x": {"type": "float", "label": "Ink 5 phase X", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink5_phase_y": {"type": "float", "label": "Ink 5 phase Y", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink5_opacity": {"type": "float", "label": "Ink 5 opacity", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "hidden": True},
        "ink6_color": {"type": "color", "label": "Ink 6 colour", "default": "#F2CC8F", "hidden": True},
        "ink6_angle": {"type": "float", "label": "Ink 6 angle", "default": 82.5, "min": -180.0, "max": 180.0, "step": 1.0, "decimals": 1, "suffix": "°", "hidden": True},
        "ink6_offset_x": {"type": "float", "label": "Ink 6 X registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink6_offset_y": {"type": "float", "label": "Ink 6 Y registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink6_phase_x": {"type": "float", "label": "Ink 6 phase X", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink6_phase_y": {"type": "float", "label": "Ink 6 phase Y", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink6_opacity": {"type": "float", "label": "Ink 6 opacity", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "hidden": True},
        "ink7_color": {"type": "color", "label": "Ink 7 colour", "default": "#457B9D", "hidden": True},
        "ink7_angle": {"type": "float", "label": "Ink 7 angle", "default": 7.5, "min": -180.0, "max": 180.0, "step": 1.0, "decimals": 1, "suffix": "°", "hidden": True},
        "ink7_offset_x": {"type": "float", "label": "Ink 7 X registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink7_offset_y": {"type": "float", "label": "Ink 7 Y registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink7_phase_x": {"type": "float", "label": "Ink 7 phase X", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink7_phase_y": {"type": "float", "label": "Ink 7 phase Y", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink7_opacity": {"type": "float", "label": "Ink 7 opacity", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "hidden": True},
        "ink8_color": {"type": "color", "label": "Ink 8 colour", "default": "#222222", "hidden": True},
        "ink8_angle": {"type": "float", "label": "Ink 8 angle", "default": 52.5, "min": -180.0, "max": 180.0, "step": 1.0, "decimals": 1, "suffix": "°", "hidden": True},
        "ink8_offset_x": {"type": "float", "label": "Ink 8 X registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink8_offset_y": {"type": "float", "label": "Ink 8 Y registration", "default": 0.0, "min": -128.0, "max": 128.0, "step": 0.25, "decimals": 2, "suffix": " px", "pixel_scaled": True, "hidden": True},
        "ink8_phase_x": {"type": "float", "label": "Ink 8 phase X", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink8_phase_y": {"type": "float", "label": "Ink 8 phase Y", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "decimals": 2, "hidden": True},
        "ink8_opacity": {"type": "float", "label": "Ink 8 opacity", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "hidden": True},
    }},
    "Dither": {"params": {
        "algorithm": {"type": "choice", "label": "Algorithm", "default": "Floyd-Steinberg", "options": ALGORITHMS},
        "mix": {"type": "float", "label": "Mix", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
        "strength": {"type": "float", "label": "Strength", "default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05, "decimals": 2, "animatable": True},
        "threshold": {"type": "float", "label": "Threshold", "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "serpentine": {"type": "bool", "label": "Serpentine", "default": True},
        "color_mix_pattern": {"type": "choice", "label": "1:1 pattern", "default": "Checker", "options": ["Checker", "Horizontal", "Vertical", "Bayer 2x2"]},
        "color_mix_distance": {"type": "choice", "label": "1:1 matching", "default": "OKLab", "options": ["OKLab", "RGB"]},
        "color_mix_phase": {"type": "int", "label": "1:1 phase", "default": 0, "min": 0, "max": 1, "step": 1, "animatable": True},
        "modulation_mode": {"type": "choice", "label": "Modulation mode", "default": "Smooth Diffuse", "options": list(MODULATION_MODES)},
        "modulation_scale": {"type": "float", "label": "Modulation scale", "default": 12.0, "min": 2.0, "max": 128.0, "step": 0.5, "decimals": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "modulation_phase": {"type": "float", "label": "Modulation phase", "default": 0.0, "min": 0.0, "max": 360.0, "step": 1.0, "decimals": 1, "suffix": "°", "animatable": True},
        "modulation_bias": {"type": "float", "label": "Modulation bias", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "modulation_detail": {"type": "float", "label": "Contour detail", "default": 0.55, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "modulation_seed": {"type": "int", "label": "Modulation seed", "default": 1, "min": 0, "max": 999999, "step": 1, "animatable": False},
        "bleed": {"type": "int", "label": "Bleed", "default": 0, "min": -10, "max": 10, "step": 1, "suffix": " px", "animatable": True, "pixel_scaled": True},
        "rounding": {"type": "float", "label": "Rounding", "default": 0.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "suffix": "%", "animatable": True},
        "sampling": {"type": "choice", "label": "Sampling", "default": "Native", "options": ["Native", "2× Supersampled"]},
        "custom_matrix_json": {"type": "text", "label": "Custom threshold matrix", "default": "[[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]", "hidden": True},
    }},
}

EFFECT_DESCRIPTIONS: dict[str, str] = {
    "Adjustments": "Adjust brightness, contrast, saturation, and gamma.",
    "Levels": "Remap black, midpoint, and white levels for precise tonal control.",
    "Local Contrast": "Boost local edge contrast to add clarity without globally sharpening the image.",
    "Hue Rotate": "Rotate image hues around the colour wheel.",
    "Tonal Map": "Map image luminance through configurable mono, duotone, tritone, or four-colour tonal anchors.",
    "Grayscale": "Convert the image to luminance-based grayscale.",
    "Invert": "Invert RGB colours for a photographic-negative look.",
    "Gaussian Blur": "Soften image detail with a smooth Gaussian blur.",
    "Median Denoise": "Remove speckle and impulse noise while preserving hard edges.",
    "Sharpen": "Increase local edge contrast to make image detail crisper.",
    "Glow": "Add a soft luminous halo around bright image detail.",
    "Bloom": "Spread bright highlights into a thresholded Screen or Add bloom.",
    "Vignette": "Darken or tint image edges with adjustable size, softness, roundness, centre, and colour.",
    "JPEG Compression": "Simulate lossy JPEG blocking, ringing, and compression damage.",
    "Chromatic Shift": "Offset colour channels to create chromatic misregistration.",
    "RGB Split": "Separate red, green, and blue channels into visible colour fringes.",
    "Posterize": "Reduce tonal precision into a smaller number of discrete colour levels.",
    "Scanlines": "Darken repeating horizontal rows to mimic scanned display lines.",
    "Interlace": "Emulate alternating video fields with configurable line treatment.",
    "Display Persistence": "Blend previous frames to emulate CRT, LCD, OLED, or generic display persistence.",
    "Chroma Bleed": "Smear colour horizontally like low-bandwidth composite video.",
    "Tracking Error": "Introduce VHS-style horizontal tracking displacement.",
    "Tape Dropout": "Create brief missing or damaged tape streaks and gaps.",
    "Temporal Jitter": "Shift frames over time to mimic unstable analog playback.",
    "Head Switching Noise": "Add noisy lower-frame distortion like VHS head-switching interference.",
    "RGB Convergence": "Misalign RGB phosphor channels to simulate imperfect CRT convergence.",
    "CRT Mask": "Overlay aperture-grille, shadow-mask, or slot-mask phosphor structure.",
    "Phosphor Glow": "Simulate light spreading from bright CRT phosphors.",
    "Beam Width": "Change CRT beam thickness to soften or broaden scanned lines.",
    "Horizontal Bloom": "Stretch bright areas horizontally like overloaded CRT electronics.",
    "Scanline Variation": "Vary scanline intensity across the frame for less uniform CRT texture.",
    "CRT Curvature": "Warp the image toward the curved surface of a CRT tube.",
    "Edge Distortion": "Distort image geometry more strongly near the screen edges.",
    "Vertical Sync Roll": "Roll or offset the frame vertically like lost vertical synchronization.",
    "Field Flicker": "Alternate field brightness over time to simulate interlaced flicker.",
    "LCD Inversion": "Add LCD polarity and inversion patterns for early flat-panel artifacts.",
    "Dot Crawl": "Create moving edge patterns from composite luma/chroma interference.",
    "Composite Noise": "Add analog composite-video noise and signal texture.",
    "RF Interference": "Add broad-band RF/static interference and signal waviness.",
    "Horizontal Tear": "Split horizontal bands sideways to simulate sync or tape tearing.",
    "Noise": "Add configurable monochrome or coloured random noise.",
    "Temporal Flicker": "Animate frame brightness for irregular or periodic flicker.",
    "Temporal Pattern": "Generate animated waves, pulses, sweeps, and drifting temporal patterns.",
    "Pixel Aspect Ratio": "Rescale presentation geometry for non-square display pixels.",
    "Pixelate": "Reduce spatial resolution into enlarged block pixels.",
    "Pixel Art Cleanup": "Clean isolated pixels, tiny clusters, stair-steps, and line artifacts while preserving edges.",
    "Pixel Sort": "Sort pixels by brightness or colour to create stretched glitch streaks.",
    "Screen Melt": "Pull image regions into long melting streaks.",
    "Block Shuffle": "Rearrange rectangular image blocks for scrambled mosaic glitches.",
    "Pixel Scatter": "Displace individual pixels randomly for fragmented digital noise.",
    "Data Shift": "Shift image data in chunks to create digital displacement bands.",
    "Row Shift": "Offset individual image rows horizontally.",
    "Column Shift": "Offset individual image columns vertically.",
    "Cellular Automata": "Evolve a cellular pattern from image structure for generative pixel textures.",
    "Databend": "Simulate corrupted image-data decoding with displaced and broken regions.",
    "Channel Swap": "Reorder RGB channels for alternate colour mappings.",
    "Pixel Material": "Render pixels as stylized cells such as dots, CRT phosphors, LEDs, beads, or tiles.",
    "Text Overlay": "Render a legacy editable text overlay retained for older projects and presets.",
    "ASCII / Glyph": "Rebuild image detail using character glyphs selected by brightness or structure.",
    "Pixel Text": "Place editable pixel-aligned text with font, outline, shadow, and layout controls.",
    "Text Pattern": "Repeat text across the image as a configurable pattern.",
    "Text Mask": "Use rendered text as a mask to reveal or suppress image regions.",
    "Wave / Jitter Text": "Distort rendered text positions with waves and jitter.",
    "Typewriter Text": "Animate text appearing progressively like a typewriter.",
    "Text Glitch": "Corrupt and displace rendered text for digital glitch effects.",
    "Dither Glow": "Add configurable glow to the structure of a dithered image.",
    "Hardware Limits": "Apply strict image-space limits from a selected hardware profile.",
    "Hardware Display": "Apply the display or presentation treatment from a selected hardware profile.",
    "Pop Tone": "Create manga and pop-art dot screening with controllable density and variation.",
    "Polygon Dither": "Rebuild image regions as triangle, pentagon, hexagon, or low-poly cells.",
    "Beehive": "Quantize the image through an integral honeycomb or hex-cell raster.",
    "Print Lab": "Build independent mono, CMYK, RGB, or spot-colour AM halftone separations.",
    "Dither": "Map colours to the active palette using quantization, ordered, diffusion, or modulation algorithms.",
}

EFFECT_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Color & Tone", (
        "Adjustments", "Levels", "Local Contrast", "Tonal Map", "Posterize", "Grayscale", "Hue Rotate", "Invert",
    )),
    ("Detail & Light", (
        "Median Denoise", "Gaussian Blur", "Sharpen", "Glow", "Bloom", "Vignette",
    )),
    ("Pixel & Dither", (
        "Pixelate", "Pixel Art Cleanup", "Pixel Material", "Dither", "Pop Tone", "Polygon Dither", "Beehive", "Dither Glow",
    )),
    ("Print Lab", (
        "Print Lab",
    )),
    ("Text & Overlay", (
        "Pixel Text", "Text Pattern", "Text Mask", "Wave / Jitter Text", "Typewriter Text", "Text Glitch", "ASCII / Glyph",
    )),
    ("Noise & Motion", (
        "Noise", "Temporal Flicker", "Temporal Pattern", "Cellular Automata",
    )),
    ("Channels & Color Glitch", (
        "Chromatic Shift", "RGB Split", "Channel Swap",
    )),
    ("Pixel & Data Glitch", (
        "Row Shift", "Column Shift", "Pixel Scatter", "Pixel Sort", "Block Shuffle", "Data Shift", "Databend", "Screen Melt",
    )),
    ("Display Geometry & Response", (
        "Pixel Aspect Ratio", "CRT Curvature", "Edge Distortion", "Display Persistence", "LCD Inversion",
    )),
    ("CRT & Scan", (
        "Scanlines", "Scanline Variation", "Interlace", "Field Flicker", "CRT Mask", "RGB Convergence", "Beam Width", "Phosphor Glow", "Horizontal Bloom",
    )),
    ("Analog Signal", (
        "Chroma Bleed", "Dot Crawl", "Composite Noise", "RF Interference", "Vertical Sync Roll",
    )),
    ("Tape & Compression", (
        "Tracking Error", "Tape Dropout", "Head Switching Noise", "Horizontal Tear", "Temporal Jitter", "JPEG Compression",
    )),
    ("Hardware Stages", (
        "Hardware Limits", "Hardware Display",
    )),
)


FIXED_STAGE_KINDS = frozenset({"Hardware Limits", "Hardware Display"})
_FIXED_STAGE_ORDER = {"Hardware Limits": 0, "Hardware Display": 1}


# Text Overlay is retained as a legacy effect so old projects/presets render
# exactly as before. Pixel Text is its feature-complete replacement in the
# add-effect UI (font, alignment, wrapping, spacing, rotation, outline/shadow).
_HIDDEN_EFFECT_KINDS = frozenset({"Text Overlay"})


def effect_categories() -> list[dict[str, object]]:
    """Return effect categories for the add-layer UI.

    Any future effect that has not been assigned yet is kept reachable in an
    automatic Other category instead of silently disappearing from the UI.
    """
    grouped: list[dict[str, object]] = []
    seen: set[str] = set(_HIDDEN_EFFECT_KINDS)
    for name, kinds in EFFECT_CATEGORIES:
        available = [kind for kind in kinds if kind in EFFECT_DEFINITIONS and kind not in _HIDDEN_EFFECT_KINDS]
        if available:
            grouped.append({
                "name": name,
                "effects": available,
                "descriptions": {kind: EFFECT_DESCRIPTIONS.get(kind, "") for kind in available},
            })
            seen.update(available)
    uncategorized = [kind for kind in EFFECT_DEFINITIONS if kind not in seen]
    if uncategorized:
        grouped.append({
            "name": "Other",
            "effects": uncategorized,
            "descriptions": {kind: EFFECT_DESCRIPTIONS.get(kind, "") for kind in uncategorized},
        })
    return grouped


# Numeric effect controls are animatable unless they are identity/random seeds.
# This keeps the timeline capability aligned with the effect schema without
# requiring a second hand-maintained list of motion-capable parameters.
for _definition in EFFECT_DEFINITIONS.values():
    for _param_name, _spec in _definition.get("params", {}).items():
        if _spec.get("type") in {"int", "float", "duration"} and _param_name != "seed":
            _spec.setdefault("animatable", True)


def new_effect(kind: str, *, enabled: bool = True, effect_id: str | None = None) -> dict[str, Any]:
    if kind not in EFFECT_DEFINITIONS:
        raise ValueError(f"Unknown effect type: {kind}")
    params = {key: deepcopy(spec.get("default")) for key, spec in EFFECT_DEFINITIONS[kind]["params"].items()}
    return {
        "id": effect_id or uuid4().hex[:12],
        "kind": kind,
        "enabled": bool(enabled),
        "opacity": 1.0,
        "blend_mode": "Normal",
        "mask": default_layer_mask(),
        "group_id": "",
        "params": params,
    }


def default_effect_stack(settings: Any | None = None) -> list[dict[str, Any]]:
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
        # The pre-family Modulation algorithm was a sine-based screen. Legacy
        # scalar settings therefore map to the closest new mode instead of
        # silently changing appearance to Smooth Diffuse.
        if dither["params"]["algorithm"] == "Modulation":
            dither["params"]["modulation_mode"] = "Sine Wave Modulation"
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
        try:
            step["opacity"] = max(0.0, min(1.0, float(raw.get("opacity", 1.0))))
        except (TypeError, ValueError):
            step["opacity"] = 1.0
        blend_mode = str(raw.get("blend_mode", "Normal") or "Normal")
        step["blend_mode"] = blend_mode if blend_mode in BLEND_MODES else "Normal"
        raw_mask = raw.get("mask") if isinstance(raw.get("mask"), dict) else {}
        mask_type = str(raw_mask.get("type", "None") or "None")
        if mask_type not in MASK_TYPES:
            mask_type = "None"
        try:
            mask_feather = max(0.0, min(1.0, float(raw_mask.get("feather", 0.0))))
        except (TypeError, ValueError):
            mask_feather = 0.0
        try:
            mask_strength = max(0.0, min(1.0, float(raw_mask.get("strength", 1.0))))
        except (TypeError, ValueError):
            mask_strength = 1.0
        step["mask"] = {
            "type": mask_type,
            "invert": bool(raw_mask.get("invert", False)),
            "feather": mask_feather,
            "strength": mask_strength,
        }
        step["group_id"] = str(raw.get("group_id", "") or "")
        raw_params = raw.get("params", {}) if isinstance(raw.get("params"), dict) else {}
        # Existing 0.6.0-and-earlier Modulation layers had no mode selector and
        # used a sine carrier. Preserve that look when opening old projects or
        # presets while new Modulation layers default to Smooth Diffuse.
        if kind == "Dither" and str(raw_params.get("algorithm", "")) == "Modulation" and "modulation_mode" not in raw_params:
            step["params"]["modulation_mode"] = "Sine Wave Modulation"
        for key, spec in EFFECT_DEFINITIONS[kind]["params"].items():
            if key not in raw_params:
                continue
            value = raw_params[key]
            ptype = spec.get("type")
            try:
                if ptype == "int":
                    value = max(int(spec["min"]), min(int(spec["max"]), int(round(float(value)))))
                elif ptype in {"float", "duration"}:
                    value = max(float(spec["min"]), min(float(spec["max"]), float(value)))
                elif ptype == "bool":
                    value = bool(value)
                elif ptype == "choice":
                    options = [str(v) for v in spec.get("options", [])]
                    value = str(value)
                    if options and value not in options:
                        value = str(spec.get("default", options[0]))
                elif ptype in {"text", "file", "glyph_set"}:
                    value = str(value)
                elif ptype == "color":
                    text = str(value).strip().upper()
                    hex_to_rgb(text)
                    value = text if text.startswith("#") else f"#{text}"
            except (TypeError, ValueError):
                value = deepcopy(spec.get("default"))
            step["params"][key] = value
        normalized.append(step)
    if not normalized:
        return default_effect_stack(settings)
    regular = [step for step in normalized if step.get("kind") not in FIXED_STAGE_KINDS]
    staged = [step for step in normalized if step.get("kind") in FIXED_STAGE_KINDS]
    staged.sort(key=lambda step: _FIXED_STAGE_ORDER.get(str(step.get("kind")), 99))
    return regular + staged


def scale_normalized_stack_for_preview(stack: list[dict[str, Any]], scale: float) -> list[dict[str, Any]]:
    """Scale an already-normalized stack without validating it a second time."""
    result = deepcopy(stack)
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


def scale_stack_for_preview(stack: list[dict[str, Any]], scale: float) -> list[dict[str, Any]]:
    return scale_normalized_stack_for_preview(normalize_effect_stack(stack), scale)


def animatable_targets(stack: list[dict[str, Any]]) -> list[tuple[str, str, float]]:
    targets: list[tuple[str, str, float]] = []
    for step in normalize_effect_stack(stack):
        targets.append((f"effect:{step['id']}:__opacity__", f"{step['kind']} · Opacity", float(step.get("opacity", 1.0))))
        definition = EFFECT_DEFINITIONS.get(step["kind"], {})
        for key, spec in definition.get("params", {}).items():
            if not spec.get("animatable"):
                continue
            value = step["params"].get(key, spec.get("default", 0.0))
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                targets.append((f"effect:{step['id']}:{key}", f"{step['kind']} · {spec.get('label', key)}", float(value)))
    return targets
