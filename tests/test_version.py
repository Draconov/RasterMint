# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from pathlib import Path

import rastermint


def test_runtime_version_matches_version_file() -> None:
    root = Path(__file__).resolve().parents[1]
    expected = (root / "VERSION").read_text(encoding="utf-8").strip()
    assert expected
    assert rastermint.__version__ == expected


def test_v071_group_fix_update_version():
    root = Path(__file__).resolve().parents[1]
    assert (root / "VERSION").read_text(encoding="utf-8").strip() == "0.7.1"
