# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_versions() -> tuple[str, str]:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    init = (ROOT / "src/rastermint/__init__.py").read_text(encoding="utf-8")
    p = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    i = re.search(r'^__version__\s*=\s*"([^"]+)"', init, re.MULTILINE)
    if not p or not i:
        raise SystemExit("Could not locate version declarations")
    return p.group(1), i.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="Optional git tag, e.g. v0.1.0")
    args = parser.parse_args()

    package_version, app_version = read_versions()
    if package_version != app_version:
        raise SystemExit(f"Version mismatch: pyproject={package_version}, app={app_version}")
    if args.tag:
        tag_version = args.tag.removeprefix("v")
        if tag_version != package_version:
            raise SystemExit(f"Tag {args.tag} does not match project version {package_version}")
    print(f"Version OK: {package_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
