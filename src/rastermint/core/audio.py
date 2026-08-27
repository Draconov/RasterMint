# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np


def _ffmpeg_executable() -> str:
    from .ffmpeg_runtime import configure_bundled_ffmpeg
    configured = configure_bundled_ffmpeg()
    if configured:
        return configured
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def extract_audio_envelope(path: str | Path, *, rate: float = 30.0, sample_rate: int = 8000) -> tuple[list[float], float]:
    """Decode audio to a normalized RMS envelope without keeping raw audio in memory."""
    source = str(Path(path))
    rate = max(1.0, min(120.0, float(rate)))
    sample_rate = max(1000, int(sample_rate))
    samples_per_bin = max(1, round(sample_rate / rate))
    command = [
        _ffmpeg_executable(), "-v", "error", "-i", source,
        "-vn", "-ac", "1", "-ar", str(sample_rate), "-f", "f32le", "-",
    ]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.stdout is None:
        raise RuntimeError("FFmpeg did not expose decoded audio.")

    envelope: list[float] = []
    pending = np.empty((0,), dtype=np.float32)
    while True:
        chunk = proc.stdout.read(65536)
        if not chunk:
            break
        usable = len(chunk) - (len(chunk) % 4)
        if usable <= 0:
            continue
        values = np.frombuffer(chunk[:usable], dtype="<f4").astype(np.float32, copy=False)
        if pending.size:
            values = np.concatenate((pending, values))
            pending = np.empty((0,), dtype=np.float32)
        count = values.size // samples_per_bin
        if count:
            body = values[: count * samples_per_bin].reshape(count, samples_per_bin)
            rms = np.sqrt(np.mean(np.square(body, dtype=np.float32), axis=1))
            envelope.extend(float(value) for value in rms)
        tail = values[count * samples_per_bin :]
        if tail.size:
            pending = np.array(tail, copy=True)

    stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    code = proc.wait()
    if code != 0:
        raise RuntimeError(stderr.strip() or "FFmpeg could not analyse the audio track.")
    if pending.size:
        envelope.append(float(np.sqrt(np.mean(np.square(pending, dtype=np.float32)))))
    if not envelope:
        raise RuntimeError("No audio track was found.")

    values = np.asarray(envelope, dtype=np.float32)
    # Robust normalization prevents a single transient from flattening the rest.
    peak = float(np.percentile(values, 99.0)) if values.size else 0.0
    if peak > 1e-9:
        values = np.clip(values / peak, 0.0, 1.0)
    else:
        values[:] = 0.0
    return [round(float(value), 6) for value in values], rate
