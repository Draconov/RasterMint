# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_qml_backend_import_graph_does_not_eagerly_import_render_pipeline():
    forbidden = {
        "numpy",
        "PIL",
        "PIL.Image",
        "rastermint.core.batch",
        "rastermint.core.effect_stack",
        "rastermint.core.gif_export",
        "rastermint.core.hardware",
        "rastermint.core.media",
        "rastermint.core.palette",
        "rastermint.core.processor",
        "rastermint.core.svg_export",
    }
    startup_modules = (
        SRC / "rastermint/qmlui/backend.py",
        SRC / "rastermint/qmlui/export_backend.py",
        SRC / "rastermint/qmlui/preferences_backend.py",
        SRC / "rastermint/qmlui/workers.py",
        SRC / "rastermint/qmlui/batch_worker.py",
    )
    for path in startup_modules:
        eager = _top_level_imports(path) & forbidden
        assert not eager, f"{path.name} eagerly imports heavy modules: {sorted(eager)}"


def test_animation_metadata_uses_light_effect_schema():
    imports = _top_level_imports(SRC / "rastermint/core/animation.py")
    assert "rastermint.core.effect_stack" not in imports
    assert "effect_stack" not in imports
    source = (SRC / "rastermint/core/animation.py").read_text(encoding="utf-8")
    assert "from .effect_schema import" in source


def test_app_defers_backend_import_until_main_runs():
    tree = ast.parse((SRC / "rastermint/app.py").read_text(encoding="utf-8"))
    top_level = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "rastermint.qmlui.export_backend" not in top_level
    assert "rastermint.qmlui.image_provider" not in top_level
    assert "rastermint.qmlui.theme" not in top_level


def test_runtime_prefers_frozen_lean_ffmpeg(tmp_path, monkeypatch):
    from rastermint.core.ffmpeg_runtime import configure_bundled_ffmpeg

    folder = tmp_path / "rastermint_ffmpeg"
    folder.mkdir()
    name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    executable = folder / name
    executable.write_bytes(b"test")

    monkeypatch.delenv("IMAGEIO_FFMPEG_EXE", raising=False)
    monkeypatch.delenv("RASTERMINT_FFMPEG_EXE", raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert configure_bundled_ffmpeg() == str(executable)
    assert os.environ["IMAGEIO_FFMPEG_EXE"] == str(executable)


def test_ffmpeg_packaging_prefers_validated_override_and_manifest_is_lean():
    spec = (ROOT / "build/rastermint.spec").read_text(encoding="utf-8")
    assert 'os.environ.get("RASTERMINT_FFMPEG_EXE"' in spec
    assert '"rastermint_ffmpeg"' in spec
    assert "imageio_ffmpeg.get_ffmpeg_exe()" in spec  # safe local fallback
    assert "hook-imageio_ffmpeg.py" in spec

    hook = (ROOT / "build/hooks/hook-imageio_ffmpeg.py").read_text(encoding="utf-8")
    assert "collect_data_files" not in hook
    assert "datas = []" in hook

    payload = json.loads((ROOT / "build/ffmpeg-vcpkg/vcpkg.json").read_text(encoding="utf-8"))
    dependency = payload["dependencies"][0]
    assert dependency["name"] == "ffmpeg"
    assert dependency["default-features"] is False
    assert set(dependency["features"]) == {"ffmpeg", "swresample", "swscale", "x264", "zlib"}

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "!build/hooks/hook-imageio_ffmpeg.py" in gitignore
    assert "!build/ffmpeg-vcpkg/" in gitignore
    assert "!build/ffmpeg-vcpkg/vcpkg.json" in gitignore

    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "RASTERMINT_REQUIRE_LEAN_FFMPEG" not in workflow


def test_backend_import_stays_light_when_pyside6_is_available():
    pytest.importorskip("PySide6")
    code = r'''
import sys
# Establish a Qt-only baseline so optional imports performed internally by
# PySide6 itself are not misattributed to RasterMint's backend.
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtQml
import PySide6.QtQuick
before = set(sys.modules)
import rastermint.qmlui.export_backend
forbidden = {
    "rastermint.core.processor",
    "rastermint.core.effect_stack",
    "rastermint.core.hardware",
    "rastermint.core.media",
    "rastermint.core.gif_export",
    "rastermint.core.batch",
    "numpy",
    "PIL.Image",
}
loaded = sorted(name for name in forbidden if name in sys.modules and name not in before)
if loaded:
    raise SystemExit("eager heavy imports: " + ", ".join(loaded))
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
