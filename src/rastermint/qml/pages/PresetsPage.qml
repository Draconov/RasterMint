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
            spacing: 6

            MintLabel {
                text: "Presets"
                font.bold: true
                font.pixelSize: 15
                Layout.fillWidth: true
                Layout.minimumWidth: 62
            }

            MintButton {
                text: "Load JSON…"
                Layout.preferredWidth: 92
                onClicked: loadPresetDialog.open()
            }

            MintButton {
                text: "Save JSON…"
                Layout.preferredWidth: 92
                onClicked: savePresetDialog.open()
            }

            MintButton {
                text: "↻"
                Layout.preferredWidth: 34
                onClicked: backend.refreshPresetThumbnails()

                ToolTip.visible: hovered
                ToolTip.text: "Refresh preset thumbnails"
            }
        }

        GridView {
            id: presetGrid

            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            property int columns: width >= 620 ? 3 : 2

            cellWidth: width / columns
            cellHeight: 176
            model: backend.builtinPresets

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }

            delegate: Rectangle {
                width: presetGrid.cellWidth - 8
                height: presetGrid.cellHeight - 8
                radius: 8
                color: presetMouse.containsMouse ? theme.panelHoverColor : theme.panelRaisedColor
                border.color: theme.borderColor

                Column {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 6

                    Rectangle {
                        width: parent.width
                        height: 108
                        radius: 5
                        color: theme.canvasColor
                        clip: true

                        Image {
                            anchors.fill: parent
                            anchors.margins: 3
                            fillMode: Image.PreserveAspectFit
                            cache: false
                            source: "image://rastermint/preset/" + modelData.id + "?r=" + backend.previewRevision
                        }
                    }

                    Text {
                        width: parent.width
                        text: modelData.name
                        color: theme.textColor
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width
                        text: modelData.description
                        color: theme.mutedTextColor
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    id: presetMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: backend.applyBuiltinPreset(modelData.id)
                }

                ToolTip.visible: presetMouse.containsMouse
                ToolTip.text: modelData.description
            }
        }
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
