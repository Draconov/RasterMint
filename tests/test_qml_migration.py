from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "rastermint"


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


def test_custom_qml_popups_are_forced_into_the_quick_scene():
    main = (PACKAGE / "qml" / "Main.qml").read_text(encoding="utf-8")
    combo = (PACKAGE / "qml" / "components" / "MintComboBox.qml").read_text(encoding="utf-8")
    layers = (PACKAGE / "qml" / "pages" / "LayersPage.qml").read_text(encoding="utf-8")
    settings = (PACKAGE / "qml" / "SettingsDialog.qml").read_text(encoding="utf-8")
    about = (PACKAGE / "qml" / "AboutDialog.qml").read_text(encoding="utf-8")

    # Qt 6.8+ can choose Window/Native popup implementations by style/platform.
    # RasterMint customizes these controls, so keep them in the same Quick scene.
    mint_menu = (PACKAGE / "qml" / "components" / "MintMenu.qml").read_text(encoding="utf-8")
    assert "popupType: Popup.Item" in mint_menu
    assert main.count("MintMenu {") >= 3
    assert "popupType: Popup.Item" in combo
    assert "popupType: Popup.Item" in layers
    assert "popupType: Popup.Item" in settings
    assert "popupType: Popup.Item" in about


def test_application_disables_native_menu_promotion_before_qguiapplication():
    app_py = (PACKAGE / "app.py").read_text(encoding="utf-8")
    dont_bar = "AA_DontUseNativeMenuBar"
    dont_windows = "AA_DontUseNativeMenuWindows"
    create_app = "app = QGuiApplication(sys.argv)"

    assert dont_bar in app_py
    assert dont_windows in app_py
    assert app_py.index(dont_bar) < app_py.index(create_app)
    assert app_py.index(dont_windows) < app_py.index(create_app)


def test_empty_drop_prompt_is_centered_and_not_duplicated_by_status_overlay():
    main = (PACKAGE / "qml" / "Main.qml").read_text(encoding="utf-8")
    canvas = (PACKAGE / "qml" / "ImageCanvas.qml").read_text(encoding="utf-8")

    assert 'objectName: "emptyDropPrompt"' in canvas
    assert "anchors.centerIn: parent" in canvas
    assert 'text: qsTr("Open or drop an image, GIF, or video to begin")' in canvas
    assert "visible: backend.statusText.length > 0" in main


def test_qml_file_dialogs_pass_normalized_urls_to_backend():
    main = (PACKAGE / "qml" / "Main.qml").read_text(encoding="utf-8")
    palette = (PACKAGE / "qml" / "pages" / "PalettePage.qml").read_text(encoding="utf-8")
    presets = (PACKAGE / "qml" / "pages" / "PresetsPage.qml").read_text(encoding="utf-8")
    hardware = (PACKAGE / "qml" / "pages" / "HardwarePage.qml").read_text(encoding="utf-8")

    # Only verify the QML/Python boundary contract here. Menu wording, visual
    # layout and implementation details are exercised by QML runtime smoke
    # tests instead of brittle exact-source assertions.
    required_main_calls = {
        "backend.openFile(window.urlString(selectedFile))",
        "backend.exportImage(window.urlString(selectedFile))",
        "backend.exportToClipboard()",
        "backend.exportMedia(window.urlString(selectedFile))",
        "backend.exportSequence(window.urlString(selectedFolder))",
        "window.urlStrings(selectedFiles)",
        "window.urlString(selectedFolder)",
        "backend.loadPreset(window.urlString(selectedFile))",
        "backend.savePreset(window.urlString(selectedFile))",
    }
    for call in required_main_calls:
        assert call in main
    assert "selectedFile.toString()" in palette
    assert "selectedFile.toString()" in presets
    assert "selectedFile.toString()" in hardware


def test_mirror_axes_preserve_backend_position_bindings_while_dragging():
    canvas = (PACKAGE / "qml" / "ImageCanvas.qml").read_text(encoding="utf-8")
    assert "drag.target:" not in canvas
    assert 'backend.setMirrorAxis("horizontal"' in canvas
    assert 'backend.setMirrorAxis("vertical"' in canvas
    assert "mapToItem(imageFrame" in canvas


def test_every_backend_method_called_by_qml_exists_in_backend_class():
    import re

    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in (PACKAGE / "qml").rglob("*.qml"))
    # The QML backend is composed through inheritance: export_backend ->
    # preferences_backend -> backend. Scan the complete runtime API instead of
    # incorrectly treating backend.py as the only implementation file.
    backend_files = [
        PACKAGE / "qmlui" / "backend.py",
        PACKAGE / "qmlui" / "preferences_backend.py",
        PACKAGE / "qmlui" / "export_backend.py",
    ]
    backend_text = "\n".join(path.read_text(encoding="utf-8") for path in backend_files if path.is_file())
    called = set(re.findall(r"\bbackend\.([A-Za-z_][A-Za-z0-9_]*)\s*\(", qml_text))
    defined = set(re.findall(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", backend_text, re.MULTILINE))
    missing = sorted(called - defined)
    assert not missing, f"QML calls backend methods that do not exist: {missing}"


def test_add_layer_popup_is_anchored_to_its_button():
    layers = (PACKAGE / "qml" / "pages" / "LayersPage.qml").read_text(encoding="utf-8")
    assert 'objectName: "addLayerButton"' in layers
    assert "mapToItem(Overlay.overlay" in layers
    assert "parent: Overlay.overlay" in layers


def test_theme_chooser_order_and_new_themes_are_stable():
    theme_py = (PACKAGE / "qmlui" / "theme.py").read_text(encoding="utf-8")
    expected = [
        "rastermint-dark",
        "rastermint-light",
        "oled",
        "trueblack",
        "solarized-dark",
        "solarized-light",
        "mint",
        "sunrise",
        "halloween",
    ]
    positions = [theme_py.index(f'"{theme_id}"') for theme_id in expected]
    assert positions == sorted(positions)

    sunrise = json.loads((PACKAGE / "data" / "themes" / "sunrise.json").read_text(encoding="utf-8"))
    halloween = json.loads((PACKAGE / "data" / "themes" / "halloween.json").read_text(encoding="utf-8"))
    trueblack = json.loads((PACKAGE / "data" / "themes" / "trueblack.json").read_text(encoding="utf-8"))

    assert sunrise["name"] == "Sunrise"
    assert sunrise["window"].upper() == "#655561"
    assert sunrise["accent"].upper() == "#FCB08C"
    assert "#8FA0BF" in [c.upper() for c in sunrise["paletteSource"]]
    assert halloween["name"] == "Halloween"
    assert halloween["accent"].upper() == "#FF7A18"
    assert halloween["window"].upper() == "#160D1D"
    assert trueblack["name"] == "TrueBlack"
    assert trueblack["window"] == "#000000"
    assert trueblack["panel"] == "#000000"


def test_settings_and_about_dialogs_remain_separate_qml_components():
    settings = PACKAGE / "qml" / "SettingsDialog.qml"
    about = PACKAGE / "qml" / "AboutDialog.qml"
    assert settings.is_file()
    assert about.is_file()
    # Syntax/theme binding regressions are covered by test_qml_runtime, which
    # compiles every QML component with the actual Qt engine in CI.
