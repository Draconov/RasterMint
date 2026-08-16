import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Item {
    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            MintLabel { text: "Presets"; font.bold: true; font.pixelSize: 15; Layout.fillWidth: true }
            MintButton { text: "↻"; onClicked: backend.refreshPresetThumbnails() }
        }
        ListView {
            Layout.fillWidth: true
            Layout.preferredHeight: 176
            orientation: ListView.Horizontal
            spacing: 8
            clip: true
            model: backend.builtinPresets
            ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AlwaysOff }
            delegate: Rectangle {
                width: 132; height: 164; radius: 8
                color: presetMouse.containsMouse ? theme.panelHoverColor : theme.panelRaisedColor
                border.color: theme.borderColor
                Column {
                    anchors.fill: parent; anchors.margins: 7; spacing: 6
                    Rectangle {
                        width: parent.width; height: 108; radius: 5; color: theme.canvasColor; clip: true
                        Image {
                            anchors.fill: parent; anchors.margins: 3
                            fillMode: Image.PreserveAspectFit
                            cache: false
                            source: "image://rastermint/preset/" + modelData.id + "?r=" + backend.previewRevision
                        }
                    }
                    Text { width: parent.width; text: modelData.name; color: theme.textColor; font.bold: true; elide: Text.ElideRight }
                    Text { width: parent.width; text: modelData.description; color: theme.mutedTextColor; font.pixelSize: 10; elide: Text.ElideRight }
                }
                MouseArea { id: presetMouse; anchors.fill: parent; hoverEnabled: true; onClicked: backend.applyBuiltinPreset(modelData.id) }
                ToolTip.visible: presetMouse.containsMouse
                ToolTip.text: modelData.description
            }
        }
        RowLayout {
            Layout.fillWidth: true
            MintButton { Layout.fillWidth: true; text: "Load JSON…"; onClicked: loadPresetDialog.open() }
            MintButton { Layout.fillWidth: true; text: "Save JSON…"; onClicked: savePresetDialog.open() }
        }
        Item { Layout.fillHeight: true }
    }
    FileDialog {
        id: loadPresetDialog
        title: "Load RasterMint preset"
        nameFilters: ["JSON preset (*.json)", "All files (*)"]
        onAccepted: backend.loadPreset(selectedFile.toString())
    }
    FileDialog {
        id: savePresetDialog
        title: "Save RasterMint preset"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["JSON preset (*.json)"]
        onAccepted: backend.savePreset(selectedFile.toString())
    }
}
