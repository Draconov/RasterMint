from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "rastermint"


def test_qml_is_the_only_desktop_ui_tree():
    assert not (PACKAGE / "ui").exists()
    assert (PACKAGE / "qml" / "Main.qml").is_file()
    assert (PACKAGE / "qmlui" / "backend.py").is_file()


def test_default_theme_matches_rastermint_dark():
    path = PACKAGE / "data" / "themes" / "rastermint-dark.json"
    theme = json.loads(path.read_text(encoding="utf-8"))
    assert theme["id"] == "rastermint-dark"
    assert theme["name"] == "RasterMint Dark"
    assert theme["window"].upper() == "#15181D"
    assert theme["accent"].upper() == "#A5BD34"


def test_theme_files_have_required_keys():
    required = {
        "id", "name", "window", "canvas", "panel", "panelRaised", "panelHover",
        "border", "text", "textMuted", "accent", "accentHover", "accentText",
        "danger", "selection", "mirrorAxis",
    }
    files = list((PACKAGE / "data" / "themes").glob("*.json"))
    assert len(files) >= 6
    ids = set()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert required <= data.keys()
        assert data["id"] not in ids
        ids.add(data["id"])


def test_qml_files_are_packaged():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for pattern in ["data/themes/*.json", "qml/*.qml", "qml/components/*.qml", "qml/pages/*.qml"]:
        assert pattern in pyproject


def test_old_roadmap_is_not_restored():
    assert not (ROOT / "ROADMAP.md").exists()

def test_solarized_themes_use_canonical_colors():
    dark = json.loads((PACKAGE / "data" / "themes" / "solarized-dark.json").read_text(encoding="utf-8"))
    light = json.loads((PACKAGE / "data" / "themes" / "solarized-light.json").read_text(encoding="utf-8"))

    assert dark["id"] == "solarized-dark"
    assert dark["name"] == "Solarized Dark"
    assert dark["window"].upper() == "#002B36"  # base03
    assert dark["panel"].upper() == "#073642"   # base02
    assert dark["text"].upper() == "#839496"    # base0

    assert light["id"] == "solarized-light"
    assert light["name"] == "Solarized Light"
    assert light["window"].upper() == "#FDF6E3"  # base3
    assert light["panel"].upper() == "#EEE8D5"   # base2
    assert light["text"].upper() == "#657B83"    # base00

    for theme in (dark, light):
        assert theme["accent"].upper() == "#268BD2"
        assert theme["accentHover"].upper() == "#2AA198"
        assert theme["danger"].upper() == "#DC322F"
        assert theme["author"] == "Ethan Schoonover"
        assert theme["license"] == "MIT"

def test_linux_workflows_install_qt_runtime_libraries():
    for relative in [
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
    ]:
        workflow = (ROOT / relative).read_text(encoding="utf-8")
        assert "libegl1" in workflow
        assert "libgl1" in workflow
        assert "libopengl0" in workflow
        assert "libxkbcommon0" in workflow
        assert "libxcb-cursor0" in workflow
        assert "QT_QPA_PLATFORM: offscreen" in workflow
        assert "QSG_RHI_BACKEND: software" in workflow

