# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from .color_utils import hex_to_rgb
from .dither_metadata import ALGORITHMS

# The UI consumes this schema directly. Keeping effect metadata in the core means
# adding a new effect does not require hard-coding another form in the QML UI.
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
    "Noise": {"params": {
        "amount": {"type": "float", "label": "Amount", "default": 12.0, "min": 0.0, "max": 100.0, "step": 1.0, "decimals": 1, "animatable": True},
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
    "Dither": {"params": {
        "algorithm": {"type": "choice", "label": "Algorithm", "default": "Floyd-Steinberg", "options": ALGORITHMS},
        "mix": {"type": "float", "label": "Mix", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05, "decimals": 2, "animatable": True},
        "strength": {"type": "float", "label": "Strength", "default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05, "decimals": 2, "animatable": True},
        "threshold": {"type": "float", "label": "Threshold", "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2, "animatable": True},
        "serpentine": {"type": "bool", "label": "Serpentine", "default": True},
        "color_mix_pattern": {"type": "choice", "label": "1:1 pattern", "default": "Checker", "options": ["Checker", "Horizontal", "Vertical", "Bayer 2x2"]},
        "color_mix_distance": {"type": "choice", "label": "1:1 matching", "default": "OKLab", "options": ["OKLab", "RGB"]},
        "color_mix_phase": {"type": "int", "label": "1:1 phase", "default": 0, "min": 0, "max": 1, "step": 1, "animatable": True},
    }},
}

EFFECT_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Color & Tone", (
        "Adjustments", "Levels", "Local Contrast", "Hue Rotate", "Grayscale", "Invert", "Posterize",
    )),
    ("Detail & Light", (
        "Gaussian Blur", "Median Denoise", "Sharpen", "Glow", "Bloom",
    )),
    ("Pixel & Dither", (
        "Pixelate", "Dither", "Dither Glow", "Pixel Material",
    )),
    ("Hardware Stages", (
        "Hardware Limits", "Hardware Display",
    )),
    ("Display & Analog", (
        "Pixel Aspect Ratio", "Scanlines", "Interlace", "JPEG Compression",
    )),
    ("Glitch & Channels", (
        "Chromatic Shift", "RGB Split", "Pixel Sort", "Screen Melt", "Block Shuffle",
        "Pixel Scatter", "Data Shift", "Row Shift", "Column Shift", "Databend", "Channel Swap",
    )),
    ("Noise & Motion", (
        "Noise", "Temporal Flicker", "Temporal Pattern", "Cellular Automata",
    )),
    ("Text & Overlay", (
        "Pixel Text", "Text Pattern", "Text Mask",
        "Wave / Jitter Text", "Typewriter Text", "Text Glitch", "ASCII / Glyph",
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
            grouped.append({"name": name, "effects": available})
            seen.update(available)
    uncategorized = [kind for kind in EFFECT_DEFINITIONS if kind not in seen]
    if uncategorized:
        grouped.append({"name": "Other", "effects": uncategorized})
    return grouped


# Numeric effect controls are animatable unless they are identity/random seeds.
# This keeps the timeline capability aligned with the effect schema without
# requiring a second hand-maintained list of motion-capable parameters.
for _definition in EFFECT_DEFINITIONS.values():
    for _param_name, _spec in _definition.get("params", {}).items():
        if _spec.get("type") in {"int", "float"} and _param_name != "seed":
            _spec.setdefault("animatable", True)


def new_effect(kind: str, *, enabled: bool = True, effect_id: str | None = None) -> dict[str, Any]:
    if kind not in EFFECT_DEFINITIONS:
        raise ValueError(f"Unknown effect type: {kind}")
    params = {key: deepcopy(spec.get("default")) for key, spec in EFFECT_DEFINITIONS[kind]["params"].items()}
    return {"id": effect_id or uuid4().hex[:12], "kind": kind, "enabled": bool(enabled), "params": params}


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
        raw_params = raw.get("params", {}) if isinstance(raw.get("params"), dict) else {}
        for key, spec in EFFECT_DEFINITIONS[kind]["params"].items():
            if key not in raw_params:
                continue
            value = raw_params[key]
            ptype = spec.get("type")
            try:
                if ptype == "int":
                    value = max(int(spec["min"]), min(int(spec["max"]), int(round(float(value)))))
                elif ptype == "float":
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
        definition = EFFECT_DEFINITIONS.get(step["kind"], {})
        for key, spec in definition.get("params", {}).items():
            if not spec.get("animatable"):
                continue
            value = step["params"].get(key, spec.get("default", 0.0))
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                targets.append((f"effect:{step['id']}:{key}", f"{step['kind']} · {spec.get('label', key)}", float(value)))
    return targets
