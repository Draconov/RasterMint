# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
from threading import RLock
from typing import Any

from PIL import Image


class LayerRenderCache:
    """Bounded LRU cache of intermediate layer-stack results.

    Cache entries are keyed by source identity plus a cumulative signature of
    the normalized stack. Editing layer N therefore reuses the rendered output
    after layer N-1 while invalidating only the changed suffix.
    """

    def __init__(self, max_megabytes: int = 256) -> None:
        self._lock = RLock()
        self._entries: OrderedDict[tuple[str, str], tuple[Image.Image, int]] = OrderedDict()
        self._bytes = 0
        self._max_bytes = max(16, int(max_megabytes)) * 1024 * 1024

    @property
    def max_megabytes(self) -> int:
        return max(16, round(self._max_bytes / (1024 * 1024)))

    def set_budget(self, max_megabytes: int) -> None:
        with self._lock:
            self._max_bytes = max(16, min(4096, int(max_megabytes))) * 1024 * 1024
            self._trim()

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._bytes = 0

    @staticmethod
    def _image_bytes(image: Image.Image) -> int:
        return max(1, image.width * image.height * max(1, len(image.getbands())))


    @staticmethod
    def source_signature(image: Image.Image) -> str:
        """Return a compact content signature for a prepared raster source.

        Preview frames are small enough that hashing their raw bytes is cheaper
        than accidentally re-rendering every unchanged prefix layer. Geometry
        changes naturally produce a new signature, so crop/target/mirror edits
        cannot reuse stale intermediate images.
        """
        digest = hashlib.blake2b(digest_size=16)
        digest.update(str(image.mode).encode("ascii", errors="ignore"))
        digest.update(f"{image.width}x{image.height}".encode("ascii"))
        digest.update(image.tobytes())
        return digest.hexdigest()

    @staticmethod
    def prefix_signatures(stack: list[dict[str, Any]], palette: list[str]) -> list[str]:
        # Palette is included globally for correctness. It makes palette edits
        # invalidate earlier layers too, which is conservative but safe.
        digest = hashlib.blake2b(digest_size=16)
        digest.update(json.dumps(list(palette), separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        result: list[str] = []
        for step in stack:
            digest.update(b"\0")
            digest.update(json.dumps(step, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8"))
            result.append(digest.hexdigest())
        return result

    def longest_prefix(self, context: str, signatures: list[str]) -> tuple[int, Image.Image | None]:
        with self._lock:
            for index in range(len(signatures) - 1, -1, -1):
                key = (str(context), signatures[index])
                item = self._entries.get(key)
                if item is None:
                    continue
                self._entries.move_to_end(key)
                return index + 1, item[0].copy()
        return 0, None

    def store(self, context: str, signature: str, image: Image.Image) -> None:
        key = (str(context), str(signature))
        copy = image.copy()
        size = self._image_bytes(copy)
        with self._lock:
            previous = self._entries.pop(key, None)
            if previous is not None:
                self._bytes -= previous[1]
            self._entries[key] = (copy, size)
            self._bytes += size
            self._trim()

    def _trim(self) -> None:
        while self._bytes > self._max_bytes and self._entries:
            _key, (_image, size) = self._entries.popitem(last=False)
            self._bytes -= size
