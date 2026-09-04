#!/usr/bin/env bash
# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="python3"
[[ -x .venv/bin/python ]] && PYTHON=".venv/bin/python"

"$PYTHON" -m pip install -e '.[build]'

imageio_ffmpeg_path() {
    "$PYTHON" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())' 2>/dev/null | tail -n 1
}

find_vcpkg() {
    local candidate=""
    if [[ -n "${VCPKG_INSTALLATION_ROOT:-}" ]]; then
        candidate="$VCPKG_INSTALLATION_ROOT/vcpkg"
        [[ -x "$candidate" ]] && { printf '%s\n' "$candidate"; return 0; }
    fi
    if command -v vcpkg >/dev/null 2>&1; then
        command -v vcpkg
        return 0
    fi
    return 1
}

validate_smaller_ffmpeg() {
    local candidate="$1"
    [[ -f "$candidate" && -x "$candidate" ]] || return 1

    echo "Validating lean RasterMint FFmpeg: $candidate"
    if ! "$PYTHON" scripts/validate_ffmpeg.py "$candidate"; then
        echo "WARNING: lean FFmpeg failed RasterMint's codec/media smoke tests." >&2
        return 1
    fi

    local reference
    reference="$(imageio_ffmpeg_path || true)"
    if [[ -f "$reference" ]]; then
        local candidate_bytes reference_bytes
        candidate_bytes="$(stat -c '%s' "$candidate")"
        reference_bytes="$(stat -c '%s' "$reference")"
        if (( candidate_bytes >= reference_bytes )); then
            echo "WARNING: lean FFmpeg is not smaller than imageio-ffmpeg; keeping the known-good bundled binary." >&2
            return 1
        fi
        "$PYTHON" - "$candidate_bytes" "$reference_bytes" <<'PY'
import sys
candidate = int(sys.argv[1])
reference = int(sys.argv[2])
print(f"Lean FFmpeg saves {(reference-candidate)/(1024*1024):.1f} MiB inside the one-file payload before compression.")
PY
    fi
    return 0
}

build_lean_ffmpeg() {
    local vcpkg
    if ! vcpkg="$(find_vcpkg)"; then
        echo "WARNING: vcpkg was not found; Linux build will use imageio-ffmpeg's bundled executable." >&2
        return 1
    fi

    local manifest_root="$PWD/build/ffmpeg-vcpkg"
    local work_root="$manifest_root/work-linux"
    local cache_root="$manifest_root/cache/linux"
    local install_root="$work_root/installed"
    local buildtrees="$work_root/buildtrees"
    local packages="$work_root/packages"
    local binary_cache="$cache_root/binary"
    local downloads="$cache_root/downloads"

    mkdir -p "$install_root" "$buildtrees" "$packages" "$binary_cache" "$downloads"
    export VCPKG_BINARY_SOURCES="clear;files,$binary_cache,readwrite"

    echo "Building/restoring RasterMint's lean static Linux FFmpeg with vcpkg..." >&2
    echo "vcpkg binary cache: $binary_cache" >&2
    # Send vcpkg's full log to stderr so command substitution receives only the
    # final executable path. This mirrors the Windows fix and avoids contaminating
    # RASTERMINT_FFMPEG_EXE with build output.
    if ! "$vcpkg" install \
        "--x-manifest-root=$manifest_root" \
        "--x-install-root=$install_root" \
        "--x-buildtrees-root=$buildtrees" \
        "--x-packages-root=$packages" \
        "--downloads-root=$downloads" \
        "--triplet=x64-linux" >&2; then
        echo "WARNING: vcpkg could not build the lean Linux FFmpeg." >&2
        return 1
    fi

    local candidate="$install_root/x64-linux/tools/ffmpeg/ffmpeg"
    if [[ ! -f "$candidate" ]]; then
        candidate="$(find "$install_root" -type f -name ffmpeg -not -path '*/debug/*' -print -quit)"
    fi
    [[ -f "$candidate" ]] || {
        echo "WARNING: vcpkg completed but no release ffmpeg executable was found." >&2
        return 1
    }

    # vcpkg's release tool can still contain symbol metadata depending on the
    # port/toolchain revision. Remove it before comparing/package validation.
    if command -v strip >/dev/null 2>&1; then
        strip --strip-unneeded "$candidate" 2>/dev/null || true
    fi
    chmod +x "$candidate"
    printf '%s\n' "$candidate"
}

LEAN_FFMPEG=""
if [[ -n "${RASTERMINT_FFMPEG_EXE:-}" ]]; then
    if validate_smaller_ffmpeg "$RASTERMINT_FFMPEG_EXE"; then
        LEAN_FFMPEG="$(realpath "$RASTERMINT_FFMPEG_EXE")"
    else
        echo "WARNING: ignoring invalid RASTERMINT_FFMPEG_EXE override." >&2
    fi
fi

if [[ -z "$LEAN_FFMPEG" ]]; then
    if candidate="$(build_lean_ffmpeg)" && validate_smaller_ffmpeg "$candidate"; then
        LEAN_FFMPEG="$(realpath "$candidate")"
    fi
fi

if [[ -n "$LEAN_FFMPEG" ]]; then
    export RASTERMINT_FFMPEG_EXE="$LEAN_FFMPEG"
    echo "PyInstaller will bundle lean Linux FFmpeg: $LEAN_FFMPEG"
else
    unset RASTERMINT_FFMPEG_EXE || true
    echo "WARNING: lean Linux FFmpeg is unavailable; falling back to imageio-ffmpeg's known-good executable." >&2
fi

"$PYTHON" -m PyInstaller build/rastermint.spec --noconfirm --clean

if [[ ! -f dist/RasterMint ]]; then
    echo "PyInstaller did not create dist/RasterMint" >&2
    exit 1
fi

mkdir -p release
rm -f release/RasterMint-linux-x86_64.tar.gz
# The one-file payload is already compressed internally, but maximum gzip is a
# free final pass over the outer archive and preserves the executable bit.
tar -C dist -cf - RasterMint | gzip -9 > release/RasterMint-linux-x86_64.tar.gz

"$PYTHON" - <<'PY'
from pathlib import Path
raw = Path("dist/RasterMint").stat().st_size / (1024 * 1024)
packed = Path("release/RasterMint-linux-x86_64.tar.gz").stat().st_size / (1024 * 1024)
print(f"Built release/RasterMint-linux-x86_64.tar.gz ({packed:.1f} MiB; one-file executable {raw:.1f} MiB)")
PY
