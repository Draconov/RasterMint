# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from PIL import Image

from .processor import process_image
from .settings import ProcessingSettings


def process_batch(
    paths: Iterable[str | Path],
    output_dir: str | Path,
    settings: ProcessingSettings,
    *,
    progress: Callable[[int, int, Path], None] | None = None,
) -> list[Path]:
    inputs = [Path(p) for p in paths]
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    total = len(inputs)
    for index, path in enumerate(inputs, start=1):
        with Image.open(path) as source:
            result = process_image(source.convert("RGB"), settings, display_mode=settings.display_mode if settings.display_export else "raw", include_grid=settings.grid_enabled and settings.grid_export)
        target = destination / f"{path.stem}-rastermint.png"
        result.save(target)
        written.append(target)
        if progress:
            progress(index, total, target)
    return written
