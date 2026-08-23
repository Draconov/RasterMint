import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "components"
import "pages" as Pages

ApplicationWindow {
    id: window
    width: 1440
    height: 900
    minimumWidth: 1000
    minimumHeight: 650
    visible: true
    title: "RasterMint " + backend.version
    color: theme.windowColor

    property int inspectorIndex: 2

    function urlString(value) {
        return value ? value.toString() : ""
    }

    function urlStrings(values) {
        var result = []
        for (var i = 0; i < values.length; ++i)
            result.push(window.urlString(values[i]))
        return result
    }

    function openQuickExportImageDialog() {
        quickExportImageDialog.selectedFile = backend.suggestedExportFile("PNG")
        quickExportImageDialog.open()
    }

    function suggestedMediaBaseFile() {
        var base = backend.suggestedExportFile("PNG")
        if (!base || base.length === 0)
            return ""
        return base.replace(/\.png$/i, "")
    }

    function openMediaExport() {
        exportMediaDialog.selectedNameFilter.index = 0
        exportMediaDialog.selectedFile = window.suggestedMediaBaseFile()
        exportMediaDialog.open()
    }

    function closeTopMenus(exceptMenu) {
        if (fileMenu !== exceptMenu && fileMenu.opened)
            fileMenu.close()
        if (editMenu !== exceptMenu && editMenu.opened)
            editMenu.close()
        if (viewMenu !== exceptMenu && viewMenu.opened)
            viewMenu.close()
    }

    function toggleTopMenu(menu, button) {
        if (menu.opened) {
            menu.close()
            return
        }
        closeTopMenus(menu)
        // Use Menu.popup(parent, x, y) explicitly instead of relying on the
        // MenuBar/MenuBarItem auto-popup path. Qt documents these coordinates
        // as relative to the supplied parent item, so this deterministically
        // places the menu directly below the clicked button on every platform.
        menu.popup(button, 0, button.height)
    }

    function switchTopMenuOnHover(menu, button) {
        if (fileMenu.opened || editMenu.opened || viewMenu.opened) {
            if (!menu.opened) {
                closeTopMenus(menu)
                menu.popup(button, 0, button.height)
            }
        }
    }

    header: Rectangle {
        id: topBar
        objectName: "topBar"
        implicitHeight: 34
        height: 34
        color: theme.panelColor
        border.color: theme.borderColor
        border.width: 1

        Row {
            id: topMenuButtons
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            spacing: 0

            MintMenuBarButton {
                id: fileMenuButton
                objectName: "topMenuButton_File"
                text: "File"
                menuOpen: fileMenu.opened
                onClicked: window.toggleTopMenu(fileMenu, fileMenuButton)
                onHoveredChanged: if (hovered) window.switchTopMenuOnHover(fileMenu, fileMenuButton)
            }

            MintMenuBarButton {
                id: editMenuButton
                objectName: "topMenuButton_Edit"
                text: "Edit"
                menuOpen: editMenu.opened
                onClicked: window.toggleTopMenu(editMenu, editMenuButton)
                onHoveredChanged: if (hovered) window.switchTopMenuOnHover(editMenu, editMenuButton)
            }

            MintMenuBarButton {
                id: viewMenuButton
                objectName: "topMenuButton_View"
                text: "View"
                menuOpen: viewMenu.opened
                onClicked: window.toggleTopMenu(viewMenu, viewMenuButton)
                onHoveredChanged: if (hovered) window.switchTopMenuOnHover(viewMenu, viewMenuButton)
            }
        }

        MintMenu {
            id: fileMenu
            objectName: "fileMenu"
            title: "File"
            menuWidth: 300
            onClosed: fileMenuButton.focus = false

            Action { text: "Open File…"; shortcut: StandardKey.Open; onTriggered: openDialog.open() }
            MintMenuSeparator { }
            Action { text: "Quick Export Image…"; enabled: backend.hasSource; shortcut: "Ctrl+E"; onTriggered: window.openQuickExportImageDialog() }
            Action { text: "Export Image…"; enabled: backend.hasSource; shortcut: "Ctrl+Shift+E"; onTriggered: advancedExportDialog.open() }
            Action { text: "Export Animation / Video…"; enabled: backend.hasSource; shortcut: "Ctrl+Alt+S"; onTriggered: window.openMediaExport() }
            Action { text: "Export PNG Sequence…"; enabled: backend.hasSource; shortcut: "Ctrl+Alt+P"; onTriggered: sequenceFolderDialog.open() }
            Action { text: "Batch Export Images…"; shortcut: "Ctrl+Shift+B"; onTriggered: batchExportDialog.open() }
            MintMenuSeparator { }
            Action { text: "Load Preset…"; shortcut: "Ctrl+L"; onTriggered: loadPresetDialog.open() }
            Action { text: "Save Preset…"; shortcut: "Ctrl+Shift+S"; onTriggered: savePresetDialog.open() }
            MintMenuSeparator { }
            Action { text: "Quit"; shortcut: StandardKey.Quit; onTriggered: Qt.quit() }
        }

        MintMenu {
            id: editMenu
            objectName: "editMenu"
            title: "Edit"
            menuWidth: 330
            onClosed: editMenuButton.focus = false

            Action { text: "Undo"; enabled: backend.canUndo; shortcut: "Ctrl+Z"; onTriggered: backend.undo() }
            Action { text: "Redo"; enabled: backend.canRedo; shortcut: "Ctrl+Y"; onTriggered: backend.redo() }
            MintMenuSeparator { }
            Action { text: "Flip Image Horizontally"; enabled: backend.hasSource; shortcut: "Ctrl+Shift+H"; onTriggered: backend.flipHorizontal() }
            Action { text: "Flip Image Vertically"; enabled: backend.hasSource; shortcut: "Ctrl+Shift+V"; onTriggered: backend.flipVertical() }
            MintMenuSeparator { }
            Action {
                text: "Mirror Image Horizontally"
                enabled: backend.hasSource
                shortcut: "Ctrl+Alt+H"
                checkable: true
                checked: Boolean(backend.settingsMap.mirror_horizontal)
                onTriggered: backend.toggleMirrorHorizontal()
            }
            Action {
                text: "Mirror Image Vertically"
                enabled: backend.hasSource
                shortcut: "Ctrl+Alt+V"
                checkable: true
                checked: Boolean(backend.settingsMap.mirror_vertical)
                onTriggered: backend.toggleMirrorVertical()
            }
            MintMenuSeparator { }
            Action { text: "Rotate 90° Clockwise"; enabled: backend.hasSource; shortcut: "Ctrl+R"; onTriggered: backend.rotateImage(90) }
            Action { text: "Rotate 90° Counter-clockwise"; enabled: backend.hasSource; shortcut: "Ctrl+Shift+R"; onTriggered: backend.rotateImage(-90) }
            Action { text: "Rotate 180°"; enabled: backend.hasSource; shortcut: "Ctrl+Alt+R"; onTriggered: backend.rotateImage(180) }
            Action { text: "Reset Image Transform"; enabled: backend.hasSource; shortcut: "Ctrl+Shift+0"; onTriggered: backend.resetImageTransform() }
            MintMenuSeparator { }
            Action { text: "Settings…"; shortcut: "Ctrl+,"; onTriggered: settingsDialog.open() }
        }

        MintMenu {
            id: viewMenu
            objectName: "viewMenu"
            title: "View"
            menuWidth: 280
            onClosed: viewMenuButton.focus = false

            Action { text: "Fit Preview"; enabled: backend.hasSource; shortcut: "F"; onTriggered: { canvas.resetView(); backend.reportAction("Fit preview") } }
            Action {
                text: "Show Hotkeys"
                shortcut: "Ctrl+Alt+K"
                checkable: true
                checked: backend.showHotkeys
                onTriggered: backend.setShowHotkeys(checked)
            }
            MintMenuSeparator { }
            Action { text: "About RasterMint"; shortcut: "F1"; onTriggered: aboutDialog.open() }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            ImageCanvas { id: canvas; anchors.fill: parent }
            DropArea {
                anchors.fill: parent
                onDropped: function(drop) {
                    if (drop.urls.length > 0) {
                        backend.openFile(window.urlString(drop.urls[0]))
                        drop.acceptProposedAction()
                    }
                }
            }
            Rectangle {
                id: actionToast
                objectName: "lastActionToast"
                anchors { left: parent.left; bottom: parent.bottom; margins: 12 }
                visible: backend.statusText.length > 0
                z: 100
                color: theme.panelRaisedColor
                border.color: theme.borderColor
                border.width: 1
                radius: 6
                width: Math.min(parent.width - 24, statusLabel.implicitWidth + 18)
                height: 28
                Text { id: statusLabel; anchors.centerIn: parent; text: backend.statusText; color: theme.textColor; font.pixelSize: 11; elide: Text.ElideRight; width: Math.min(implicitWidth, parent.parent.width - 42) }
            }
        }

        Rectangle {
            id: inspectorPanel
            objectName: "inspectorPanel"
            Layout.minimumWidth: 620
            Layout.preferredWidth: Math.max(620, Math.min(700, window.width * 0.36))
            Layout.fillHeight: true
            color: theme.panelColor
            border.color: theme.borderColor

            RowLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.preferredWidth: 132
                    Layout.fillHeight: true
                    color: theme.panelColor
                    border.color: theme.borderColor
                    ColumnLayout {
                        anchors { fill: parent; margins: 6 }
                        spacing: 3
                        Repeater {
                            model: ["Presets", "Preview", "Layers", "Palette", "Raster", "Hardware", "Source", "Animation", "Randomize", "Media"]
                            InspectorNavButton {
                                Layout.fillWidth: true
                                text: modelData
                                selected: window.inspectorIndex === index
                                onClicked: window.inspectorIndex = index
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: theme.panelColor
                    border.color: theme.borderColor
                    Item {
                        anchors { fill: parent; margins: 12 }
                        StackLayout {
                            anchors.fill: parent
                            currentIndex: window.inspectorIndex
                            Pages.PresetsPage { }
                            Pages.PreviewPage { onFitRequested: canvas.resetView() }
                            Pages.LayersPage { }
                            Pages.PalettePage { }
                            Pages.RasterPage { }
                            Pages.HardwarePage { }
                            Pages.SourcePage { }
                            Pages.AnimationPage { }
                            Pages.RandomizePage { }
                            Pages.MediaPage { }
                        }
                    }
                }
            }
        }
    }

    SettingsDialog { id: settingsDialog }
    AboutDialog { id: aboutDialog }
    ExportImageDialog {
        id: advancedExportDialog
        urlNormalizer: function(value) { return window.urlString(value) }
    }
    BatchExportDialog {
        id: batchExportDialog
        urlsNormalizer: function(selectedFiles) { return window.urlStrings(selectedFiles) }
        urlNormalizer: function(selectedFolder) { return window.urlString(selectedFolder) }
    }

    FileDialog {
        id: openDialog
        title: "Open media"
        nameFilters: ["Supported media (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff *.gif *.mp4 *.mov *.mkv *.webm *.avi *.m4v)", "All files (*)"]
        onAccepted: backend.openFile(window.urlString(selectedFile))
    }
    FileDialog {
        id: quickExportImageDialog
        title: "Quick Export Image — 1× current output"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "png"
        nameFilters: ["PNG (*.png)", "JPEG (*.jpg *.jpeg)", "WebP (*.webp)", "TIFF (*.tif *.tiff)", "SVG (*.svg)"]
        onAccepted: backend.exportImage(window.urlString(selectedFile))
    }
    FileDialog {
        id: exportMediaDialog
        title: "Export animation / video"
        fileMode: FileDialog.SaveFile
        defaultSuffix: selectedNameFilter.index === 1 ? "gif" : "mp4"
        nameFilters: ["MP4 video (*.mp4)", "Animated GIF (*.gif)"]
        onAccepted: backend.exportMedia(window.urlString(selectedFile))
    }
    FolderDialog { id: sequenceFolderDialog; title: "Choose PNG sequence folder"; onAccepted: backend.exportSequence(window.urlString(selectedFolder)) }
    FileDialog { id: loadPresetDialog; title: "Load preset"; nameFilters: ["JSON preset (*.json)"]; onAccepted: backend.loadPreset(window.urlString(selectedFile)) }
    FileDialog { id: savePresetDialog; title: "Save preset"; fileMode: FileDialog.SaveFile; defaultSuffix: "json"; nameFilters: ["JSON preset (*.json)"]; onAccepted: backend.savePreset(window.urlString(selectedFile)) }

    MessageDialog { id: errorDialog; title: "RasterMint"; buttons: MessageDialog.Ok }
    MessageDialog { id: infoDialog; title: "RasterMint"; buttons: MessageDialog.Ok }
    Connections {
        target: backend
        function onErrorOccurred(title, message) { errorDialog.title = title; errorDialog.text = message; errorDialog.open() }
        function onInfoOccurred(title, message) { infoDialog.title = title; infoDialog.text = message; infoDialog.open() }
    }

    Component.onDestruction: backend.shutdown()
}
