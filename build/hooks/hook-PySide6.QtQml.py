# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Lean PyInstaller hook for RasterMint's PySide6.QtQml dependency.

PyInstaller's stock QtQml hook copies every QML module shipped by PySide6.
That includes large optional families such as WebEngine and Quick3D even when
RasterMint never imports them. This hook asks Qt's qmlimportscanner which QML
modules RasterMint actually uses, expands their QML-level dependencies, and
copies only those module directories.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path, PurePath
import re
import shutil
import subprocess

from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
APP_QML_DIR = ROOT / "src" / "rastermint" / "qml"

# Keep PyInstaller's normal dependency collection for the QtQml Python module
# and linked Qt libraries. We only replace the stock hook's "copy all QML"
# behavior.
hiddenimports, binaries, datas = add_qt6_dependencies(__file__)

_MODULE_RE = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")
_QML_IMPORT_RE = re.compile(r"(?m)^\s*import\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\b")
_QMLDIR_DEP_RE = re.compile(
    r"^\s*(?:(?:optional)\s+)?(?:depends|import)\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\b"
)


def _qml_root() -> Path:
    location = pyside6_library_info.location
    raw = location.get("QmlImportsPath") or location.get("Qml2ImportsPath")
    if not raw:
        raise RuntimeError("PySide6 did not report a Qt QML import path")
    path = Path(raw).resolve()
    if not path.is_dir():
        raise RuntimeError(f"Qt QML import path does not exist: {path}")
    return path


def _find_qmlimportscanner() -> str:
    # Prefer the PySide wrapper when it is on PATH (GitHub Actions / activated
    # virtualenvs). Fall back to Qt's bundled binary for local build scripts
    # that invoke .venv\\Scripts\\python.exe without activating the venv.
    for name in ("pyside6-qmlimportscanner", "qmlimportscanner"):
        candidate = shutil.which(name)
        if candidate:
            return candidate

    location = pyside6_library_info.location
    exe_name = "qmlimportscanner.exe" if os.name == "nt" else "qmlimportscanner"
    for key in ("LibraryExecutablesPath", "BinariesPath", "PrefixPath"):
        raw = location.get(key)
        if not raw:
            continue
        candidate = Path(raw) / exe_name
        if candidate.is_file():
            return str(candidate)

    raise RuntimeError(
        "Could not locate qmlimportscanner. PySide6 is installed, but its QML scanner is missing."
    )


def _scan_app_modules(qml_root: Path) -> set[str]:
    if not APP_QML_DIR.is_dir():
        raise RuntimeError(f"RasterMint QML source directory is missing: {APP_QML_DIR}")

    scanner = _find_qmlimportscanner()
    command = [
        scanner,
        "-rootPath",
        str(APP_QML_DIR),
        "-importPath",
        str(qml_root),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "qmlimportscanner failed with exit code "
            f"{result.returncode}:\n{result.stderr.strip() or result.stdout.strip()}"
        )

    output = result.stdout.strip()
    start = output.find("[")
    end = output.rfind("]")
    if start < 0 or end < start:
        raise RuntimeError(f"qmlimportscanner returned unexpected output:\n{output}")

    try:
        records = json.loads(output[start : end + 1])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse qmlimportscanner output: {exc}") from exc

    modules = {
        str(record.get("name"))
        for record in records
        if isinstance(record, dict)
        and record.get("type") == "module"
        and isinstance(record.get("name"), str)
        and _MODULE_RE.match(record["name"])
    }

    # RasterMint selects Basic dynamically from Python before loading QML, so
    # the source scanner cannot reliably infer this style module on its own.
    modules.add("QtQuick.Controls.Basic")

    if not modules:
        raise RuntimeError("qmlimportscanner found no Qt QML modules for RasterMint")
    return modules


def _module_dir(qml_root: Path, module_name: str) -> Path:
    return qml_root.joinpath(*module_name.split("."))


def _module_dependencies(qml_root: Path, module_name: str) -> set[str]:
    """Read dependencies without descending into sibling/child QML modules."""
    module_dir = _module_dir(qml_root, module_name)
    if not module_dir.is_dir():
        return set()

    dependencies: set[str] = set()
    qmldir = module_dir / "qmldir"
    if qmldir.is_file():
        for line in qmldir.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = _QMLDIR_DEP_RE.match(line)
            if match:
                dependencies.add(match.group(1))

    # Composite QML files can import implementation/template modules that are
    # not necessarily listed as qmldir dependencies. Parse those imports too,
    # while pruning nested directories that are independent QML modules (for
    # example the other Qt Quick Controls styles we do not want to package).
    for current_root, dirs, files in os.walk(module_dir):
        current = Path(current_root)
        dirs[:] = [name for name in dirs if not (current / name / "qmldir").is_file()]
        for filename in files:
            if not filename.endswith(".qml"):
                continue
            source = (current / filename).read_text(encoding="utf-8", errors="ignore")
            dependencies.update(_QML_IMPORT_RE.findall(source))

    return {
        name
        for name in dependencies
        if _MODULE_RE.match(name) and _module_dir(qml_root, name).is_dir()
    }


def _dependency_closure(qml_root: Path, initial: set[str]) -> list[str]:
    selected = set(initial)
    pending = list(initial)
    while pending:
        module_name = pending.pop()
        for dependency in _module_dependencies(qml_root, module_name):
            if dependency not in selected:
                selected.add(dependency)
                pending.append(dependency)
    return sorted(selected)


def _dest_dir(qml_root: Path, qml_dest_root: PurePath, source: Path) -> PurePath:
    relative = source.relative_to(qml_root)
    return qml_dest_root / (relative if source.is_dir() else relative.parent)


def _dedupe(items):
    seen = set()
    output = []
    for item in items:
        key = tuple(map(str, item)) if isinstance(item, tuple) else str(item)
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


qml_root = _qml_root()
selected_modules = _dependency_closure(qml_root, _scan_app_modules(qml_root))
qml_dest_root = PurePath(pyside6_library_info.qt_rel_dir) / "qml"

selected_binaries = []
selected_datas = []
for module_name in selected_modules:
    module_dir = _module_dir(qml_root, module_name)
    qmldir_file = module_dir / "qmldir"
    if not qmldir_file.is_file():
        # Some modules are provided entirely by linked C++ libraries and have
        # no deployable QML directory. Their Qt libraries are already handled
        # by add_qt6_dependencies().
        continue

    module_binaries, module_datas = pyside6_library_info._process_qml_plugin(qmldir_file)
    selected_binaries.extend(
        (str(source), str(_dest_dir(qml_root, qml_dest_root, source)))
        for source in module_binaries
    )
    selected_datas.extend(
        (str(source), str(_dest_dir(qml_root, qml_dest_root, source)))
        for source in module_datas
    )

binaries = _dedupe(binaries + selected_binaries)
datas = _dedupe(datas + selected_datas)

logger.info(
    "RasterMint lean Qt QML hook: %d modules selected: %s",
    len(selected_modules),
    ", ".join(selected_modules),
)
