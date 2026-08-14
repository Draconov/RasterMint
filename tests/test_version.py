# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from pathlib import Path

import rastermint


def test_runtime_version_matches_version_file() -> None:
    root = Path(__file__).resolve().parents[1]
    expected = (root / "VERSION").read_text(encoding="utf-8").strip()
    assert expected
    assert rastermint.__version__ == expected
