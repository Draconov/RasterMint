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
    if "\\" in name or ":" in name or "\x00" in name or name.startswith("/"):
        return None
    raw_parts = name.split("/")
    if not raw_parts or any(part in {"", ".", ".."} for part in raw_parts):
        return None
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


# Keep imported backup sizes bounded. Preview and import follow the exact same
# validation route; a ZIP is always validated before Replace deletes anything.
_MAX_BACKUP_BYTES = 256 * 1024 * 1024
_MAX_BACKUP_FILES = 5000


def _read_backup(source: Path) -> tuple[dict[str, object], list[tuple[str, Path, bytes]]]:
    """Read and validate the same archive members used for preview and import."""
    with ZipFile(source, "r") as archive:
        try:
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        except KeyError as exc:
            raise ValueError("backup is missing manifest.json") from exc
        except (ValueError, UnicodeError) as exc:
            raise ValueError("backup manifest is invalid") from exc
        if not isinstance(manifest, dict) or manifest.get("format") != "rastermint-user-content":
            raise ValueError("unsupported RasterMint backup format")
        if manifest.get("version") != 1:
            raise ValueError("unsupported RasterMint backup version")
        if not isinstance(manifest.get("collections"), dict):
            raise ValueError("backup collections must be a JSON object")
        members: list[tuple[str, Path, bytes]] = []
        seen: set[tuple[str, str]] = set()
        total = 0
        for info in archive.infolist():
            if info.is_dir() or info.filename == "manifest.json":
                continue
            resolved = _safe_archive_relative_path(info.filename)
            if resolved is None:
                raise ValueError("backup contains an unsafe or unsupported file path")
            root, rel = resolved
            if rel.suffix.lower() not in {".json", ".png", ".webp", ".jpg", ".jpeg"}:
                raise ValueError("backup contains an unsupported file type")
            # Reject Unix symlinks and duplicate filenames, including paths
            # that collide on Windows' case-insensitive filesystem.
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("backup contains a symbolic link")
            key = (root, rel.as_posix().casefold())
            if key in seen:
                raise ValueError("backup contains duplicate filenames")
            seen.add(key)
            total += info.file_size
            if total > _MAX_BACKUP_BYTES or len(seen) > _MAX_BACKUP_FILES:
                raise ValueError("backup exceeds size or file-count limits")
            payload = archive.read(info)
            if len(payload) != info.file_size:
                raise ValueError("backup contains a damaged file")
            if rel.suffix.lower() == ".json":
                try:
                    json.loads(payload.decode("utf-8"))
                except (UnicodeError, ValueError) as exc:
                    raise ValueError("backup contains an invalid JSON file") from exc
            members.append((root, rel, payload))
        return manifest, members


def preview_user_content(source: Path, data_root: Path) -> dict[str, int]:
    """Report what an archive will restore, without modifying user data."""
    manifest, members = _read_backup(Path(source))
    collections = manifest["collections"]
    def number(key: str) -> int:
        value = collections.get(key, [])
        return len(value) if isinstance(value, list) else 0
    return {
        "files": len(members),
        "presets": sum(root == "presets" and rel.suffix.lower() == ".json" for root, rel, _ in members),
        "palettes": sum(root == "palettes" and rel.suffix.lower() == ".json" for root, rel, _ in members),
        "matrices": number("customDitherMatricesV1"),
        "animations": number("animationClipLibraryV1"),
        "saved_palettes": number("userPalettesV1"),
        "categories": len(collections.get("presetLibraryMetaV1", {}).get("categories", {}))
            if isinstance(collections.get("presetLibraryMetaV1"), dict)
            and isinstance(collections["presetLibraryMetaV1"].get("categories", {}), dict) else 0,
        "conflicts": sum((Path(data_root) / root / rel).exists() for root, rel, _ in members),
    }


def import_user_content(source: Path, data_root: Path, *, mode: str = "merge") -> tuple[int, dict[str, object]]:
    """Restore validated library files and return the QSettings collections."""
    data_root = Path(data_root)
    mode = str(mode or "merge").strip().casefold()
    if mode not in {"merge", "replace"}:
        raise ValueError("unsupported import mode")
    manifest, members = _read_backup(Path(source))
    # Never traverse symlinked library roots or ancestor directories inside the
    # managed libraries. This is particularly important for Replace.
    for root in LIBRARY_DIRECTORIES:
        directory = data_root / root
        if directory.is_symlink():
            raise ValueError("user library is a symbolic link")
    for root, rel, _ in members:
        target = data_root / root / rel
        if any(ancestor.is_symlink() for ancestor in target.parents if ancestor != data_root.parent):
            raise ValueError("backup target traverses a symbolic link")
    if mode == "replace":
        for dirname in LIBRARY_DIRECTORIES:
            directory = data_root / dirname
            if directory.exists():
                shutil.rmtree(directory)
    for root, rel, payload in members:
        target = data_root / root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return len(members), manifest["collections"]
