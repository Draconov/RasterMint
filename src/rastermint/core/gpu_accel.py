# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""Small optional OpenCL acceleration layer for RasterMint.

The core deliberately has no hard GPU dependency.  When a system OpenCL
runtime and a GPU device are available, selected data-parallel operations can
use it.  Any discovery/build/runtime failure returns ``None`` to the caller so
the existing NumPy implementation remains the source-of-truth fallback.

Set ``RASTERMINT_GPU=0`` (or ``off``/``false``/``cpu``) to force CPU rendering.
"""

from __future__ import annotations

import ctypes
from ctypes import byref, c_char_p, c_int, c_size_t, c_uint, c_ulong, c_void_p
import os
import platform
import threading
from typing import Any

import numpy as np


_CL_SUCCESS = 0
_CL_DEVICE_TYPE_GPU = 1 << 2
_CL_MEM_WRITE_ONLY = 1 << 1
_CL_MEM_READ_ONLY = 1 << 2
_CL_MEM_COPY_HOST_PTR = 1 << 5
_CL_TRUE = 1
_CL_DEVICE_NAME = 0x102B
_CL_PLATFORM_NAME = 0x0902
_CL_PROGRAM_BUILD_LOG = 0x1183
_CL_PLATFORM_NOT_FOUND_KHR = -1001

# Transfers and kernel launch overhead dominate tiny jobs.  The score is roughly
# pixel_count × palette_count for palette mapping and pixel_count × 3 for RGB
# bit-depth quantization.
_MIN_PALETTE_WORK = 750_000
_MIN_CHANNEL_PIXELS = 512 * 512

_KERNEL_SOURCE = r"""
__kernel void rm_nearest_palette(
    __global const float *pixels,
    __global const float *palette,
    const int palette_count,
    const int pixel_count,
    __global float *output)
{
    const int gid = (int)get_global_id(0);
    if (gid >= pixel_count || palette_count <= 0) return;

    const int base = gid * 3;
    const float r = pixels[base + 0];
    const float g = pixels[base + 1];
    const float b = pixels[base + 2];

    int best = 0;
    float dr = r - palette[0];
    float dg = g - palette[1];
    float db = b - palette[2];
    float best_dist = dr * dr + dg * dg + db * db;

    for (int i = 1; i < palette_count; ++i) {
        const int p = i * 3;
        dr = r - palette[p + 0];
        dg = g - palette[p + 1];
        db = b - palette[p + 2];
        const float dist = dr * dr + dg * dg + db * db;
        if (dist < best_dist) {
            best_dist = dist;
            best = i;
        }
    }

    const int p = best * 3;
    output[base + 0] = palette[p + 0];
    output[base + 1] = palette[p + 1];
    output[base + 2] = palette[p + 2];
}

inline uchar rm_quantize_channel(const uchar raw, const int bits)
{
    const int safe_bits = clamp(bits, 1, 8);
    const float levels = (float)((1 << safe_bits) - 1);
    const float first = rint(((float)raw / 255.0f) * levels);
    const float value = rint((first / levels) * 255.0f);
    return convert_uchar_sat(value);
}

__kernel void rm_channel_bits(
    __global const uchar *pixels,
    const int red_bits,
    const int green_bits,
    const int blue_bits,
    const int pixel_count,
    __global uchar *output)
{
    const int gid = (int)get_global_id(0);
    if (gid >= pixel_count) return;
    const int base = gid * 3;
    output[base + 0] = rm_quantize_channel(pixels[base + 0], red_bits);
    output[base + 1] = rm_quantize_channel(pixels[base + 1], green_bits);
    output[base + 2] = rm_quantize_channel(pixels[base + 2], blue_bits);
}
"""


def _gpu_allowed() -> bool:
    value = str(os.environ.get("RASTERMINT_GPU", "auto") or "auto").strip().lower()
    return value not in {"0", "off", "false", "no", "cpu", "disabled"}


def _library_candidates() -> tuple[str, ...]:
    system = platform.system().lower()
    if system == "windows":
        return ("OpenCL.dll",)
    if system == "darwin":
        return ("/System/Library/Frameworks/OpenCL.framework/OpenCL", "OpenCL")
    return ("libOpenCL.so.1", "libOpenCL.so")


def _load_opencl_library() -> ctypes.CDLL | None:
    for name in _library_candidates():
        try:
            return ctypes.CDLL(name)
        except OSError:
            continue
    return None


class _OpenCLBackend:
    def __init__(self) -> None:
        lib = _load_opencl_library()
        if lib is None:
            raise RuntimeError("OpenCL runtime not found")
        self.lib = lib
        self.lock = threading.RLock()
        self.context = c_void_p()
        self.queue = c_void_p()
        self.program = c_void_p()
        self.device = c_void_p()
        self.platform = c_void_p()
        self.k_nearest = c_void_p()
        self.k_channel = c_void_p()
        self.device_name = "OpenCL GPU"
        self.platform_name = "OpenCL"
        self._configure_api()
        self._initialize()

    def _configure_api(self) -> None:
        lib = self.lib
        lib.clGetPlatformIDs.argtypes = [c_uint, ctypes.POINTER(c_void_p), ctypes.POINTER(c_uint)]
        lib.clGetPlatformIDs.restype = c_int
        lib.clGetPlatformInfo.argtypes = [c_void_p, c_uint, c_size_t, c_void_p, ctypes.POINTER(c_size_t)]
        lib.clGetPlatformInfo.restype = c_int
        lib.clGetDeviceIDs.argtypes = [c_void_p, c_ulong, c_uint, ctypes.POINTER(c_void_p), ctypes.POINTER(c_uint)]
        lib.clGetDeviceIDs.restype = c_int
        lib.clGetDeviceInfo.argtypes = [c_void_p, c_uint, c_size_t, c_void_p, ctypes.POINTER(c_size_t)]
        lib.clGetDeviceInfo.restype = c_int
        lib.clCreateContext.argtypes = [c_void_p, c_uint, ctypes.POINTER(c_void_p), c_void_p, c_void_p, ctypes.POINTER(c_int)]
        lib.clCreateContext.restype = c_void_p
        lib.clCreateCommandQueue.argtypes = [c_void_p, c_void_p, c_ulong, ctypes.POINTER(c_int)]
        lib.clCreateCommandQueue.restype = c_void_p
        lib.clCreateProgramWithSource.argtypes = [c_void_p, c_uint, ctypes.POINTER(c_char_p), ctypes.POINTER(c_size_t), ctypes.POINTER(c_int)]
        lib.clCreateProgramWithSource.restype = c_void_p
        lib.clBuildProgram.argtypes = [c_void_p, c_uint, ctypes.POINTER(c_void_p), c_char_p, c_void_p, c_void_p]
        lib.clBuildProgram.restype = c_int
        lib.clGetProgramBuildInfo.argtypes = [c_void_p, c_void_p, c_uint, c_size_t, c_void_p, ctypes.POINTER(c_size_t)]
        lib.clGetProgramBuildInfo.restype = c_int
        lib.clCreateKernel.argtypes = [c_void_p, c_char_p, ctypes.POINTER(c_int)]
        lib.clCreateKernel.restype = c_void_p
        lib.clCreateBuffer.argtypes = [c_void_p, c_ulong, c_size_t, c_void_p, ctypes.POINTER(c_int)]
        lib.clCreateBuffer.restype = c_void_p
        lib.clSetKernelArg.argtypes = [c_void_p, c_uint, c_size_t, c_void_p]
        lib.clSetKernelArg.restype = c_int
        lib.clEnqueueNDRangeKernel.argtypes = [c_void_p, c_void_p, c_uint, c_void_p, ctypes.POINTER(c_size_t), c_void_p, c_uint, c_void_p, c_void_p]
        lib.clEnqueueNDRangeKernel.restype = c_int
        lib.clEnqueueReadBuffer.argtypes = [c_void_p, c_void_p, c_uint, c_size_t, c_size_t, c_void_p, c_uint, c_void_p, c_void_p]
        lib.clEnqueueReadBuffer.restype = c_int
        lib.clFinish.argtypes = [c_void_p]
        lib.clFinish.restype = c_int
        for name in ("clReleaseMemObject", "clReleaseKernel", "clReleaseProgram", "clReleaseCommandQueue", "clReleaseContext"):
            fn = getattr(lib, name)
            fn.argtypes = [c_void_p]
            fn.restype = c_int

    @staticmethod
    def _check(code: int, operation: str) -> None:
        if int(code) != _CL_SUCCESS:
            raise RuntimeError(f"{operation} failed with OpenCL error {int(code)}")

    def _info_string(self, fn: Any, handle: c_void_p, param: int) -> str:
        size = c_size_t(0)
        if int(fn(handle, param, 0, None, byref(size))) != _CL_SUCCESS or size.value <= 1:
            return ""
        buffer = ctypes.create_string_buffer(size.value)
        if int(fn(handle, param, size.value, buffer, None)) != _CL_SUCCESS:
            return ""
        return buffer.value.decode("utf-8", errors="replace").strip()

    def _initialize(self) -> None:
        count = c_uint(0)
        code = int(self.lib.clGetPlatformIDs(0, None, byref(count)))
        if code == _CL_PLATFORM_NOT_FOUND_KHR or count.value == 0:
            raise RuntimeError("No OpenCL platform found")
        self._check(code, "clGetPlatformIDs")
        platforms = (c_void_p * count.value)()
        self._check(self.lib.clGetPlatformIDs(count.value, platforms, None), "clGetPlatformIDs")

        chosen_platform = None
        chosen_device = None
        for platform_id in platforms:
            device_count = c_uint(0)
            code = int(self.lib.clGetDeviceIDs(platform_id, _CL_DEVICE_TYPE_GPU, 0, None, byref(device_count)))
            if code != _CL_SUCCESS or device_count.value == 0:
                continue
            devices = (c_void_p * device_count.value)()
            if int(self.lib.clGetDeviceIDs(platform_id, _CL_DEVICE_TYPE_GPU, device_count.value, devices, None)) == _CL_SUCCESS:
                chosen_platform = c_void_p(platform_id)
                chosen_device = c_void_p(devices[0])
                break
        if chosen_platform is None or chosen_device is None:
            raise RuntimeError("No OpenCL GPU device found")

        self.platform = chosen_platform
        self.device = chosen_device
        self.platform_name = self._info_string(self.lib.clGetPlatformInfo, self.platform, _CL_PLATFORM_NAME) or "OpenCL"
        self.device_name = self._info_string(self.lib.clGetDeviceInfo, self.device, _CL_DEVICE_NAME) or "OpenCL GPU"

        err = c_int(0)
        device_array = (c_void_p * 1)(self.device)
        self.context = c_void_p(self.lib.clCreateContext(None, 1, device_array, None, None, byref(err)))
        self._check(err.value, "clCreateContext")
        if not self.context:
            raise RuntimeError("OpenCL returned a null context")

        self.queue = c_void_p(self.lib.clCreateCommandQueue(self.context, self.device, 0, byref(err)))
        self._check(err.value, "clCreateCommandQueue")
        if not self.queue:
            raise RuntimeError("OpenCL returned a null command queue")

        encoded = _KERNEL_SOURCE.encode("utf-8")
        source = c_char_p(encoded)
        source_length = c_size_t(len(encoded))
        self.program = c_void_p(self.lib.clCreateProgramWithSource(self.context, 1, byref(source), byref(source_length), byref(err)))
        self._check(err.value, "clCreateProgramWithSource")
        build_code = int(self.lib.clBuildProgram(self.program, 1, device_array, None, None, None))
        if build_code != _CL_SUCCESS:
            log = self._info_string(
                lambda handle, param, size, value, size_ret: self.lib.clGetProgramBuildInfo(handle, self.device, param, size, value, size_ret),
                self.program,
                _CL_PROGRAM_BUILD_LOG,
            )
            raise RuntimeError(f"OpenCL kernel build failed ({build_code}): {log}")

        self.k_nearest = c_void_p(self.lib.clCreateKernel(self.program, b"rm_nearest_palette", byref(err)))
        self._check(err.value, "clCreateKernel(rm_nearest_palette)")
        self.k_channel = c_void_p(self.lib.clCreateKernel(self.program, b"rm_channel_bits", byref(err)))
        self._check(err.value, "clCreateKernel(rm_channel_bits)")

    def _buffer(self, flags: int, array: np.ndarray | None, size: int) -> c_void_p:
        err = c_int(0)
        ptr = None if array is None else c_void_p(int(array.ctypes.data))
        mem = c_void_p(self.lib.clCreateBuffer(self.context, flags, int(size), ptr, byref(err)))
        self._check(err.value, "clCreateBuffer")
        if not mem:
            raise RuntimeError("OpenCL returned a null buffer")
        return mem

    def _set_mem_arg(self, kernel: c_void_p, index: int, mem: c_void_p) -> None:
        self._check(self.lib.clSetKernelArg(kernel, index, ctypes.sizeof(c_void_p), byref(mem)), "clSetKernelArg")

    def _set_int_arg(self, kernel: c_void_p, index: int, value: int) -> None:
        scalar = c_int(int(value))
        self._check(self.lib.clSetKernelArg(kernel, index, ctypes.sizeof(scalar), byref(scalar)), "clSetKernelArg")

    def _run_1d(self, kernel: c_void_p, count: int) -> None:
        global_size = c_size_t(max(1, int(count)))
        self._check(
            self.lib.clEnqueueNDRangeKernel(self.queue, kernel, 1, None, byref(global_size), None, 0, None, None),
            "clEnqueueNDRangeKernel",
        )
        self._check(self.lib.clFinish(self.queue), "clFinish")

    def nearest_palette(self, image: np.ndarray, palette: np.ndarray) -> np.ndarray:
        source = np.ascontiguousarray(image, dtype=np.float32)
        pal = np.ascontiguousarray(palette, dtype=np.float32).reshape(-1, 3)
        if source.ndim != 3 or source.shape[-1] != 3 or pal.size == 0:
            raise ValueError("Expected H×W×3 image and non-empty RGB palette")
        h, w, _ = source.shape
        pixel_count = int(h * w)
        output = np.empty_like(source)
        source_flat = source.reshape(-1)
        output_flat = output.reshape(-1)
        mems: list[c_void_p] = []
        with self.lock:
            try:
                src_mem = self._buffer(_CL_MEM_READ_ONLY | _CL_MEM_COPY_HOST_PTR, source_flat, source_flat.nbytes); mems.append(src_mem)
                pal_mem = self._buffer(_CL_MEM_READ_ONLY | _CL_MEM_COPY_HOST_PTR, pal, pal.nbytes); mems.append(pal_mem)
                out_mem = self._buffer(_CL_MEM_WRITE_ONLY, None, output_flat.nbytes); mems.append(out_mem)
                self._set_mem_arg(self.k_nearest, 0, src_mem)
                self._set_mem_arg(self.k_nearest, 1, pal_mem)
                self._set_int_arg(self.k_nearest, 2, len(pal))
                self._set_int_arg(self.k_nearest, 3, pixel_count)
                self._set_mem_arg(self.k_nearest, 4, out_mem)
                self._run_1d(self.k_nearest, pixel_count)
                self._check(
                    self.lib.clEnqueueReadBuffer(
                        self.queue, out_mem, _CL_TRUE, 0, output_flat.nbytes,
                        c_void_p(int(output_flat.ctypes.data)), 0, None, None,
                    ),
                    "clEnqueueReadBuffer",
                )
            finally:
                for mem in reversed(mems):
                    self.lib.clReleaseMemObject(mem)
        return output

    def channel_bits(self, image: np.ndarray, bits: tuple[int, int, int]) -> np.ndarray:
        source = np.ascontiguousarray(image, dtype=np.uint8)
        if source.ndim != 3 or source.shape[-1] != 3:
            raise ValueError("Expected H×W×3 RGB image")
        h, w, _ = source.shape
        pixel_count = int(h * w)
        output = np.empty_like(source)
        source_flat = source.reshape(-1)
        output_flat = output.reshape(-1)
        mems: list[c_void_p] = []
        with self.lock:
            try:
                src_mem = self._buffer(_CL_MEM_READ_ONLY | _CL_MEM_COPY_HOST_PTR, source_flat, source_flat.nbytes); mems.append(src_mem)
                out_mem = self._buffer(_CL_MEM_WRITE_ONLY, None, output_flat.nbytes); mems.append(out_mem)
                self._set_mem_arg(self.k_channel, 0, src_mem)
                self._set_int_arg(self.k_channel, 1, bits[0])
                self._set_int_arg(self.k_channel, 2, bits[1])
                self._set_int_arg(self.k_channel, 3, bits[2])
                self._set_int_arg(self.k_channel, 4, pixel_count)
                self._set_mem_arg(self.k_channel, 5, out_mem)
                self._run_1d(self.k_channel, pixel_count)
                self._check(
                    self.lib.clEnqueueReadBuffer(
                        self.queue, out_mem, _CL_TRUE, 0, output_flat.nbytes,
                        c_void_p(int(output_flat.ctypes.data)), 0, None, None,
                    ),
                    "clEnqueueReadBuffer",
                )
            finally:
                for mem in reversed(mems):
                    self.lib.clReleaseMemObject(mem)
        return output


_BACKEND_LOCK = threading.Lock()
_BACKEND: _OpenCLBackend | None | bool = None
_BACKEND_ERROR = ""
_RUNTIME_FAILURES = 0


def _get_backend() -> _OpenCLBackend | None:
    global _BACKEND, _BACKEND_ERROR
    if not _gpu_allowed():
        return None
    if _BACKEND is False:
        return None
    if isinstance(_BACKEND, _OpenCLBackend):
        return _BACKEND
    with _BACKEND_LOCK:
        if isinstance(_BACKEND, _OpenCLBackend):
            return _BACKEND
        if _BACKEND is False:
            return None
        try:
            _BACKEND = _OpenCLBackend()
            _BACKEND_ERROR = ""
        except Exception as exc:
            _BACKEND = False
            _BACKEND_ERROR = str(exc)
            return None
    return _BACKEND if isinstance(_BACKEND, _OpenCLBackend) else None


def _runtime_failure(exc: Exception) -> None:
    global _RUNTIME_FAILURES, _BACKEND, _BACKEND_ERROR
    _RUNTIME_FAILURES += 1
    _BACKEND_ERROR = str(exc)
    # A transient allocation failure should not immediately poison the backend,
    # but repeated driver/runtime errors should stop retrying every frame.
    if _RUNTIME_FAILURES >= 3:
        _BACKEND = False


def try_quantize_nearest(image: np.ndarray, palette: np.ndarray) -> np.ndarray | None:
    """Return GPU nearest-palette output, or ``None`` for the CPU fallback."""
    source = np.asarray(image)
    pal = np.asarray(palette)
    if source.ndim != 3 or source.shape[-1] != 3 or pal.ndim != 2 or pal.shape[-1] != 3 or len(pal) == 0:
        return None
    pixel_count = int(source.shape[0] * source.shape[1])
    if pixel_count * int(len(pal)) < _MIN_PALETTE_WORK:
        return None
    backend = _get_backend()
    if backend is None:
        return None
    try:
        return backend.nearest_palette(source, pal)
    except Exception as exc:
        _runtime_failure(exc)
        return None


def try_quantize_channel_bits(image: np.ndarray, bits: list[int] | tuple[int, ...]) -> np.ndarray | None:
    """Return GPU RGB bit-depth quantization, or ``None`` for CPU fallback."""
    source = np.asarray(image)
    if source.ndim != 3 or source.shape[-1] != 3:
        return None
    pixel_count = int(source.shape[0] * source.shape[1])
    if pixel_count < _MIN_CHANNEL_PIXELS:
        return None
    raw = list(bits)
    if not raw:
        return None
    while len(raw) < 3:
        raw.append(raw[-1])
    clean = tuple(max(1, min(8, int(v))) for v in raw[:3])
    backend = _get_backend()
    if backend is None:
        return None
    try:
        return backend.channel_bits(source, clean)
    except Exception as exc:
        _runtime_failure(exc)
        return None


def gpu_backend_info() -> dict[str, Any]:
    """Small diagnostic snapshot without forcing GPU initialization when disabled."""
    if not _gpu_allowed():
        return {"enabled": False, "available": False, "backend": "CPU", "device": "", "error": "Disabled by RASTERMINT_GPU"}
    backend = _get_backend()
    if backend is None:
        return {"enabled": True, "available": False, "backend": "CPU", "device": "", "error": _BACKEND_ERROR}
    return {
        "enabled": True,
        "available": True,
        "backend": "OpenCL",
        "platform": backend.platform_name,
        "device": backend.device_name,
        "error": _BACKEND_ERROR,
    }
