#!/usr/bin/env bash
# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="python3"
[[ -x .venv/bin/python ]] && PYTHON=".venv/bin/python"

"$PYTHON" -m pip install -e '.[build]'
"$PYTHON" -m PyInstaller build/rastermint.spec --noconfirm --clean

if [[ ! -d dist/RasterMint.app ]]; then
    echo "PyInstaller did not create dist/RasterMint.app" >&2
    exit 1
fi

mkdir -p release
rm -f release/RasterMint-macOS.zip
ditto -c -k --sequesterRsrc --keepParent dist/RasterMint.app release/RasterMint-macOS.zip
echo "Built release/RasterMint-macOS.zip"
