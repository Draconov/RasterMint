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

    property int inspectorIndex: 7

    function urlString(value) {
        return value ? value.toString() : ""
    }

    function urlStrings(values) {
        var result = []
        for (var i = 0; i < values.length; ++i)
            result.push(window.urlString(values[i]))
        return result
    }

    function pasteImageShortcutAllowed() {
        var item = window.activeFocusItem
        if (!item)
            return true
        var typeName = String(item)
        return typeName.indexOf("TextInput") < 0 && typeName.indexOf("TextEdit") < 0
    }

    function renderEtaLabel() {
        var eta = Number(backend.renderEtaSeconds)
        if (!isFinite(eta) || eta < 0)
            return qsTr("Estimating…")
        if (eta < 0.1)
            return qsTr("Finishing…")
        var value = eta < 10 ? eta.toFixed(1) : String(Math.ceil(eta))
        return qsTr("~%1 s remaining").arg(value)
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
                text: qsTr("File")
                menuOpen: fileMenu.opened
                onClicked: window.toggleTopMenu(fileMenu, fileMenuButton)
                onHoveredChanged: if (hovered) window.switchTopMenuOnHover(fileMenu, fileMenuButton)
            }

            MintMenuBarButton {
                id: editMenuButton
                objectName: "topMenuButton_Edit"
                text: qsTr("Edit")
                menuOpen: editMenu.opened
                onClicked: window.toggleTopMenu(editMenu, editMenuButton)
                onHoveredChanged: if (hovered) window.switchTopMenuOnHover(editMenu, editMenuButton)
            }

            MintMenuBarButton {
                id: viewMenuButton
                objectName: "topMenuButton_View"
                text: qsTr("View")
                menuOpen: viewMenu.opened
                onClicked: window.toggleTopMenu(viewMenu, viewMenuButton)
                onHoveredChanged: if (hovered) window.switchTopMenuOnHover(viewMenu, viewMenuButton)
            }
        }

        MintMenu {
            id: fileMenu
            objectName: "fileMenu"
            title: qsTr("File")
            menuWidth: 300
            onClosed: fileMenuButton.focus = false

            Action { text: qsTr("Open File…"); shortcut: StandardKey.Open; onTriggered: openDialog.open() }
            Action {
                text: qsTr("Paste Image from Clipboard")
                shortcut: StandardKey.Paste
                enabled: window.pasteImageShortcutAllowed()
                onTriggered: backend.pasteImageFromClipboard()
            }
            MintMenuSeparator { }
            Action { text: qsTr("Open Project…"); shortcut: "Ctrl+Alt+O"; onTriggered: openProjectDialog.open() }
            Action { text: qsTr("Save Project…"); shortcut: "Ctrl+Alt+Shift+S"; onTriggered: saveProjectDialog.open() }
            MintMenuSeparator { }
            Action { text: qsTr("Export to Clipboard…"); enabled: backend.hasSource; onTriggered: backend.exportToClipboard() }
            Action { text: qsTr("Quick Export Image…"); enabled: backend.hasSource; shortcut: "Ctrl+E"; onTriggered: window.openQuickExportImageDialog() }
            Action { text: qsTr("Export Image…"); enabled: backend.hasSource; shortcut: "Ctrl+Shift+E"; onTriggered: advancedExportDialog.open() }
            Action { text: qsTr("Export Animation / Video…"); enabled: backend.hasSource; shortcut: "Ctrl+Alt+S"; onTriggered: window.openMediaExport() }
            Action { text: qsTr("Export PNG Sequence…"); enabled: backend.hasSource; shortcut: "Ctrl+Alt+P"; onTriggered: sequenceFolderDialog.open() }
            Action { text: qsTr("Batch Export Images…"); shortcut: "Ctrl+Shift+B"; onTriggered: batchExportDialog.open() }
            MintMenuSeparator { }
            Action { text: qsTr("Load Preset…"); shortcut: "Ctrl+L"; onTriggered: loadPresetDialog.open() }
            Action { text: qsTr("Save Preset…"); shortcut: "Ctrl+Shift+S"; onTriggered: savePresetDialog.open() }
            MintMenuSeparator { }
            Action { text: qsTr("Quit"); shortcut: StandardKey.Quit; onTriggered: Qt.quit() }
        }

        MintMenu {
            id: editMenu
            objectName: "editMenu"
            title: qsTr("Edit")
            menuWidth: 330
            onClosed: editMenuButton.focus = false

            Action { text: qsTr("Undo"); enabled: backend.canUndo; shortcut: "Ctrl+Z"; onTriggered: backend.undo() }
            Action { text: qsTr("Redo"); enabled: backend.canRedo; shortcut: "Ctrl+Y"; onTriggered: backend.redo() }
            MintMenuSeparator { }
            Action { text: qsTr("Flip Image Horizontally"); enabled: backend.hasSource; shortcut: "Ctrl+Shift+H"; onTriggered: backend.flipHorizontal() }
            Action { text: qsTr("Flip Image Vertically"); enabled: backend.hasSource; shortcut: "Ctrl+Shift+V"; onTriggered: backend.flipVertical() }
            MintMenuSeparator { }
            Action {
                text: qsTr("Mirror Image Horizontally")
                enabled: backend.hasSource
                shortcut: "Ctrl+Alt+H"
                checkable: true
                checked: Boolean(backend.settingsMap.mirror_horizontal)
                onTriggered: backend.toggleMirrorHorizontal()
            }
            Action {
                text: qsTr("Mirror Image Vertically")
                enabled: backend.hasSource
                shortcut: "Ctrl+Alt+V"
                checkable: true
                checked: Boolean(backend.settingsMap.mirror_vertical)
                onTriggered: backend.toggleMirrorVertical()
            }
            MintMenuSeparator { }
            Action { text: qsTr("Rotate 90° Clockwise"); enabled: backend.hasSource; shortcut: "Ctrl+R"; onTriggered: backend.rotateImage(90) }
            Action { text: qsTr("Rotate 90° Counter-clockwise"); enabled: backend.hasSource; shortcut: "Ctrl+Shift+R"; onTriggered: backend.rotateImage(-90) }
            Action { text: qsTr("Rotate 180°"); enabled: backend.hasSource; shortcut: "Ctrl+Alt+R"; onTriggered: backend.rotateImage(180) }
            Action { text: qsTr("Reset Image Transform"); enabled: backend.hasSource; shortcut: "Ctrl+Shift+0"; onTriggered: backend.resetImageTransform() }
            MintMenuSeparator { }
            Action { text: qsTr("Settings…"); shortcut: "Ctrl+,"; onTriggered: settingsDialog.open() }
        }

        MintMenu {
            id: viewMenu
            objectName: "viewMenu"
            title: qsTr("View")
            menuWidth: 280
            onClosed: viewMenuButton.focus = false

            Action { text: qsTr("Fit Preview"); enabled: backend.hasSource; shortcut: "F"; onTriggered: { canvas.resetView(); backend.reportAction("Fit preview") } }
            Action {
                text: qsTr("Show Hotkeys")
                shortcut: "Ctrl+Alt+K"
                checkable: true
                checked: backend.showHotkeys
                onTriggered: backend.setShowHotkeys(checked)
            }
            MintMenuSeparator { }
            Action { text: qsTr("Capture Snapshot A"); enabled: backend.hasSource; shortcut: "Ctrl+Alt+1"; onTriggered: backend.captureSnapshot("A") }
            Action { text: qsTr("Capture Snapshot B"); enabled: backend.hasSource; shortcut: "Ctrl+Alt+2"; onTriggered: backend.captureSnapshot("B") }
            Action { text: qsTr("Apply Snapshot A"); enabled: backend.snapshotAReady; onTriggered: backend.applySnapshot("A") }
            Action { text: qsTr("Apply Snapshot B"); enabled: backend.snapshotBReady; onTriggered: backend.applySnapshot("B") }
            Action { text: qsTr("A/B Split View"); enabled: backend.snapshotAReady && backend.snapshotBReady; checkable: true; checked: backend.comparisonEnabled; onTriggered: backend.setComparisonEnabled(checked) }
            MintMenuSeparator { }
            Action { text: qsTr("About RasterMint"); shortcut: "F1"; onTriggered: aboutDialog.open() }
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
                id: renderProgressPanel
                objectName: "renderProgressPanel"
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 18
                visible: backend.renderBusy && backend.renderProgressVisible
                z: 110
                width: Math.min(parent.width - 48, 520)
                height: 62
                radius: 7
                color: theme.panelRaisedColor
                border.color: theme.borderColor
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 7

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            Layout.fillWidth: true
                            text: backend.renderStage.length > 0 ? backend.renderStage : qsTr("Rendering preview")
                            color: theme.textColor
                            font.pixelSize: 11
                            font.bold: true
                            elide: Text.ElideRight
                        }

                        Text {
                            text: window.renderEtaLabel()
                            color: theme.mutedTextColor
                            font.pixelSize: 10
                            horizontalAlignment: Text.AlignRight
                        }
                    }

                    ProgressBar {
                        id: renderProgressBar
                        objectName: "renderProgressBar"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 8
                        from: 0
                        to: 1
                        value: Math.max(0, Math.min(1, backend.renderProgress))
                        padding: 0

                        background: Rectangle {
                            implicitHeight: 8
                            radius: 4
                            color: theme.panelColor
                            border.color: theme.borderColor
                            border.width: 1
                        }

                        contentItem: Item {
                            implicitHeight: 8
                            clip: true
                            Rectangle {
                                width: renderProgressBar.visualPosition * parent.width
                                height: parent.height
                                radius: 4
                                color: theme.accentColor
                            }
                        }
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
                    Layout.preferredWidth: 56
                    Layout.fillHeight: true
                    color: theme.panelColor
                    border.color: theme.borderColor
                    ColumnLayout {
                        anchors { fill: parent; margins: 6 }
                        spacing: 3

                        InspectorNavButton {
                            Layout.fillWidth: true
                            text: qsTr("Randomize")
                            iconSource: Qt.resolvedUrl("../data/icons/sidebar-random.png")
                            selected: window.inspectorIndex === 0
                            onClicked: window.inspectorIndex = 0
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 11
                            Rectangle {
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    verticalCenter: parent.verticalCenter
                                    leftMargin: 8
                                    rightMargin: 8
                                }
                                height: 1
                                color: theme.borderColor
                            }
                        }

                        InspectorNavButton {
                            Layout.fillWidth: true
                            text: qsTr("Presets")
                            iconSource: Qt.resolvedUrl("../data/icons/sidebar-presets.png")
                            selected: window.inspectorIndex === 4
                            onClicked: window.inspectorIndex = 4
                        }
                        InspectorNavButton {
                            Layout.fillWidth: true
                            text: qsTr("Hardware")
                            iconSource: Qt.resolvedUrl("../data/icons/sidebar-hardware.png")
                            selected: window.inspectorIndex === 5
                            onClicked: window.inspectorIndex = 5
                        }
                        InspectorNavButton {
                            Layout.fillWidth: true
                            text: qsTr("Palette")
                            paletteSwatches: true
                            selected: window.inspectorIndex === 6
                            onClicked: window.inspectorIndex = 6
                        }
                        InspectorNavButton {
                            Layout.fillWidth: true
                            text: qsTr("Layers")
                            iconSource: Qt.resolvedUrl("../data/icons/sidebar-layers.png")
                            selected: window.inspectorIndex === 7
                            onClicked: window.inspectorIndex = 7
                        }
                        InspectorNavButton {
                            Layout.fillWidth: true
                            text: qsTr("Print Lab")
                            iconSource: Qt.resolvedUrl("../data/icons/sidebar-print-lab.png")
                            selected: window.inspectorIndex === 10
                            onClicked: window.inspectorIndex = 10
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 11
                            Rectangle {
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    verticalCenter: parent.verticalCenter
                                    leftMargin: 8
                                    rightMargin: 8
                                }
                                height: 1
                                color: theme.borderColor
                            }
                        }

                        InspectorNavButton {
                            Layout.fillWidth: true
                            text: qsTr("Source")
                            iconSource: Qt.resolvedUrl("../data/icons/sidebar-source.png")
                            selected: window.inspectorIndex === 1
                            onClicked: window.inspectorIndex = 1
                        }
                        InspectorNavButton {
                            Layout.fillWidth: true
                            text: qsTr("Preview")
                            iconSource: Qt.resolvedUrl("../data/icons/sidebar-preview.png")
                            selected: window.inspectorIndex === 2
                            onClicked: window.inspectorIndex = 2
                        }
                        InspectorNavButton {
                            Layout.fillWidth: true
                            text: qsTr("Raster")
                            iconSource: Qt.resolvedUrl("../data/icons/sidebar-raster.png")
                            selected: window.inspectorIndex === 3
                            onClicked: window.inspectorIndex = 3
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 11
                            Rectangle {
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    verticalCenter: parent.verticalCenter
                                    leftMargin: 8
                                    rightMargin: 8
                                }
                                height: 1
                                color: theme.borderColor
                            }
                        }

                        InspectorNavButton {
                            Layout.fillWidth: true
                            text: qsTr("Animation")
                            iconSource: Qt.resolvedUrl("../data/icons/sidebar-animation.png")
                            selected: window.inspectorIndex === 8
                            onClicked: window.inspectorIndex = 8
                        }
                        InspectorNavButton {
                            Layout.fillWidth: true
                            text: qsTr("Media Playback")
                            iconSource: Qt.resolvedUrl("../data/icons/sidebar-media-playback.png")
                            selected: window.inspectorIndex === 9
                            onClicked: window.inspectorIndex = 9
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
                            Pages.RandomizePage { }
                            Pages.SourcePage { }
                            Pages.PreviewPage { onFitRequested: canvas.resetView() }
                            Pages.RasterPage { }
                            Pages.PresetsPage { }
                            Pages.HardwarePage { }
                            Pages.PalettePage { }
                            Pages.LayersPage { }
                            Pages.AnimationPage { }
                            Pages.MediaPage { }
                            Pages.PrintLabPage { }
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
        title: qsTr("Open media")
        nameFilters: ["Supported media (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff *.gif *.mp4 *.mov *.mkv *.webm *.avi *.m4v)", "All files (*)"]
        onAccepted: backend.openFile(window.urlString(selectedFile))
    }
    FileDialog {
        id: quickExportImageDialog
        title: qsTr("Quick Export Image — 1× current output")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "png"
        nameFilters: ["PNG (*.png)", "JPEG (*.jpg *.jpeg)", "WebP (*.webp)", "TIFF (*.tif *.tiff)", "SVG (*.svg)"]
        onAccepted: backend.exportImage(window.urlString(selectedFile))
    }
    FileDialog {
        id: exportMediaDialog
        title: qsTr("Export animation / video")
        fileMode: FileDialog.SaveFile
        defaultSuffix: selectedNameFilter.index === 1 ? "gif" : "mp4"
        nameFilters: ["MP4 video (*.mp4)", "Animated GIF (*.gif)"]
        onAccepted: backend.exportMedia(window.urlString(selectedFile))
    }
    FolderDialog { id: sequenceFolderDialog; title: qsTr("Choose PNG sequence folder"); onAccepted: backend.exportSequence(window.urlString(selectedFolder)) }
    FileDialog { id: openProjectDialog; title: qsTr("Open RasterMint project"); nameFilters: ["RasterMint Project (*.rastermint)"]; onAccepted: backend.loadProject(window.urlString(selectedFile)) }
    FileDialog { id: saveProjectDialog; title: qsTr("Save RasterMint project"); fileMode: FileDialog.SaveFile; defaultSuffix: "rastermint"; nameFilters: ["RasterMint Project (*.rastermint)"]; onAccepted: backend.saveProject(window.urlString(selectedFile)) }
    FileDialog { id: loadPresetDialog; title: qsTr("Load preset"); nameFilters: ["JSON preset (*.json)"]; onAccepted: backend.loadPreset(window.urlString(selectedFile)) }
    FileDialog { id: savePresetDialog; title: qsTr("Save preset"); fileMode: FileDialog.SaveFile; defaultSuffix: "json"; nameFilters: ["JSON preset (*.json)"]; onAccepted: backend.savePreset(window.urlString(selectedFile)) }

    MessageDialog { id: errorDialog; title: "RasterMint"; buttons: MessageDialog.Ok }
    MessageDialog { id: infoDialog; title: "RasterMint"; buttons: MessageDialog.Ok }
    Connections {
        target: backend
        function onErrorOccurred(title, message) { errorDialog.title = title; errorDialog.text = message; errorDialog.open() }
        function onInfoOccurred(title, message) { infoDialog.title = title; infoDialog.text = message; infoDialog.open() }
    }

    Component.onDestruction: backend.shutdown()
}
