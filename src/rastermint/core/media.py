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
from .processor import make_preview_settings, make_preview_source, process_image, target_raster_size
from .settings import ProcessingSettings
from .temporal import TemporalEffectState, max_persistence_seconds

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
    from .ffmpeg_runtime import configure_bundled_ffmpeg

    configure_bundled_ffmpeg()
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
    temporal_state = TemporalEffectState()

    if target.suffix.lower() == ".gif":
        frames: list[Image.Image] = []
        for index in range(frame_count):
            t = index / fps
            animated = settings_at_time(settings, t)
            frame = process_image(image, animated, frame_time=t, frame_index=index, display_mode=settings.display_mode if settings.display_export else "raw", include_grid=settings.grid_export, temporal_state=temporal_state)
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
            frame = process_image(image, animated, frame_time=t, frame_index=index, display_mode=settings.display_mode if settings.display_export else "raw", include_grid=settings.grid_export, temporal_state=temporal_state).convert("RGB")
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
    temporal_state = TemporalEffectState()
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
                temporal_state=temporal_state,
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
    temporal_state = TemporalEffectState()

    temp_dir = Path(tempfile.mkdtemp(prefix="rastermint-video-"))
    video_only = temp_dir / "video-only.mp4"
    writer = None
    try:
        for index, raw in enumerate(frames):
            arr = np.frombuffer(raw, dtype=np.uint8).reshape(int(source_h), int(source_w), 3)
            source_frame = Image.fromarray(arr, "RGB")
            t = index / fps
            animated = settings_at_time(settings, t)
            result = process_image(source_frame, animated, frame_time=t, frame_index=index, display_mode=settings.display_mode if settings.display_export else "raw", include_grid=settings.grid_export, temporal_state=temporal_state).convert("RGB")
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



def render_image_preview_frames(
    image: Image.Image,
    settings: ProcessingSettings,
    *,
    max_side: int = 640,
    fps_limit: int = 30,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[list[Image.Image], list[float], float]:
    """Pre-render an accurate-at-preview-resolution animation cache."""
    duration = max(0.1, float(settings.animation_duration))
    fps = float(max(1, min(int(settings.animation_fps), max(1, int(fps_limit)))))
    frame_count = max(1, int(round(duration * fps)))
    # Keep rendered preview memory bounded; final export remains unrestricted.
    # 180 RGB preview frames at 640 px are already roughly 200–250 MB once
    # Python/Pillow overhead is included. The old 900-frame cache could exceed
    # a gigabyte and was a plausible source of intermittent process exits.
    if frame_count > 180:
        fps = max(1.0, 180.0 / duration)
        frame_count = 180

    final_size = target_raster_size(image.size, settings)
    preview_source = make_preview_source(image, max_side=max_side, settings=settings)
    frames: list[Image.Image] = []
    times: list[float] = []
    temporal_state = TemporalEffectState()
    for index in range(frame_count):
        t = min(duration, index / fps)
        animated = settings_at_time(settings, t)
        preview_settings = make_preview_settings(animated, final_size, preview_source.size)
        frame = process_image(
            preview_source,
            preview_settings,
            frame_time=t,
            frame_index=index,
            display_mode=preview_settings.display_mode,
            include_grid=preview_settings.grid_enabled and preview_settings.grid_preview,
            temporal_state=temporal_state,
        )
        frames.append(frame)
        times.append(t)
        if progress:
            progress(index + 1, frame_count)
    return frames, times, fps


def _iter_video_segment_frames(path: str | Path, start_time: float, duration: float, fps: float):
    source = Path(path)
    if source.suffix.lower() == ".gif":
        info = _probe_gif(source)
        count = max(1, int(round(duration * fps)))
        for index in range(count):
            t = min(info.duration, start_time + index / fps)
            yield t, _read_gif_frame(source, t)
        return

    ff = _imageio_ffmpeg()
    params = ["-ss", f"{max(0.0, start_time):.6f}"] if start_time > 0 else []
    output_params = ["-t", f"{max(0.01, duration):.6f}", "-vf", f"fps={max(1.0, fps):.6f}"]
    generator = ff.read_frames(str(source), pix_fmt="rgb24", input_params=params, output_params=output_params)
    try:
        meta = next(generator)
        width, height = meta["size"]
        for index, raw in enumerate(generator):
            arr = np.frombuffer(raw, dtype=np.uint8).reshape(int(height), int(width), 3)
            yield start_time + index / fps, Image.fromarray(arr.copy(), "RGB")
    finally:
        generator.close()


def render_processed_video_frame(
    source_path: str | Path,
    settings: ProcessingSettings,
    time_seconds: float,
) -> Image.Image:
    """Render one video frame with temporal history rebuilt before it.

    This is used for still-frame export from a video. The warm-up spans the
    requested persistence window but bounds sampling to roughly 300 frames for
    very long retention times. Sequential animation/video exports remain exact
    at their export frame rate because they carry one state through every frame.
    """
    info = probe_video(source_path)
    t_final = max(0.0, min(float(time_seconds), max(0.0, info.duration)))
    temporal_state = TemporalEffectState()
    persistence_window = min(t_final, max_persistence_seconds(settings.effect_stack))
    if persistence_window > 0.0:
        warmup_start = max(0.0, t_final - persistence_window)
        warmup_fps = min(max(1.0, float(info.fps or 25.0)), max(1.0, 300.0 / max(1.0, persistence_window)))
        for t, source_frame in _iter_video_segment_frames(
            source_path, warmup_start, persistence_window, warmup_fps
        ):
            animated = settings_at_time(settings, t)
            process_image(
                source_frame,
                animated,
                frame_time=t,
                frame_index=max(0, round(t * max(1.0, info.fps))),
                display_mode=animated.display_mode if animated.display_export else "raw",
                include_grid=animated.grid_enabled and animated.grid_export,
                temporal_state=temporal_state,
            )

    source_frame = read_video_frame(source_path, t_final)
    animated = settings_at_time(settings, t_final)
    return process_image(
        source_frame,
        animated,
        frame_time=t_final,
        frame_index=max(0, round(t_final * max(1.0, info.fps))),
        display_mode=animated.display_mode if animated.display_export else "raw",
        include_grid=animated.grid_enabled and animated.grid_export,
        temporal_state=temporal_state,
    )


def render_video_preview_frames(
    source_path: str | Path,
    settings: ProcessingSettings,
    *,
    start_time: float = 0.0,
    duration: float = 5.0,
    max_side: int = 640,
    fps_limit: int = 15,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[list[Image.Image], list[float], float]:
    """Render a short processed video segment for smooth cached playback."""
    info = probe_video(source_path)
    start_time = max(0.0, min(float(start_time), max(0.0, info.duration)))
    duration = max(0.05, min(float(duration), max(0.05, info.duration - start_time)))
    fps = max(1.0, min(float(info.fps or 15.0), float(max(1, fps_limit))))
    expected = max(1, int(round(duration * fps)))
    frames: list[Image.Image] = []
    times: list[float] = []
    temporal_state = TemporalEffectState()

    # Rebuild temporal history when rendering a preview segment that starts in
    # the middle of a video. Long persistence windows are sampled at a bounded
    # warm-up rate so seeking remains practical without storing old frames.
    persistence_window = min(start_time, max_persistence_seconds(settings.effect_stack))
    if persistence_window > 0.0:
        warmup_start = max(0.0, start_time - persistence_window)
        warmup_fps = min(fps, max(1.0, 240.0 / max(1.0, persistence_window)))
        for t, source_frame in _iter_video_segment_frames(
            source_path, warmup_start, persistence_window, warmup_fps
        ):
            animated = settings_at_time(settings, t)
            final_size = target_raster_size(source_frame.size, animated)
            preview_source = make_preview_source(source_frame, max_side=max_side, settings=animated)
            preview_settings = make_preview_settings(animated, final_size, preview_source.size)
            process_image(
                preview_source,
                preview_settings,
                frame_time=t,
                frame_index=max(0, round(t * max(1.0, info.fps))),
                display_mode=preview_settings.display_mode,
                include_grid=preview_settings.grid_enabled and preview_settings.grid_preview,
                temporal_state=temporal_state,
            )

    for index, (t, source_frame) in enumerate(_iter_video_segment_frames(source_path, start_time, duration, fps)):
        animated = settings_at_time(settings, t)
        final_size = target_raster_size(source_frame.size, animated)
        preview_source = make_preview_source(source_frame, max_side=max_side, settings=animated)
        preview_settings = make_preview_settings(animated, final_size, preview_source.size)
        frame = process_image(
            preview_source,
            preview_settings,
            frame_time=t,
            frame_index=max(0, round(t * max(1.0, info.fps))),
            display_mode=preview_settings.display_mode,
            include_grid=preview_settings.grid_enabled and preview_settings.grid_preview,
            temporal_state=temporal_state,
        )
        frames.append(frame)
        times.append(t)
        if progress:
            progress(index + 1, expected)
    return frames, times, fps


def export_image_sequence(
    image: Image.Image,
    settings: ProcessingSettings,
    output_dir: str | Path,
    *,
    prefix: str = "frame",
    duration: float | None = None,
    fps: int | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> list[Path]:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    duration = max(0.1, float(duration if duration is not None else settings.animation_duration))
    fps = max(1, int(fps if fps is not None else settings.animation_fps))
    frame_count = max(1, int(round(duration * fps)))
    digits = max(4, len(str(frame_count)))
    written: list[Path] = []
    temporal_state = TemporalEffectState()
    for index in range(frame_count):
        t = index / fps
        animated = settings_at_time(settings, t)
        frame = process_image(
            image,
            animated,
            frame_time=t,
            frame_index=index,
            display_mode=settings.display_mode if settings.display_export else "raw",
            include_grid=settings.grid_enabled and settings.grid_export,
            temporal_state=temporal_state,
        )
        path = target_dir / f"{prefix}_{index + 1:0{digits}d}.png"
        frame.save(path, format="PNG")
        written.append(path)
        if progress:
            progress(index + 1, frame_count)
    return written


def export_processed_video_sequence(
    source_path: str | Path,
    settings: ProcessingSettings,
    output_dir: str | Path,
    *,
    prefix: str = "frame",
    progress: Callable[[int, int], None] | None = None,
) -> list[Path]:
    source = Path(source_path)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    info = probe_video(source)
    total = max(1, info.frames)
    digits = max(4, len(str(total)))
    written: list[Path] = []
    temporal_state = TemporalEffectState()

    if source.suffix.lower() == ".gif":
        durations, _ = _gif_frame_durations(source)
        elapsed = 0.0
        with Image.open(source) as gif:
            count = int(getattr(gif, "n_frames", 1))
            total = max(1, count)
            digits = max(4, len(str(total)))
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
                    include_grid=settings.grid_enabled and settings.grid_export,
                    temporal_state=temporal_state,
                )
                path = target_dir / f"{prefix}_{index + 1:0{digits}d}.png"
                result.save(path, format="PNG")
                written.append(path)
                elapsed += durations[index] / 1000.0
                if progress:
                    progress(index + 1, total)
        return written

    meta, frames = iter_video_frames(source)
    width, height = meta["size"]
    fps = float(meta.get("fps") or info.fps or 25.0)
    try:
        for index, raw in enumerate(frames):
            arr = np.frombuffer(raw, dtype=np.uint8).reshape(int(height), int(width), 3)
            source_frame = Image.fromarray(arr, "RGB")
            t = index / fps
            animated = settings_at_time(settings, t)
            result = process_image(
                source_frame,
                animated,
                frame_time=t,
                frame_index=index,
                display_mode=settings.display_mode if settings.display_export else "raw",
                include_grid=settings.grid_enabled and settings.grid_export,
                temporal_state=temporal_state,
            )
            path = target_dir / f"{prefix}_{index + 1:0{digits}d}.png"
            result.save(path, format="PNG")
            written.append(path)
            if progress:
                progress(index + 1, total)
    finally:
        try:
            frames.close()  # type: ignore[attr-defined]
        except Exception:
            pass
    return written
