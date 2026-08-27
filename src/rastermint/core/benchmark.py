# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from time import perf_counter
from typing import Any

from PIL import Image

from .effect_stack import apply_normalized_effect_stack
from .processor import prepare_raster_source, runtime_effect_stack
from .settings import ProcessingSettings


def benchmark_processing(image: Image.Image, settings: ProcessingSettings) -> dict[str, Any]:
    """Benchmark the current prepared raster and each enabled layer once.

    The benchmark intentionally disables caching and tiled processing so the
    numbers represent the actual cost of rebuilding the stack. It is aimed at
    interactive diagnostics, not synthetic micro-benchmarking.
    """
    source_start = perf_counter()
    source = prepare_raster_source(image, settings)
    source_ms = (perf_counter() - source_start) * 1000.0
    stack = runtime_effect_stack(settings)

    current = source
    rows: list[dict[str, Any]] = []
    stack_start = perf_counter()
    for step in stack:
        if not bool(step.get("enabled", True)):
            continue
        started = perf_counter()
        current = apply_normalized_effect_stack(
            current,
            [step],
            settings.palette,
            frame_time=0.0,
            frame_index=0,
        )
        elapsed = (perf_counter() - started) * 1000.0
        rows.append({
            "id": str(step.get("id", "")),
            "kind": str(step.get("kind", "Layer")),
            "milliseconds": round(elapsed, 3),
        })
    stack_ms = (perf_counter() - stack_start) * 1000.0
    rows.sort(key=lambda item: float(item["milliseconds"]), reverse=True)
    return {
        "source_ms": round(source_ms, 3),
        "stack_ms": round(stack_ms, 3),
        "total_ms": round(source_ms + stack_ms, 3),
        "width": int(current.width),
        "height": int(current.height),
        "layers": rows,
    }
