import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Item {
    id: root

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
                text: "Load JSON"
                Layout.minimumWidth: implicitWidth
                onClicked: loadPresetDialog.open()
            }

            MintButton {
                text: "Save JSON"
                Layout.minimumWidth: implicitWidth
                onClicked: savePresetDialog.open()
            }

            MintButton {
                text: "Save to Library"
                Layout.minimumWidth: implicitWidth
                onClicked: saveLibraryDialog.open()
            }

            MintButton {
                text: "↻"
                Layout.minimumWidth: 34
                Layout.preferredWidth: 34
                Layout.maximumWidth: 34
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
            model: backend.allPresets

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }

            delegate: Rectangle {
                id: presetCard
                width: presetGrid.cellWidth - 8
                height: presetGrid.cellHeight - 8
                radius: 8
                color: presetMouse.containsMouse ? theme.panelHoverColor : theme.panelRaisedColor
                border.color: theme.borderColor

                property bool isUserPreset: Boolean(modelData.user)

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
                        width: parent.width - (presetCard.isUserPreset ? 30 : 0)
                        text: modelData.name + (presetCard.isUserPreset ? " · custom" : "")
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
                    onClicked: backend.applyPreset(modelData.id)
                }

                MintButton {
                    visible: presetCard.isUserPreset
                    z: 2
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 7
                    width: 30
                    height: 28
                    text: "×"
                    onClicked: backend.deletePresetFromLibrary(modelData.id)

                    ToolTip.visible: hovered
                    ToolTip.text: "Remove custom preset from library"
                }

                ToolTip.visible: presetMouse.containsMouse
                ToolTip.text: modelData.description
            }
        }
    }

    Dialog {
        id: saveLibraryDialog
        title: "Save preset to library"
        modal: true
        width: Math.min(380, root.width - 24)
        x: Math.round((root.width - width) / 2)
        y: Math.max(12, Math.round((root.height - height) / 2))
        standardButtons: Dialog.Save | Dialog.Cancel

        onOpened: {
            presetNameField.text = "Custom Preset"
            presetDescriptionField.text = ""
            presetNameField.forceActiveFocus()
            presetNameField.selectAll()
        }
        onAccepted: backend.savePresetToLibrary(presetNameField.text, presetDescriptionField.text)

        contentItem: ColumnLayout {
            spacing: 8
            MintLabel { text: "Name" }
            MintTextField {
                id: presetNameField
                Layout.fillWidth: true
                placeholderText: "Preset name"
            }
            MintLabel { text: "Description" }
            MintTextField {
                id: presetDescriptionField
                Layout.fillWidth: true
                placeholderText: "Optional description"
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
