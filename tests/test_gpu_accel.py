# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import numpy as np

from rastermint.core import gpu_accel
from rastermint.core import palette as palette_module


def test_gpu_can_be_forced_off(monkeypatch) -> None:
    monkeypatch.setenv("RASTERMINT_GPU", "0")
    info = gpu_accel.gpu_backend_info()
    assert info["enabled"] is False
    assert info["available"] is False
    assert info["backend"] == "CPU"


def test_tiny_palette_job_does_not_initialize_gpu(monkeypatch) -> None:
    def fail_if_called():
        raise AssertionError("tiny jobs should stay on CPU")

    monkeypatch.setattr(gpu_accel, "_get_backend", fail_if_called)
    image = np.zeros((8, 8, 3), dtype=np.float32)
    palette = np.asarray([[0, 0, 0], [255, 255, 255]], dtype=np.float32)
    assert gpu_accel.try_quantize_nearest(image, palette) is None


def test_tiny_channel_job_does_not_initialize_gpu(monkeypatch) -> None:
    def fail_if_called():
        raise AssertionError("tiny jobs should stay on CPU")

    monkeypatch.setattr(gpu_accel, "_get_backend", fail_if_called)
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    assert gpu_accel.try_quantize_channel_bits(image, [5, 5, 5]) is None


def test_palette_cpu_fallback_matches_previous_bounded_mapping(monkeypatch) -> None:
    monkeypatch.setattr(palette_module, "try_quantize_nearest", lambda image, palette: None)
    image = np.asarray(
        [
            [[0, 0, 0], [220, 20, 20], [20, 230, 20]],
            [[250, 250, 250], [20, 20, 220], [120, 120, 120]],
        ],
        dtype=np.float32,
    )
    palette = np.asarray(
        [[0, 0, 0], [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 255]],
        dtype=np.float32,
    )
    result = palette_module.quantize_nearest(image, palette, chunk_pixels=1024)
    expected = np.asarray(
        [
            [[0, 0, 0], [255, 0, 0], [0, 255, 0]],
            [[255, 255, 255], [0, 0, 255], [0, 0, 0]],
        ],
        dtype=np.float32,
    )
    assert np.array_equal(result, expected)


def test_palette_accepts_accelerated_result(monkeypatch) -> None:
    sentinel = np.full((2, 2, 3), 17.0, dtype=np.float32)
    monkeypatch.setattr(palette_module, "try_quantize_nearest", lambda image, palette: sentinel)
    result = palette_module.quantize_nearest(
        np.zeros((2, 2, 3), dtype=np.float32),
        np.asarray([[0, 0, 0], [255, 255, 255]], dtype=np.float32),
    )
    assert result is sentinel
