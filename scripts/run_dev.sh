#!/usr/bin/env bash
# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="python3"
[[ -x .venv/bin/python ]] && PYTHON=".venv/bin/python"
exec "$PYTHON" -m rastermint
