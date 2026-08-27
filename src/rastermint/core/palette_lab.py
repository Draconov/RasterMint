# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import colorsys
from typing import Any

import numpy as np
from PIL import Image

from .color_utils import hex_to_rgb


def _srgb8_to_oklab(values: np.ndarray) -> np.ndarray:
    rgb = np.asarray(values, dtype=np.float32) / 255.0
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    r, g, b = linear[..., 0], linear[..., 1], linear[..., 2]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack(
        (
            0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
        ),
        axis=-1,
    ).astype(np.float32)


def palette_rgb(colors: list[str]) -> np.ndarray:
    return np.asarray([hex_to_rgb(str(color)) for color in colors], dtype=np.float32)


def sort_palette(colors: list[str], mode: str) -> list[str]:
    if not colors:
        return []
    mode_key = str(mode or "Luminance").strip().casefold()
    records: list[tuple[float, float, float, int, str]] = []
    for index, color in enumerate(colors):
        r, g, b = hex_to_rgb(color)
        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
        h, s, v = colorsys.rgb_to_hsv(rf, gf, bf)
        lum = 0.2126 * rf + 0.7152 * gf + 0.0722 * bf
        if mode_key.startswith("hue"):
            key = (h, s, lum)
        elif mode_key.startswith("sat"):
            key = (s, h, lum)
        elif mode_key.startswith("value") or mode_key.startswith("bright"):
            key = (v, h, s)
        else:
            key = (lum, h, s)
        records.append((key[0], key[1], key[2], index, str(color).upper()))
    records.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return [item[4] for item in records]


def _sample_pixels(image: Image.Image | None, max_pixels: int = 100_000) -> np.ndarray:
    if image is None:
        return np.empty((0, 3), dtype=np.float32)
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8).reshape(-1, 3)
    if arr.shape[0] <= max_pixels:
        return arr.astype(np.float32)
    # Evenly-spaced deterministic sampling avoids changing analysis every refresh.
    indices = np.linspace(0, arr.shape[0] - 1, max_pixels, dtype=np.int64)
    return arr[indices].astype(np.float32)


def palette_analysis(colors: list[str], image: Image.Image | None = None, max_pixels: int = 100_000) -> dict[str, Any]:
    if not colors:
        return {
            "colors": [], "closest_pairs": [], "near_duplicates": [], "ramps": [],
            "distance_matrix": [], "suggested_count": 0, "unused_count": 0,
        }

    rgb = palette_rgb(colors)
    lab = _srgb8_to_oklab(rgb)
    count = len(colors)
    usage = np.zeros(count, dtype=np.int64)
    samples = _sample_pixels(image, max_pixels=max_pixels)
    if samples.size:
        # Bounded chunks avoid a potentially huge samples × palette matrix.
        for start in range(0, samples.shape[0], 8192):
            chunk = samples[start : start + 8192]
            # RGB distance is intentionally used for usage assignment so the
            # histogram matches RasterMint's nearest-palette quantizer closely.
            dist = np.sum((chunk[:, None, :] - rgb[None, :, :]) ** 2, axis=2)
            indices = np.argmin(dist, axis=1)
            usage += np.bincount(indices, minlength=count)

    total = int(usage.sum())
    records: list[dict[str, Any]] = []
    for index, color in enumerate(colors):
        r, g, b = [float(v) / 255.0 for v in rgb[index]]
        hue, saturation, value = colorsys.rgb_to_hsv(r, g, b)
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        records.append({
            "index": index,
            "color": str(color).upper(),
            "luminance": round(luminance, 5),
            "hue": round(hue * 360.0, 2),
            "saturation": round(saturation, 5),
            "value": round(value, 5),
            "usage": int(usage[index]),
            "percent": round((100.0 * usage[index] / total) if total else 0.0, 3),
            "unused": bool(total and usage[index] == 0),
        })

    diff = lab[:, None, :] - lab[None, :, :]
    distances = np.sqrt(np.sum(diff * diff, axis=2))
    pairs: list[dict[str, Any]] = []
    for i in range(count):
        for j in range(i + 1, count):
            pairs.append({
                "a": i,
                "b": j,
                "color_a": str(colors[i]).upper(),
                "color_b": str(colors[j]).upper(),
                "distance": round(float(distances[i, j]), 5),
            })
    pairs.sort(key=lambda item: (float(item["distance"]), int(item["a"]), int(item["b"])))
    closest = pairs[: min(24, len(pairs))]
    near = [item for item in pairs if float(item["distance"]) < 0.035]

    # Ramp detection: group moderately-saturated colours by broad hue family,
    # then order each family dark→light. Neutral colours form their own ramp.
    buckets: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        sat = float(record["saturation"])
        hue = float(record["hue"])
        if sat < 0.12:
            bucket = "Neutral"
        else:
            names = ("Red", "Orange", "Yellow", "Green", "Cyan", "Blue", "Violet", "Magenta")
            bucket = names[int(((hue + 22.5) % 360.0) // 45.0) % len(names)]
        buckets.setdefault(bucket, []).append(record)
    ramps: list[dict[str, Any]] = []
    for name, bucket in buckets.items():
        if len(bucket) < 2:
            continue
        ordered = sorted(bucket, key=lambda item: (float(item["luminance"]), int(item["index"])))
        ramps.append({"name": name, "indices": [int(item["index"]) for item in ordered], "colors": [str(item["color"]) for item in ordered]})
    ramps.sort(key=lambda item: (-len(item["indices"]), str(item["name"])))

    unused_count = sum(1 for record in records if bool(record["unused"]))
    near_duplicate_remove = {int(item["b"]) for item in near}
    low_usage = set()
    if total:
        threshold = max(1, int(round(total * 0.001)))
        low_usage = {index for index, value in enumerate(usage) if int(value) <= threshold}
    suggested_count = max(2 if count >= 2 else 1, count - len(near_duplicate_remove | low_usage))

    # A full distance matrix is useful for small palettes. Limit the visualizer
    # to 32 colours so QML does not receive tens of thousands of cells.
    matrix_limit = min(count, 32)
    matrix = [[round(float(distances[y, x]), 4) for x in range(matrix_limit)] for y in range(matrix_limit)]
    return {
        "colors": records,
        "closest_pairs": closest,
        "near_duplicates": near[:64],
        "ramps": ramps,
        "distance_matrix": matrix,
        "distance_matrix_colors": [str(color).upper() for color in colors[:matrix_limit]],
        "suggested_count": int(suggested_count),
        "unused_count": int(unused_count),
        "sample_count": int(total),
    }


def palette_mapping(source_colors: list[str], target_colors: list[str]) -> list[dict[str, Any]]:
    if not source_colors or not target_colors:
        return []
    source = palette_rgb(source_colors)
    target = palette_rgb(target_colors)
    source_lab = _srgb8_to_oklab(source)
    target_lab = _srgb8_to_oklab(target)
    distances = np.sqrt(np.sum((source_lab[:, None, :] - target_lab[None, :, :]) ** 2, axis=2))
    nearest = np.argmin(distances, axis=1)
    return [
        {
            "source_index": index,
            "source": str(source_colors[index]).upper(),
            "target_index": int(nearest[index]),
            "target": str(target_colors[int(nearest[index])]).upper(),
            "distance": round(float(distances[index, int(nearest[index])]), 5),
        }
        for index in range(len(source_colors))
    ]
