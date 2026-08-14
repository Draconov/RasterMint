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
tar -C dist -czf release/RasterMint-linux-x86_64.tar.gz RasterMint
echo "Built release/RasterMint-linux-x86_64.tar.gz"
