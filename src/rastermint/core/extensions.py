# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable

EXTENSION_FORMAT = "rastermint-extension"
EXTENSION_VERSION = 1
ASSET_KINDS = frozenset({"palettes", "themes", "translations", "hardware_profiles", "presets"})
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True, slots=True)
class ExtensionRecord:
    id: str
    name: str
    version: str
    root: Path
    assets: dict[str, Path]


def user_data_root() -> Path:
    """Return RasterMint's per-user data directory without requiring Qt.

    ``RASTERMINT_DATA_DIR`` exists primarily for portable/testing installs. The
    platform fallbacks mirror the normal application-data conventions used by
    Qt closely enough that CLI and GUI extension discovery agree.
    """
    override = str(os.environ.get("RASTERMINT_DATA_DIR", "")).strip()
    if override:
        return Path(override).expanduser()
    home = Path.home()
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or home)
        return base / "RasterMint"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "RasterMint"
    base = Path(os.environ.get("XDG_DATA_HOME") or (home / ".local" / "share"))
    return base / "RasterMint"


def extensions_root() -> Path:
    return user_data_root() / "extensions"


def _contained_path(root: Path, value: object) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = (root / text).resolve()
    resolved_root = root.resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return None
    return candidate


def _parse_extension(directory: Path) -> ExtensionRecord | None:
    manifest = directory / "extension.json"
    if not manifest.is_file():
        return None
    try:
        payload: Any = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict) or payload.get("format") != EXTENSION_FORMAT:
        return None
    try:
        version_number = int(payload.get("schema_version", payload.get("version_schema", EXTENSION_VERSION)))
    except (TypeError, ValueError):
        return None
    if version_number != EXTENSION_VERSION:
        return None

    extension_id = str(payload.get("id", "")).strip().lower()
    name = str(payload.get("name", "")).strip()
    if not extension_id or not _ID_RE.fullmatch(extension_id) or not name:
        return None

    raw_assets = payload.get("assets")
    assets: dict[str, Path] = {}
    if isinstance(raw_assets, dict):
        for kind, relative in raw_assets.items():
            key = str(kind)
            if key not in ASSET_KINDS:
                continue
            path = _contained_path(directory, relative)
            if path is not None and path.is_dir():
                assets[key] = path

    return ExtensionRecord(
        id=extension_id,
        name=name,
        version=str(payload.get("version", "1.0")),
        root=directory,
        assets=assets,
    )


def load_extensions(root: str | Path | None = None) -> tuple[ExtensionRecord, ...]:
    base = Path(root) if root is not None else extensions_root()
    if not base.is_dir():
        return ()
    records: list[ExtensionRecord] = []
    seen: set[str] = set()
    for directory in sorted((item for item in base.iterdir() if item.is_dir()), key=lambda p: p.name.casefold()):
        record = _parse_extension(directory)
        if record is None or record.id in seen:
            continue
        seen.add(record.id)
        records.append(record)
    return tuple(records)


def asset_directories(kind: str, *, root: str | Path | None = None) -> tuple[Path, ...]:
    key = str(kind)
    if key not in ASSET_KINDS:
        return ()
    result: list[Path] = []
    for extension in load_extensions(root):
        path = extension.assets.get(key)
        if path is not None:
            result.append(path)
    return tuple(result)


def asset_files(
    kind: str,
    *,
    suffixes: Iterable[str] = (".json",),
    root: str | Path | None = None,
) -> tuple[Path, ...]:
    allowed = {str(value).lower() for value in suffixes}
    files: list[Path] = []
    for directory in asset_directories(kind, root=root):
        for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
            if path.is_file() and path.suffix.lower() in allowed:
                files.append(path)
    return tuple(files)
