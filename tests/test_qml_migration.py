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



def test_preview_mode_buttons_use_supported_selected_property():
    button = (PACKAGE / "qml" / "components" / "MintButton.qml").read_text(encoding="utf-8")
    preview = (PACKAGE / "qml" / "pages" / "PreviewPage.qml").read_text(encoding="utf-8")

    assert "property bool selected: false" in button
    assert "control.selected || control.down" in button
    assert "selected: backend.previewMode === modelData" in preview
    assert "background.color:" not in preview


def test_qml_pages_do_not_override_custom_control_background_subproperties():
    # QML controls expose `background` as an Item. Assigning `background.color`
    # from an instance is invalid because the static type does not guarantee a
    # `color` property even when our component happens to use a Rectangle.
    for path in (PACKAGE / "qml").rglob("*.qml"):
        if path.name == "MintButton.qml":
            continue
        text = path.read_text(encoding="utf-8")
        assert "background.color:" not in text, path

def test_qml_does_not_separate_child_or_grouped_blocks_with_semicolons():
    # A closing QML object/grouped-property block must not be followed by a
    # semicolon before the next child object/property. This is easy to create
    # when compacting QML onto one line and causes `Unexpected token ;`.
    import re

    bad = re.compile(r"}\s*;\s*(?=(?:[A-Z][A-Za-z0-9_.]*\s*\{|[A-Za-z_][A-Za-z0-9_.]*\s*:))")
    for path in (PACKAGE / "qml").rglob("*.qml"):
        text = path.read_text(encoding="utf-8")
        match = bad.search(text)
        assert match is None, f"invalid QML block separator in {path}: {match.group(0)!r}" if match else ""

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
    assert 'text: "Open or drop an image, GIF, or video to begin"' in canvas
    assert "visible: backend.statusText.length > 0" in main


def test_qml_dialog_urls_are_normalized_before_python_slots():
    main = (PACKAGE / "qml" / "Main.qml").read_text(encoding="utf-8")
    palette = (PACKAGE / "qml" / "pages" / "PalettePage.qml").read_text(encoding="utf-8")
    presets = (PACKAGE / "qml" / "pages" / "PresetsPage.qml").read_text(encoding="utf-8")
    hardware = (PACKAGE / "qml" / "pages" / "HardwarePage.qml").read_text(encoding="utf-8")

    assert "backend.openFile(window.urlString(selectedFile))" in main
    assert "backend.exportImage(window.urlString(selectedFile))" in main
    assert "backend.exportMedia(window.urlString(selectedFile))" in main
    assert "backend.exportSequence(window.urlString(selectedFolder))" in main
    assert "window.urlStrings(selectedFiles)" in main
    assert "window.urlString(selectedFolder)" in main
    assert "backend.loadPreset(window.urlString(selectedFile))" in main
    assert "backend.savePreset(window.urlString(selectedFile))" in main
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




def test_top_bar_uses_explicit_popup_buttons_instead_of_automatic_menubar():
    main = (PACKAGE / "qml" / "Main.qml").read_text(encoding="utf-8")
    menu = (PACKAGE / "qml" / "components" / "MintMenu.qml").read_text(encoding="utf-8")
    menu_item = (PACKAGE / "qml" / "components" / "MintMenuItem.qml").read_text(encoding="utf-8")

    assert "menuBar: MenuBar" not in main
    assert "header: Rectangle" in main
    for name in ("File", "Edit", "View"):
        assert f'objectName: "topMenuButton_{name}"' in main
    assert "menu.popup(button, 0, button.height)" in main
    assert "popupType: Popup.Item" in menu
    assert "width: menuWidth" in menu
    assert "implicitWidth: control.menuWidth" in menu
    assert "implicitWidth: Math.max(220" in menu_item


def test_add_layer_popup_is_anchored_to_its_button():
    layers = (PACKAGE / "qml" / "pages" / "LayersPage.qml").read_text(encoding="utf-8")
    assert 'objectName: "addLayerButton"' in layers
    assert "mapToItem(Overlay.overlay" in layers
    assert "parent: Overlay.overlay" in layers


def test_inspector_width_and_sliders_use_available_width():
    main = (PACKAGE / "qml" / "Main.qml").read_text(encoding="utf-8")
    layers = (PACKAGE / "qml" / "pages" / "LayersPage.qml").read_text(encoding="utf-8")
    source = (PACKAGE / "qml" / "pages" / "SourcePage.qml").read_text(encoding="utf-8")
    slider = (PACKAGE / "qml" / "components" / "MintSlider.qml").read_text(encoding="utf-8")

    assert 'objectName: "inspectorPanel"' in main
    assert "Layout.minimumWidth: 620" in main
    assert "Layout.preferredWidth: Math.max(620" in main
    assert "width: paramScroll.availableWidth" in layers
    assert "width: root.availableWidth" in source
    assert "width: control.availableWidth" in slider
    assert "MintSlider" in layers


def test_undo_redo_and_last_action_toast_are_wired():
    main = (PACKAGE / "qml" / "Main.qml").read_text(encoding="utf-8")
    backend = (PACKAGE / "qmlui" / "backend.py").read_text(encoding="utf-8")
    layers = (PACKAGE / "qml" / "pages" / "LayersPage.qml").read_text(encoding="utf-8")
    canvas = (PACKAGE / "qml" / "ImageCanvas.qml").read_text(encoding="utf-8")

    assert 'text: "Undo"' in main and 'shortcut: "Ctrl+Z"' in main
    assert 'text: "Redo"' in main and 'shortcut: "Ctrl+Y"' in main
    assert 'objectName: "lastActionToast"' in main
    assert "visible: backend.statusText.length > 0" in main
    assert "def undo(self)" in backend
    assert "def redo(self)" in backend
    assert "beginHistoryGroup" in layers
    assert "beginHistoryGroup" in canvas


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


def test_settings_dialog_is_simplified_and_about_dialog_is_fully_themed():
    settings = (PACKAGE / "qml" / "SettingsDialog.qml").read_text(encoding="utf-8")
    about = (PACKAGE / "qml" / "AboutDialog.qml").read_text(encoding="utf-8")

    assert 'title: "Settings"' in settings
    assert "RasterMint Settings" not in settings
    assert 'text: "Theme"' not in settings
    assert "Themes apply immediately" not in settings
    assert "header: Rectangle" in settings

    assert "header: Rectangle" in about
    assert "color: theme.panelRaisedColor" in about
    assert "color: theme.panelColor" in about
    assert "border.color: theme.borderColor" in about


def test_top_menu_focus_does_not_stick_after_popup_closes():
    main = (PACKAGE / "qml" / "Main.qml").read_text(encoding="utf-8")
    button = (PACKAGE / "qml" / "components" / "MintMenuBarButton.qml").read_text(encoding="utf-8")

    assert "forceActiveFocus" not in main
    assert "onClosed: fileMenuButton.focus = false" in main
    assert "onClosed: editMenuButton.focus = false" in main
    assert "onClosed: viewMenuButton.focus = false" in main
    assert "control.menuOpen || control.down" in button
    assert "control.hovered" in button
    assert "visible: control.menuOpen" in button
    assert "control.activeFocus" not in button
    assert "control.visualFocus" in button


def test_view_can_toggle_native_shortcut_hints_without_disabling_shortcuts():
    main = (PACKAGE / "qml" / "Main.qml").read_text(encoding="utf-8")
    menu_item = (PACKAGE / "qml" / "components" / "MintMenuItem.qml").read_text(encoding="utf-8")
    backend = (PACKAGE / "qmlui" / "backend.py").read_text(encoding="utf-8")

    assert 'text: "Show Hotkeys"' in main
    assert 'shortcut: "Ctrl+Alt+K"' in main
    assert "checkable: true" in main
    assert "checked: backend.showHotkeys" in main
    assert "backend.setShowHotkeys(checked)" in main
    assert "Shortcut {" in menu_item
    assert "shortcutFormatter.nativeText" in menu_item
    assert "backend.showHotkeys" in menu_item
    assert "checkSlot" not in menu_item
    assert "control.indicator.width + control.spacing" not in menu_item
    assert "indicator: null" in menu_item
    assert "control.checkable && control.checked" in menu_item
    assert "theme.accentColor.r" in menu_item
    assert "0.14" in menu_item
    assert "border.width: control.checkable && control.checked ? 1 : 0" in menu_item
    assert "visible: control.checkable && control.checked" in menu_item
    assert 'text: "Mirror Image Horizontally"' in main
    assert 'checked: Boolean(backend.settingsMap.mirror_horizontal)' in main
    assert 'text: "Mirror Image Vertically"' in main
    assert 'checked: Boolean(backend.settingsMap.mirror_vertical)' in main
    assert "def setShowHotkeys(self, enabled: bool)" in backend
    assert 'self.app_settings.setValue("showHotkeysQml", enabled)' in backend


def test_theme_owned_controls_replace_remaining_basic_style_leaks():
    main = (PACKAGE / "qml" / "Main.qml").read_text(encoding="utf-8")
    pages = "\n".join(path.read_text(encoding="utf-8") for path in (PACKAGE / "qml" / "pages").glob("*.qml"))
    spinbox = (PACKAGE / "qml" / "components" / "MintSpinBox.qml").read_text(encoding="utf-8")
    separator = (PACKAGE / "qml" / "components" / "MintMenuSeparator.qml").read_text(encoding="utf-8")

    assert "MenuSeparator {" not in main.replace("MintMenuSeparator {", "")
    assert "MintMenuSeparator {" in main
    assert "SpinBox {" not in pages.replace("MintSpinBox {", "")
    assert "MintSpinBox {" in pages
    assert "theme.panelRaisedColor" in spinbox
    assert "theme.borderColor" in spinbox
    assert "theme.borderColor" in separator


def test_add_layer_popup_uses_persistent_expandable_categories():
    layers = (PACKAGE / "qml" / "pages" / "LayersPage.qml").read_text(encoding="utf-8")
    backend = (PACKAGE / "qmlui" / "backend.py").read_text(encoding="utf-8")
    assert "backend.layerCategories" in layers
    assert "expandedEffectCategories" in layers
    assert "toggleEffectCategory" in layers
    assert "addPopup.close()" in layers
    assert "def layerCategories" in backend
