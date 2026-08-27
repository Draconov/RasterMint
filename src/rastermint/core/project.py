# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_SCHEMA = "rastermint-project"
PROJECT_VERSION = 1


def save_project_file(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    if target.suffix.lower() != ".rastermint":
        target = target.with_suffix(".rastermint")
    document = {
        "schema": PROJECT_SCHEMA,
        "schema_version": PROJECT_VERSION,
        **dict(payload),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def load_project_file(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != PROJECT_SCHEMA:
        raise ValueError("This is not a RasterMint project file.")
    version = int(payload.get("schema_version", 0) or 0)
    if version < 1 or version > PROJECT_VERSION:
        raise ValueError(f"Unsupported RasterMint project schema version: {version}")
    return payload
