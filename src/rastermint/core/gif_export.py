# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable

import numpy as np
from PIL import Image

from .animation import settings_at_time
from .media import export_processed_gif, iter_video_frames
from .processor import process_image
from .settings import ProcessingSettings


def _ffmpeg_executable() -> str:
    try:
        import imageio_ffmpeg  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Video/GIF export requires imageio-ffmpeg") from exc
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run_ffmpeg(command: list[str], description: str) -> None:
    completed = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return

    detail = (completed.stderr or "").strip().splitlines()
    tail = "\n".join(detail[-8:])
    raise RuntimeError(
        f"{description} failed"
        + (f":\n{tail}" if tail else ".")
    )


def export_processed_video_gif(
    source_path: str | Path,
    settings: ProcessingSettings,
    output: str | Path,
    *,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Export any supported video source as a processed animated GIF.

    Existing GIF sources use RasterMint's duration-preserving GIF path. Other
    video formats are processed frame-by-frame into temporary lossless PNGs and
    encoded with the bundled FFmpeg using a generated 256-color palette.
    """

    source = Path(source_path)
    target = Path(output)
    if target.suffix.lower() != ".gif":
        target = target.with_suffix(".gif")
    target.parent.mkdir(parents=True, exist_ok=True)

    if source.suffix.lower() == ".gif":
        return export_processed_gif(source, settings, target, progress=progress)

    meta, frames = iter_video_frames(source)
    source_w, source_h = meta["size"]
    fps = max(1.0, float(meta.get("fps") or 25.0))
    duration = max(0.0, float(meta.get("duration") or 0.0))
    total = max(1, int(round(duration * fps)))

    temp_dir = Path(tempfile.mkdtemp(prefix="rastermint-gif-"))
    try:
        frame_count = 0
        for index, raw in enumerate(frames):
            arr = np.frombuffer(raw, dtype=np.uint8).reshape(
                int(source_h), int(source_w), 3
            )
            source_frame = Image.fromarray(arr.copy(), "RGB")
            t = index / fps
            animated = settings_at_time(settings, t)
            result = process_image(
                source_frame,
                animated,
                frame_time=t,
                frame_index=index,
                display_mode=(
                    animated.display_mode if animated.display_export else "raw"
                ),
                include_grid=animated.grid_enabled and animated.grid_export,
            )
            frame_path = temp_dir / f"frame_{index:08d}.png"
            result.save(frame_path, format="PNG", optimize=False)
            frame_count += 1
            if progress:
                progress(index + 1, total)

        if frame_count == 0:
            raise RuntimeError("Video contains no decodable frames")

        ffmpeg = _ffmpeg_executable()
        pattern = str(temp_dir / "frame_%08d.png")
        palette = temp_dir / "palette.png"

        _run_ffmpeg(
            [
                ffmpeg,
                "-y",
                "-framerate",
                f"{fps:.8f}",
                "-start_number",
                "0",
                "-i",
                pattern,
                "-vf",
                "palettegen=max_colors=256:stats_mode=diff",
                str(palette),
            ],
            "GIF palette generation",
        )

        _run_ffmpeg(
            [
                ffmpeg,
                "-y",
                "-framerate",
                f"{fps:.8f}",
                "-start_number",
                "0",
                "-i",
                pattern,
                "-i",
                str(palette),
                "-lavfi",
                "paletteuse=dither=sierra2_4a:diff_mode=rectangle",
                "-loop",
                "0",
                str(target),
            ],
            "GIF encoding",
        )

        if not target.exists():
            raise RuntimeError("GIF encoding completed without creating a file")
        return target
    finally:
        try:
            frames.close()  # type: ignore[attr-defined]
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)
