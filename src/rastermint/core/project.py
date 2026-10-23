# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Portable RasterMint projects with optional embedded external assets.

The .rastermint file remains UTF-8 JSON (schema v2) for backwards
compatibility. Embedded images, sprites, textures and font files are zlib-
compressed and base64-encoded. Old projects remain readable.
"""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any
import zlib

PROJECT_SCHEMA = "rastermint-project"
PROJECT_VERSION = 2
MAX_ASSET_BYTES = 128 * 1024 * 1024
MAX_TOTAL_ASSET_BYTES = 256 * 1024 * 1024
MAX_EMBEDDED_ASSETS = 100
ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif", ".ttf", ".otf", ".woff", ".woff2", ".svg", ".ase", ".aseprite"}


def _is_reference(key: str, value: str) -> bool:
    name = key.lower()
    return bool(value and (name in {"path", "sprite_path", "texture_path", "font_path", "image_path", "reference_path"}
                           or name.endswith(("_path", "_file"))
                 or (name == "font" and Path(value).suffix.lower() in {".ttf", ".otf"})))


def _walk_references(obj: Any):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and _is_reference(str(key), value):
                yield obj, key, value
            elif isinstance(value, (list, dict)):
                yield from _walk_references(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk_references(value)


def _encoded_file(path: Path) -> tuple[bytes, str]:
    if not path.is_file() or path.suffix.lower() not in ASSET_EXTENSIONS:
        raise ValueError(f"Unsupported or missing external project asset: {path}")
    if path.stat().st_size > MAX_ASSET_BYTES:
        raise ValueError(f"Asset exceeds 128 MiB portability limit: {path.name}")
    raw = path.read_bytes()
    return raw, path.suffix.lower()


def _add_embedded_assets(payload: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    packed = deepcopy(payload)
    assets: dict[str, dict[str, str]] = {}
    total = 0
    for parent, key, value in _walk_references(packed):
        if not value or value.startswith("data:"):
            continue
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = project_dir / candidate
        # A missing media path is an error when explicitly saving a portable
        # project, not a silently broken reference inside the supposedly
        # self-contained artifact.
        if not candidate.is_file():
            if key == "path" and not value:
                continue
            raise FileNotFoundError(f"Cannot package missing project asset: {value}")
        if candidate.suffix.lower() not in ASSET_EXTENSIONS:
            # Videos are intentionally kept as external references: embedding a
            # multi-GB video in JSON would make ordinary project saves unusable.
            continue
        raw, suffix = _encoded_file(candidate)
        total += len(raw)
        if total > MAX_TOTAL_ASSET_BYTES:
            raise ValueError("Project embeds more than 256 MiB of assets")
        digest = hashlib.sha256(raw).hexdigest()
        if digest not in assets:
            if len(assets) >= MAX_EMBEDDED_ASSETS:
                raise ValueError("Project contains more than 100 referenced assets")
            assets[digest] = {
                "name": candidate.name,
                "suffix": suffix,
                "sha256": digest,
                "encoding": "zlib+base64",
                "content": base64.b64encode(zlib.compress(raw, level=6)).decode("ascii"),
            }
        parent[key] = f"asset://{digest}"
    if assets:
        packed["embedded_assets"] = assets
    return packed


def _materialize_assets(payload: dict[str, Any], cache_dir: Path) -> dict[str, Any]:
    assets = payload.get("embedded_assets")
    if not isinstance(assets, dict) or not assets:
        return payload
    if len(assets) > MAX_EMBEDDED_ASSETS:
        raise ValueError("Project asset limit exceeded")
    materialized = deepcopy(payload)
    cache_dir.mkdir(parents=True, exist_ok=True)
    decoded: dict[str, Path] = {}
    total = 0
    for digest, record in assets.items():
        if not isinstance(record, dict) or not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Invalid embedded asset identifier")
        suffix = str(record.get("suffix", "")).lower()
        if suffix not in ASSET_EXTENSIONS or record.get("sha256") != digest or record.get("encoding") != "zlib+base64":
            raise ValueError("Invalid embedded asset metadata")
        encoded = str(record.get("content", ""))
        if len(encoded) > MAX_ASSET_BYTES * 2:
            raise ValueError("Embedded asset exceeds encoded size limit")
        compressed = base64.b64decode(encoded, validate=True)
        decompressor = zlib.decompressobj()
        raw = decompressor.decompress(compressed, MAX_ASSET_BYTES + 1)
        if len(raw) > MAX_ASSET_BYTES or decompressor.unconsumed_tail:
            raise ValueError("Embedded asset decompression size limit exceeded")
        raw += decompressor.flush(MAX_ASSET_BYTES + 1 - len(raw))
        if not decompressor.eof or len(raw) > MAX_ASSET_BYTES:
            raise ValueError("Invalid or oversized embedded asset")
        total += len(raw)
        if total > MAX_TOTAL_ASSET_BYTES or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Embedded asset exceeds total size limit or checksum mismatch")
        # A content-addressed directory prevents collisions while retaining the
        # original filename in RasterMint's source/reference displays.
        original_name = str(record.get("name") or f"asset{suffix}")
        safe_name = Path(original_name.replace("\\", "/")).name
        if safe_name in {"", ".", ".."}:
            safe_name = f"asset{suffix}"
        if Path(safe_name).suffix.lower() != suffix:
            safe_name = Path(safe_name).stem + suffix
        output = cache_dir / digest / safe_name
        if not output.is_file() or hashlib.sha256(output.read_bytes()).hexdigest() != digest:
            _atomic_write_bytes(output, raw)
        decoded[digest] = output
    for parent, key, value in _walk_references(materialized):
        if value.startswith("asset://"):
            digest = value.removeprefix("asset://")
            if digest not in decoded:
                raise ValueError("Missing embedded project asset")
            parent[key] = str(decoded[digest])
    # Avoid large blobs being kept in backend settings / memory.
    materialized.pop("embedded_assets", None)
    return materialized


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def save_project_file(path: str | Path, payload: dict[str, Any], *, package_assets: bool = False) -> Path:
    target = Path(path)
    if target.suffix.lower() != ".rastermint":
        target = target.with_suffix(".rastermint")
    document = {
        "schema": PROJECT_SCHEMA,
        "schema_version": PROJECT_VERSION,
        **dict(payload),
    }
    if package_assets:
        document = _add_embedded_assets(document, target.parent)
    _atomic_write_bytes(target, (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return target


def load_project_file(path: str | Path, *, extract_assets_to: str | Path | None = None) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != PROJECT_SCHEMA:
        raise ValueError("This is not a RasterMint project file.")
    version = int(payload.get("schema_version", 0) or 0)
    if version != PROJECT_VERSION:
        raise ValueError(f"Unsupported RasterMint project schema version: {version}")
    if extract_assets_to is not None:
        return _materialize_assets(payload, Path(extract_assets_to))
    return payload
