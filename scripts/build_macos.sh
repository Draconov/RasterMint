#!/usr/bin/env bash
# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="python3"
[[ -x .venv/bin/python ]] && PYTHON=".venv/bin/python"

"$PYTHON" -m pip install -e '.[build]'
"$PYTHON" -m PyInstaller build/rastermint.spec --noconfirm --clean
mkdir -p release
rm -f release/RasterMint-macos.zip
if [[ -d dist/RasterMint.app ]]; then
  ditto -c -k --sequesterRsrc --keepParent dist/RasterMint.app release/RasterMint-macos.zip
else
  ditto -c -k --sequesterRsrc --keepParent dist/RasterMint release/RasterMint-macos.zip
fi
echo "Built release/RasterMint-macos.zip"
