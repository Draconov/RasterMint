# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Portable backup of user-created RasterMint libraries (no cache or source files)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile


LIBRARY_DIRECTORIES = ("presets", "palettes")


def export_user_content(destination: Path, data_root: Path, collections: dict[str, object]) -> int:
    """Export library files and QSettings-backed user collections to a ZIP.

    The archive includes user-created content, not application preferences,
    media, bundled profiles, or cache. Symlinks are ignored to avoid exporting
    arbitrary files outside RasterMint's data directory.
    """
    destination = Path(destination)
    data_root = Path(data_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps({
            "format": "rastermint-user-content", "version": 1,
            "libraries": list(LIBRARY_DIRECTORIES), "collections": collections,
        }, ensure_ascii=False, indent=2) + "\n")
        for dirname in LIBRARY_DIRECTORIES:
            directory = data_root / dirname
            if not directory.is_dir() or directory.is_symlink():
                continue
            for path in sorted(directory.rglob("*")):
                if not path.is_file() or path.is_symlink():
                    continue
                if path.suffix.lower() not in {".json", ".png", ".webp", ".jpg", ".jpeg"}:
                    continue
                archive.write(path, f"{dirname}/{path.relative_to(directory).as_posix()}")
                count += 1
    return count


def _safe_archive_relative_path(name: str) -> tuple[str, Path] | None:
    pure = PurePosixPath(name)
    parts = pure.parts
    if not parts or pure.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        return None
    root = parts[0]
    if root not in LIBRARY_DIRECTORIES or len(parts) < 2:
        return None
    rel = Path(*parts[1:])
    if any(part in {"", ".", ".."} for part in rel.parts):
        return None
    return root, rel


def import_user_content(source: Path, data_root: Path, *, mode: str = "merge") -> tuple[int, dict[str, object]]:
    """Import a RasterMint user-content backup ZIP.

    Returns ``(file_count, collections)``. ``mode`` can be ``merge`` or ``replace``.
    Replace clears the managed library folders before restoring the archive.
    """
    source = Path(source)
    data_root = Path(data_root)
    mode = str(mode or "merge").strip().casefold()
    if mode not in {"merge", "replace"}:
        raise ValueError("unsupported import mode")

    with ZipFile(source, "r") as archive:
        try:
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        except KeyError as exc:
            raise ValueError("backup is missing manifest.json") from exc
        except Exception as exc:
            raise ValueError("backup manifest could not be read") from exc

        if not isinstance(manifest, dict) or manifest.get("format") != "rastermint-user-content":
            raise ValueError("unsupported RasterMint backup format")
        if int(manifest.get("version", 0)) != 1:
            raise ValueError("unsupported RasterMint backup version")
        collections = manifest.get("collections")
        if not isinstance(collections, dict):
            collections = {}

        members: list[tuple[str, Path, bytes]] = []
        for info in archive.infolist():
            if info.is_dir() or info.filename == "manifest.json":
                continue
            resolved = _safe_archive_relative_path(info.filename)
            if resolved is None:
                continue
            root, rel = resolved
            if rel.suffix.lower() not in {".json", ".png", ".webp", ".jpg", ".jpeg"}:
                continue
            members.append((root, rel, archive.read(info)))

    if mode == "replace":
        for dirname in LIBRARY_DIRECTORIES:
            directory = data_root / dirname
            if directory.exists() and not directory.is_symlink():
                shutil.rmtree(directory)

    count = 0
    for root, rel, payload in members:
        target = data_root / root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        count += 1
    return count, collections
