#!/usr/bin/env python3
# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""Validate that an FFmpeg binary covers RasterMint's offline media paths."""

from __future__ import annotations

import argparse
from pathlib import Path
import math
import struct
import subprocess
import tempfile
import wave


def _run(ffmpeg: Path, *args: str, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(ffmpeg), *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _listing(ffmpeg: Path, flag: str) -> str:
    result = _run(ffmpeg, "-hide_banner", flag)
    text = (result.stdout + result.stderr).decode("utf-8", errors="replace").lower()
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg {flag} failed:\n{text[-2000:]}")
    return text


def _require_tokens(label: str, text: str, tokens: tuple[str, ...]) -> None:
    missing = [token for token in tokens if token.lower() not in text]
    if missing:
        raise RuntimeError(f"FFmpeg is missing required {label}: {', '.join(missing)}")


def _write_test_wav(path: Path) -> None:
    sample_rate = 8_000
    frames = bytearray()
    for index in range(sample_rate // 2):
        sample = int(8_000 * math.sin(2.0 * math.pi * 440.0 * index / sample_rate))
        frames.extend(struct.pack("<h", sample))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(frames)


def _write_png_frames(folder: Path) -> None:
    from PIL import Image

    for index in range(4):
        image = Image.new("RGB", (16, 16), (30 + index * 45, 80, 210 - index * 35))
        image.save(folder / f"frame_{index:08d}.png", format="PNG")


def validate(ffmpeg: Path) -> None:
    if not ffmpeg.is_file():
        raise RuntimeError(f"FFmpeg executable does not exist: {ffmpeg}")

    version = _run(ffmpeg, "-hide_banner", "-version")
    if version.returncode != 0:
        raise RuntimeError("FFmpeg executable could not be started")

    encoders = _listing(ffmpeg, "-encoders")
    decoders = _listing(ffmpeg, "-decoders")
    demuxers = _listing(ffmpeg, "-demuxers")
    muxers = _listing(ffmpeg, "-muxers")
    filters = _listing(ffmpeg, "-filters")
    protocols = _listing(ffmpeg, "-protocols")

    _require_tokens("encoders", encoders, ("libx264", "aac", "gif"))
    _require_tokens(
        "decoders",
        decoders,
        ("h264", "hevc", "vp8", "vp9", "av1", "mpeg4", "aac", "mp3", "opus", "vorbis", "png"),
    )
    _require_tokens("demuxers", demuxers, ("mov,mp4", "matroska,webm", "avi", "image2", "rawvideo"))
    _require_tokens("muxers", muxers, ("mp4", "gif"))
    _require_tokens("filters", filters, ("palettegen", "paletteuse"))
    _require_tokens("protocols", protocols, ("file", "pipe"))

    with tempfile.TemporaryDirectory(prefix="rastermint-ffmpeg-check-") as temp_value:
        temp = Path(temp_value)
        video = temp / "video.mp4"
        source_with_audio = temp / "source-audio.mp4"
        muxed = temp / "muxed.mp4"
        wav = temp / "tone.wav"

        # imageio-ffmpeg writes RasterMint frames as raw rgb24 over stdin.
        raw = bytearray()
        for frame_index in range(6):
            for y in range(16):
                for x in range(16):
                    raw.extend(((x * 16 + frame_index * 7) & 0xFF, (y * 16) & 0xFF, 160))
        encoded = _run(
            ffmpeg,
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s:v", "16x16",
            "-r", "6",
            "-i", "pipe:0",
            "-an",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-crf", "18",
            str(video),
            input_bytes=bytes(raw),
        )
        if encoded.returncode != 0 or not video.is_file():
            detail = encoded.stderr.decode("utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"H.264 raw-pipe encode smoke test failed:\n{detail}")

        decoded = _run(
            ffmpeg,
            "-i", str(video),
            "-frames:v", "1",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-vcodec", "rawvideo",
            "pipe:1",
        )
        if decoded.returncode != 0 or len(decoded.stdout) < 16 * 16 * 3:
            detail = decoded.stderr.decode("utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"RGB decode smoke test failed:\n{detail}")

        # RasterMint preserves source audio by copying processed video and
        # re-encoding the optional source audio stream to AAC.
        _write_test_wav(wav)
        audio_source = _run(
            ffmpeg,
            "-y",
            "-i", str(video),
            "-i", str(wav),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(source_with_audio),
        )
        if audio_source.returncode != 0 or not source_with_audio.is_file():
            detail = audio_source.stderr.decode("utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"AAC encode smoke test failed:\n{detail}")

        remux = _run(
            ffmpeg,
            "-y",
            "-i", str(video),
            "-i", str(source_with_audio),
            "-map", "0:v:0",
            "-map", "1:a?",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(muxed),
        )
        if remux.returncode != 0 or not muxed.is_file():
            detail = remux.stderr.decode("utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"Audio-preserving remux smoke test failed:\n{detail}")

        # Non-GIF video -> GIF export uses PNG frames plus palettegen/paletteuse.
        _write_png_frames(temp)
        pattern = str(temp / "frame_%08d.png")
        palette = temp / "palette.png"
        gif = temp / "preview.gif"
        palette_result = _run(
            ffmpeg,
            "-y",
            "-framerate", "6",
            "-start_number", "0",
            "-i", pattern,
            "-vf", "palettegen=max_colors=256:stats_mode=diff",
            str(palette),
        )
        if palette_result.returncode != 0 or not palette.is_file():
            detail = palette_result.stderr.decode("utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"GIF palette generation smoke test failed:\n{detail}")
        gif_result = _run(
            ffmpeg,
            "-y",
            "-framerate", "6",
            "-start_number", "0",
            "-i", pattern,
            "-i", str(palette),
            "-lavfi", "paletteuse=dither=sierra2_4a:diff_mode=rectangle",
            "-loop", "0",
            str(gif),
        )
        if gif_result.returncode != 0 or not gif.is_file():
            detail = gif_result.stderr.decode("utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"GIF encode smoke test failed:\n{detail}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ffmpeg", type=Path)
    args = parser.parse_args()
    try:
        validate(args.ffmpeg.resolve())
    except Exception as exc:
        print(f"FFmpeg validation failed: {exc}")
        return 1
    size_mib = args.ffmpeg.stat().st_size / (1024 * 1024)
    print(f"Validated RasterMint FFmpeg: {args.ffmpeg} ({size_mib:.1f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
