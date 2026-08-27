# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
from pathlib import Path

from rastermint.core.extensions import asset_directories, asset_files, load_extensions


def test_extension_manifest_discovers_safe_asset_directories(tmp_path: Path):
    ext = tmp_path / "example"
    themes = ext / "themes"
    palettes = ext / "palettes"
    themes.mkdir(parents=True)
    palettes.mkdir()
    (themes / "theme.json").write_text("{}", encoding="utf-8")
    (palettes / "palette.json").write_text("{}", encoding="utf-8")
    (ext / "extension.json").write_text(
        json.dumps({
            "format": "rastermint-extension",
            "schema_version": 1,
            "id": "example-pack",
            "name": "Example Pack",
            "version": "1.0",
            "assets": {"themes": "themes", "palettes": "palettes"},
        }),
        encoding="utf-8",
    )

    records = load_extensions(tmp_path)
    assert [record.id for record in records] == ["example-pack"]
    assert asset_directories("themes", root=tmp_path) == (themes.resolve(),)
    assert asset_files("palettes", root=tmp_path) == ((palettes / "palette.json").resolve(),)


def test_extension_manifest_rejects_asset_path_escape(tmp_path: Path):
    ext = tmp_path / "bad"
    ext.mkdir()
    (ext / "extension.json").write_text(
        json.dumps({
            "format": "rastermint-extension",
            "schema_version": 1,
            "id": "bad-pack",
            "name": "Bad Pack",
            "assets": {"themes": "../outside"},
        }),
        encoding="utf-8",
    )

    records = load_extensions(tmp_path)
    assert len(records) == 1
    assert records[0].assets == {}
