# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable, Iterator

import numpy as np
from PIL import Image

from .animation import settings_at_time
from .processor import process_image
from .settings import ProcessingSettings

SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".gif"}
ANIMATED_IMAGE_SUFFIXES = {".gif"}


@dataclass(frozen=True, slots=True)
class VideoInfo:
    width: int
    height: int
    fps: float
    duration: float
    frames: int



def _gif_frame_durations(path: str | Path) -> tuple[list[int], tuple[int, int]]:
    durations: list[int] = []
    with Image.open(path) as img:
        size = img.size
        count = int(getattr(img, "n_frames", 1))
        for index in range(count):
            img.seek(index)
            durations.append(max(10, int(img.info.get("duration", 100) or 100)))
    return durations, size


def _probe_gif(path: str | Path) -> VideoInfo:
    durations, size = _gif_frame_durations(path)
    duration = sum(durations) / 1000.0
    frames = len(durations)
    fps = frames / duration if duration > 0 else 10.0
    return VideoInfo(size[0], size[1], fps, duration, frames)


def _read_gif_frame(path: str | Path, time_seconds: float = 0.0) -> Image.Image:
    durations, _ = _gif_frame_durations(path)
    if not durations:
        raise RuntimeError("GIF has no frames")
    total_ms = max(1, sum(durations))
    target_ms = min(total_ms - 1, int(max(0.0, float(time_seconds)) * 1000.0))
    elapsed = 0
    frame_index = 0
    for i, duration in enumerate(durations):
        if target_ms < elapsed + duration:
            frame_index = i
            break
        elapsed += duration
    with Image.open(path) as img:
        img.seek(frame_index)
        return img.convert("RGB").copy()


class _GifByteIterator:
    def __init__(self, path: str | Path) -> None:
        self._image = Image.open(path)
        self._count = int(getattr(self._image, "n_frames", 1))
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self) -> bytes:
        if self._index >= self._count:
            self.close()
            raise StopIteration
        self._image.seek(self._index)
        frame = self._image.convert("RGB")
        self._index += 1
        return np.asarray(frame, dtype=np.uint8).tobytes()

    def close(self) -> None:
        if self._image is not None:
            try:
                self._image.close()
            finally:
                self._image = None  # type: ignore[assignment]


def _iter_gif_frames(path: str | Path) -> tuple[dict, Iterator[bytes]]:
    info = _probe_gif(path)
    meta = {"size": (info.width, info.height), "fps": info.fps, "duration": info.duration}
    return meta, _GifByteIterator(path)

def _imageio_ffmpeg():
    try:
        import imageio_ffmpeg  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError("Video support requires imageio-ffmpeg") from exc
    return imageio_ffmpeg


def video_support_available() -> bool:
    try:
        _imageio_ffmpeg().get_ffmpeg_exe()
        return True
    except Exception:
        return False


def probe_video(path: str | Path) -> VideoInfo:
    if Path(path).suffix.lower() == ".gif":
        return _probe_gif(path)
    ff = _imageio_ffmpeg()
    generator = ff.read_frames(str(path), pix_fmt="rgb24")
    try:
        meta = next(generator)
    finally:
        generator.close()
    width, height = meta.get("size", (0, 0))
    fps = float(meta.get("fps") or 25.0)
    duration = float(meta.get("duration") or 0.0)
    frames = int(round(duration * fps)) if duration > 0 else 0
    if not width or not height:
        raise RuntimeError("Could not determine video dimensions")
    return VideoInfo(int(width), int(height), fps, duration, frames)


def read_video_frame(path: str | Path, time_seconds: float = 0.0) -> Image.Image:
    if Path(path).suffix.lower() == ".gif":
        return _read_gif_frame(path, time_seconds)
    ff = _imageio_ffmpeg()
    params = ["-ss", f"{max(0.0, float(time_seconds)):.6f}"] if time_seconds > 0 else []
    generator = ff.read_frames(
        str(path),
        pix_fmt="rgb24",
        input_params=params,
        output_params=["-frames:v", "1"],
    )
    try:
        meta = next(generator)
        frame = next(generator)
    except StopIteration as exc:
        raise RuntimeError("Could not decode video frame") from exc
    finally:
        generator.close()
    width, height = meta["size"]
    arr = np.frombuffer(frame, dtype=np.uint8).reshape(int(height), int(width), 3)
    return Image.fromarray(arr.copy(), "RGB")


def iter_video_frames(path: str | Path) -> tuple[dict, Iterator[bytes]]:
    if Path(path).suffix.lower() == ".gif":
        return _iter_gif_frames(path)
    ff = _imageio_ffmpeg()
    generator = ff.read_frames(str(path), pix_fmt="rgb24")
    meta = next(generator)
    return meta, generator


def _prepare_h264_frame(image: Image.Image) -> Image.Image:
    """Pad odd dimensions by one edge pixel for widely compatible yuv420p H.264."""
    rgb = image.convert("RGB")
    w, h = rgb.size
    pad_w = w & 1
    pad_h = h & 1
    if not pad_w and not pad_h:
        return rgb
    arr = np.asarray(rgb, dtype=np.uint8)
    padded = np.pad(arr, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
    return Image.fromarray(padded, "RGB")


def _open_mp4_writer(path: str | Path, size: tuple[int, int], fps: float):
    ff = _imageio_ffmpeg()
    writer = ff.write_frames(
        str(path),
        size,
        fps=max(1.0, float(fps)),
        codec="libx264",
        pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p",
        macro_block_size=1,
        output_params=["-movflags", "+faststart", "-crf", "18"],
    )
    writer.send(None)
    return writer


def _mux_source_audio(video_only: Path, source: Path, output: Path) -> bool:
    ff = _imageio_ffmpeg()
    command = [
        ff.get_ffmpeg_exe(), "-y",
        "-i", str(video_only),
        "-i", str(source),
        "-map", "0:v:0",
        "-map", "1:a?",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output),
    ]
    completed = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return completed.returncode == 0 and output.exists()


def export_image_animation(
    image: Image.Image,
    settings: ProcessingSettings,
    output: str | Path,
    *,
    duration: float | None = None,
    fps: int | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    target = Path(output)
    duration = max(0.1, float(duration if duration is not None else settings.animation_duration))
    fps = max(1, int(fps if fps is not None else settings.animation_fps))
    frame_count = max(1, int(round(duration * fps)))

    if target.suffix.lower() == ".gif":
        frames: list[Image.Image] = []
        for index in range(frame_count):
            t = index / fps
            animated = settings_at_time(settings, t)
            frame = process_image(image, animated, frame_time=t, frame_index=index, display_mode=settings.display_mode if settings.display_export else "raw", include_grid=settings.grid_export)
            frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=256))
            if progress:
                progress(index + 1, frame_count)
        target.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(
            target,
            save_all=True,
            append_images=frames[1:],
            duration=max(1, round(1000 / fps)),
            loop=0,
            optimize=False,
        )
        return target

    target = target.with_suffix(".mp4") if target.suffix.lower() != ".mp4" else target
    target.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    try:
        for index in range(frame_count):
            t = index / fps
            animated = settings_at_time(settings, t)
            frame = process_image(image, animated, frame_time=t, frame_index=index, display_mode=settings.display_mode if settings.display_export else "raw", include_grid=settings.grid_export).convert("RGB")
            frame = _prepare_h264_frame(frame)
            if writer is None:
                writer = _open_mp4_writer(target, frame.size, fps)
            writer.send(np.asarray(frame, dtype=np.uint8).tobytes())
            if progress:
                progress(index + 1, frame_count)
    finally:
        if writer is not None:
            writer.close()
    return target



def export_processed_gif(
    source_path: str | Path,
    settings: ProcessingSettings,
    output: str | Path,
    *,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    source = Path(source_path)
    target = Path(output)
    target = target.with_suffix(".gif") if target.suffix.lower() != ".gif" else target
    target.parent.mkdir(parents=True, exist_ok=True)
    durations, _ = _gif_frame_durations(source)
    frames: list[Image.Image] = []
    elapsed = 0.0
    with Image.open(source) as gif:
        count = int(getattr(gif, "n_frames", 1))
        for index in range(count):
            gif.seek(index)
            source_frame = gif.convert("RGB")
            animated = settings_at_time(settings, elapsed)
            result = process_image(
                source_frame,
                animated,
                frame_time=elapsed,
                frame_index=index,
                display_mode=settings.display_mode if settings.display_export else "raw",
                include_grid=settings.grid_export,
            )
            frames.append(result.convert("P", palette=Image.Palette.ADAPTIVE, colors=256))
            elapsed += durations[index] / 1000.0
            if progress:
                progress(index + 1, count)
    if not frames:
        raise RuntimeError("GIF has no frames")
    frames[0].save(
        target,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
        disposal=2,
    )
    return target

def export_processed_video(
    source_path: str | Path,
    settings: ProcessingSettings,
    output: str | Path,
    *,
    include_audio: bool = True,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    source = Path(source_path)
    target = Path(output)
    if source.suffix.lower() == ".gif" and target.suffix.lower() == ".gif":
        return export_processed_gif(source, settings, target, progress=progress)
    target = target.with_suffix(".mp4") if target.suffix.lower() != ".mp4" else target
    target.parent.mkdir(parents=True, exist_ok=True)

    meta, frames = iter_video_frames(source)
    source_w, source_h = meta["size"]
    fps = float(meta.get("fps") or 25.0)
    duration = float(meta.get("duration") or 0.0)
    total = max(0, int(round(duration * fps)))

    temp_dir = Path(tempfile.mkdtemp(prefix="rastermint-video-"))
    video_only = temp_dir / "video-only.mp4"
    writer = None
    try:
        for index, raw in enumerate(frames):
            arr = np.frombuffer(raw, dtype=np.uint8).reshape(int(source_h), int(source_w), 3)
            source_frame = Image.fromarray(arr, "RGB")
            t = index / fps
            animated = settings_at_time(settings, t)
            result = process_image(source_frame, animated, frame_time=t, frame_index=index, display_mode=settings.display_mode if settings.display_export else "raw", include_grid=settings.grid_export).convert("RGB")
            result = _prepare_h264_frame(result)
            if writer is None:
                writer = _open_mp4_writer(video_only, result.size, fps)
            writer.send(np.asarray(result, dtype=np.uint8).tobytes())
            if progress:
                progress(index + 1, total)
        if writer is not None:
            writer.close()
            writer = None
        if include_audio and _mux_source_audio(video_only, source, target):
            return target
        shutil.move(str(video_only), str(target))
        return target
    finally:
        if writer is not None:
            writer.close()
        try:
            frames.close()  # type: ignore[attr-defined]
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)
