#!/usr/bin/env bash
# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="python3"
[[ -x .venv/bin/python ]] && PYTHON=".venv/bin/python"

"$PYTHON" -m pip install -e '.[build]'
"$PYTHON" -m PyInstaller build/rastermint.spec --noconfirm --clean

if [[ ! -f dist/RasterMint ]]; then
    echo "PyInstaller did not create dist/RasterMint" >&2
    exit 1
fi

mkdir -p release
rm -f release/RasterMint-linux-x86_64.tar.gz
# tar preserves the executable bit, unlike a bare GitHub artifact download.
tar -C dist -czf release/RasterMint-linux-x86_64.tar.gz RasterMint
echo "Built release/RasterMint-linux-x86_64.tar.gz"
