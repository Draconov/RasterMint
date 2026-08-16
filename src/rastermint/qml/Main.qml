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
    property var pendingBatchFiles: []

    menuBar: MenuBar {
        id: appMenu
        background: Rectangle { color: theme.panelColor; border.color: theme.borderColor }
        delegate: MenuBarItem {
            id: menuBarItem
            contentItem: Text { text: menuBarItem.text; color: theme.textColor; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter }
            background: Rectangle { radius: 4; color: menuBarItem.highlighted || menuBarItem.hovered ? theme.selectionColor : "transparent"; Behavior on color { ColorAnimation { duration: 70 } } }
        }

        Menu {
            title: "File"
            delegate: MintMenuItem { }
            background: Rectangle { color: theme.panelRaisedColor; border.color: theme.borderColor; radius: 7 }
            Action { text: "Open File…"; shortcut: StandardKey.Open; onTriggered: openDialog.open() }
            MenuSeparator { }
            Action { text: "Export Current Frame…"; enabled: backend.hasSource; shortcut: StandardKey.SaveAs; onTriggered: exportImageDialog.open() }
            Action { text: "Export Animation / Video…"; enabled: backend.hasSource; shortcut: "Ctrl+Alt+S"; onTriggered: exportMediaDialog.open() }
            Action { text: "Export PNG Sequence…"; enabled: backend.hasSource; shortcut: "Ctrl+Alt+P"; onTriggered: sequenceFolderDialog.open() }
            Action { text: "Batch Export Images…"; onTriggered: batchSourceDialog.open() }
            MenuSeparator { }
            Action { text: "Load Preset…"; shortcut: "Ctrl+L"; onTriggered: loadPresetDialog.open() }
            Action { text: "Save Preset…"; shortcut: "Ctrl+Shift+S"; onTriggered: savePresetDialog.open() }
            MenuSeparator { }
            Action { text: "Quit"; shortcut: StandardKey.Quit; onTriggered: Qt.quit() }
        }

        Menu {
            title: "Edit"
            delegate: MintMenuItem { }
            background: Rectangle { color: theme.panelRaisedColor; border.color: theme.borderColor; radius: 7 }
            Action { text: "Flip Image Horizontally"; enabled: backend.hasSource; shortcut: "Ctrl+Shift+H"; onTriggered: backend.flipHorizontal() }
            Action { text: "Flip Image Vertically"; enabled: backend.hasSource; shortcut: "Ctrl+Shift+V"; onTriggered: backend.flipVertical() }
            MenuSeparator { }
            Action {
                text: (Boolean(backend.settingsMap.mirror_horizontal) ? "✓  " : "") + "Mirror Image Horizontally"
                enabled: backend.hasSource
                shortcut: "Ctrl+Alt+H"
                onTriggered: backend.toggleMirrorHorizontal()
            }
            Action {
                text: (Boolean(backend.settingsMap.mirror_vertical) ? "✓  " : "") + "Mirror Image Vertically"
                enabled: backend.hasSource
                shortcut: "Ctrl+Alt+V"
                onTriggered: backend.toggleMirrorVertical()
            }
            MenuSeparator { }
            Action { text: "Rotate 90° Clockwise"; enabled: backend.hasSource; shortcut: "Ctrl+R"; onTriggered: backend.rotateImage(90) }
            Action { text: "Rotate 90° Counter-clockwise"; enabled: backend.hasSource; onTriggered: backend.rotateImage(-90) }
            Action { text: "Rotate 180°"; enabled: backend.hasSource; onTriggered: backend.rotateImage(180) }
            Action { text: "Reset Image Transform"; enabled: backend.hasSource; onTriggered: backend.resetImageTransform() }
            MenuSeparator { }
            Action { text: "Settings…"; shortcut: "Ctrl+,"; onTriggered: settingsDialog.open() }
        }

        Menu {
            title: "View"
            delegate: MintMenuItem { }
            background: Rectangle { color: theme.panelRaisedColor; border.color: theme.borderColor; radius: 7 }
            Action { text: "Fit Preview"; enabled: backend.hasSource; shortcut: "F"; onTriggered: canvas.resetView() }
            MenuSeparator { }
            Action { text: "About RasterMint"; onTriggered: aboutDialog.open() }
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
                    if (drop.urls.length > 0) backend.openFile(drop.urls[0])
                }
            }
            Rectangle {
                anchors { left: parent.left; bottom: parent.bottom; margins: 12 }
                visible: backend.statusText.length > 0
                color: Qt.rgba(0, 0, 0, 0.62)
                radius: 6
                width: Math.min(parent.width - 24, statusLabel.implicitWidth + 18)
                height: 28
                Text { id: statusLabel; anchors.centerIn: parent; text: backend.statusText; color: "white"; font.pixelSize: 11; elide: Text.ElideRight; width: Math.min(implicitWidth, parent.parent.width - 42) }
            }
        }

        Rectangle {
            Layout.preferredWidth: 510
            Layout.fillHeight: true
            color: theme.panelColor
            border.color: theme.borderColor

            RowLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.preferredWidth: 112
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

    FileDialog {
        id: openDialog
        title: "Open media"
        nameFilters: ["Supported media (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff *.gif *.mp4 *.mov *.mkv *.webm *.avi *.m4v)", "All files (*)"]
        onAccepted: backend.openFile(selectedFile)
    }
    FileDialog {
        id: exportImageDialog
        title: "Export current frame"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "png"
        nameFilters: ["PNG (*.png)", "JPEG (*.jpg *.jpeg)", "WebP (*.webp)", "TIFF (*.tif *.tiff)", "SVG (*.svg)"]
        onAccepted: backend.exportImage(selectedFile)
    }
    FileDialog {
        id: exportMediaDialog
        title: "Export animation / video"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "mp4"
        nameFilters: ["MP4 video (*.mp4)", "Animated GIF (*.gif)"]
        onAccepted: backend.exportMedia(selectedFile)
    }
    FolderDialog { id: sequenceFolderDialog; title: "Choose PNG sequence folder"; onAccepted: backend.exportSequence(selectedFolder) }
    FileDialog {
        id: batchSourceDialog
        title: "Select images for batch processing"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["Images (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)"]
        onAccepted: { window.pendingBatchFiles = selectedFiles; batchFolderDialog.open() }
    }
    FolderDialog { id: batchFolderDialog; title: "Choose batch output folder"; onAccepted: backend.batchExport(window.pendingBatchFiles, selectedFolder) }
    FileDialog { id: loadPresetDialog; title: "Load preset"; nameFilters: ["JSON preset (*.json)"]; onAccepted: backend.loadPreset(selectedFile) }
    FileDialog { id: savePresetDialog; title: "Save preset"; fileMode: FileDialog.SaveFile; defaultSuffix: "json"; nameFilters: ["JSON preset (*.json)"]; onAccepted: backend.savePreset(selectedFile) }

    MessageDialog { id: errorDialog; title: "RasterMint"; buttons: MessageDialog.Ok }
    MessageDialog { id: infoDialog; title: "RasterMint"; buttons: MessageDialog.Ok }
    Connections {
        target: backend
        function onErrorOccurred(title, message) { errorDialog.title = title; errorDialog.text = message; errorDialog.open() }
        function onInfoOccurred(title, message) { infoDialog.title = title; infoDialog.text = message; infoDialog.open() }
    }

    Component.onDestruction: backend.shutdown()
}
