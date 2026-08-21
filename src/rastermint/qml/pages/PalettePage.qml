import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Item {
    id: root
    property int colorEditIndex: -1

    ColumnLayout {
        anchors.fill: parent
        spacing: 9

        MintLabel { text: "Palette"; font.bold: true; font.pixelSize: 15 }
        MintLabel {
            Layout.fillWidth: true
            text: (backend.settingsMap.palette_name || "Custom") + " · " + (backend.settingsMap.palette || []).length + " colors"
            color: theme.mutedTextColor
            elide: Text.ElideRight
        }

        Flickable {
            Layout.fillWidth: true
            Layout.preferredHeight: 78
            contentWidth: swatches.width
            contentHeight: height
            clip: true
            Row {
                id: swatches
                spacing: 4
                Repeater {
                    model: backend.settingsMap.palette || []
                    Rectangle {
                        width: 38; height: 38; radius: 5; color: modelData
                        property bool locked: Boolean((backend.settingsMap.palette_locks || [])[index])
                        border.color: locked ? theme.accentColor : theme.borderColor
                        border.width: locked ? 2 : 1
                        Text {
                            visible: parent.locked
                            anchors { right: parent.right; bottom: parent.bottom; margins: 3 }
                            text: "●"
                            color: theme.accentColor
                            font.pixelSize: 9
                        }
                        MouseArea {
                            id: swatchMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            cursorShape: Qt.PointingHandCursor
                            onClicked: function(mouse) {
                                if (mouse.button === Qt.RightButton) {
                                    backend.setPaletteLock(index, !parent.locked)
                                } else {
                                    root.colorEditIndex = index
                                    colorDialog.selectedColor = parent.color
                                    colorDialog.open()
                                }
                            }
                        }
                        ToolTip.visible: swatchMouse.containsMouse
                        ToolTip.text: (index + 1) + ": " + modelData + (locked ? " · locked" : " · right-click to lock")
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            MintButton {
                text: "+"
                enabled: (backend.settingsMap.palette || []).length < 256
                onClicked: {
                    root.colorEditIndex = -1
                    var colors = backend.settingsMap.palette || []
                    colorDialog.selectedColor = colors.length ? colors[colors.length - 1] : "#FFFFFF"
                    colorDialog.open()
                }
            }
            MintButton {
                text: "−"
                enabled: (backend.settingsMap.palette || []).length > 1
                onClicked: backend.removePaletteColor(-1)
            }
            MintButton {
                Layout.fillWidth: true
                text: "Randomize unlocked"
                onClicked: backend.randomizePaletteUnlocked()
            }
        }

        MintTextField {
            id: searchField
            Layout.fillWidth: true
            placeholderText: "Search palettes…"
        }

        ListView {
            Layout.fillWidth: true
            Layout.preferredHeight: 190
            clip: true
            spacing: 3
            model: backend.allPaletteLibrary
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOff }

            delegate: Rectangle {
                width: ListView.view.width
                property bool matches: searchField.text.length === 0 || (modelData.name + " " + modelData.category + " " + modelData.description).toLowerCase().indexOf(searchField.text.toLowerCase()) >= 0
                property bool isUserPalette: Boolean(modelData.user)
                height: matches ? 44 : 0
                visible: matches
                radius: 6
                color: paletteMouse.containsMouse ? theme.panelHoverColor : "transparent"

                MouseArea {
                    id: paletteMouse
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.right: parent.right
                    anchors.rightMargin: parent.isUserPalette ? 36 : 0
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: backend.applyPalette(modelData.id)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 5
                    spacing: 6

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Text {
                            Layout.fillWidth: true
                            text: modelData.name
                            color: theme.textColor
                            font.bold: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: modelData.category + " · " + modelData.colors.length + " colors" + (modelData.user ? " · custom" : "")
                            color: theme.mutedTextColor
                            font.pixelSize: 10
                        }
                    }

                    Row {
                        spacing: 0
                        Repeater {
                            model: modelData.colors.slice(0, 8)
                            Rectangle { width: 11; height: 24; color: modelData }
                        }
                    }

                    MintButton {
                        visible: Boolean(modelData.user)
                        Layout.preferredWidth: 30
                        text: "×"
                        onClicked: backend.deletePaletteFromLibrary(modelData.id)

                        ToolTip.visible: hovered
                        ToolTip.text: "Remove custom palette from library"
                    }
                }

                ToolTip.visible: paletteMouse.containsMouse
                ToolTip.text: modelData.description
            }
        }

        RowLayout {
            Layout.fillWidth: true
            MintButton { Layout.fillWidth: true; text: "Import…"; onClicked: importPaletteDialog.open() }
            MintButton {
                Layout.fillWidth: true
                text: "Save to Library…"
                onClicked: saveLibraryDialog.open()
            }
        }
        RowLayout {
            Layout.fillWidth: true
            MintButton { Layout.fillWidth: true; text: "Export JSON…"; onClicked: exportJsonDialog.open() }
            MintButton { Layout.fillWidth: true; text: "Export HEX…"; onClicked: exportHexDialog.open() }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
        MintLabel { text: "Optimize from image"; font.bold: true }
        RowLayout {
            Layout.fillWidth: true
            MintSpinBox { id: colorCount; from: 2; to: 256; value: 8; editable: true; Layout.preferredWidth: 90 }
            MintComboBox { id: optimizer; Layout.fillWidth: true; model: backend.paletteOptimizerNames }
            MintButton { text: "Optimize"; enabled: backend.hasSource; onClicked: backend.optimizePalette(colorCount.value, optimizer.currentText) }
        }

        MintLabel { text: "Lospec"; font.bold: true }
        RowLayout {
            Layout.fillWidth: true
            MintTextField { id: lospecField; Layout.fillWidth: true; placeholderText: "slug or Lospec URL" }
            MintButton { text: "Fetch"; enabled: lospecField.text.length > 0; onClicked: backend.fetchLospec(lospecField.text) }
        }

        MintLabel { text: "Gradient"; font.bold: true }
        RowLayout {
            Layout.fillWidth: true
            MintTextField { id: startColor; Layout.fillWidth: true; text: "#163B2A" }
            MintTextField { id: endColor; Layout.fillWidth: true; text: "#F1E66B" }
        }
        RowLayout {
            Layout.fillWidth: true
            MintSpinBox { id: gradientCount; from: 2; to: 256; value: 8; Layout.preferredWidth: 90 }
            MintComboBox { id: colorSpace; Layout.fillWidth: true; model: ["OKLab", "RGB", "Linear RGB", "HSV", "HSL"] }
            MintButton { text: "Generate"; onClicked: backend.generatePalette(startColor.text, endColor.text, gradientCount.value, colorSpace.currentText) }
        }
        Item { Layout.fillHeight: true }
    }

    ColorDialog {
        id: colorDialog
        title: root.colorEditIndex >= 0 ? "Edit palette color" : "Add palette color"
        onAccepted: {
            var value = selectedColor.toString()
            if (root.colorEditIndex >= 0) backend.setPaletteColor(root.colorEditIndex, value)
            else backend.addPaletteColor(value)
        }
    }

    Dialog {
        id: saveLibraryDialog
        title: "Save palette to library"
        modal: true
        width: Math.min(360, root.width - 24)
        x: Math.round((root.width - width) / 2)
        y: Math.max(12, Math.round((root.height - height) / 2))
        standardButtons: Dialog.Save | Dialog.Cancel

        onOpened: {
            var currentName = backend.settingsMap.palette_name || ""
            paletteNameField.text = currentName === "Custom" ? "Custom Palette" : currentName
            paletteCategoryField.text = "Custom"
            paletteNameField.forceActiveFocus()
            paletteNameField.selectAll()
        }
        onAccepted: backend.savePaletteToLibrary(paletteNameField.text, paletteCategoryField.text)

        contentItem: ColumnLayout {
            spacing: 8
            MintLabel { text: "Name" }
            MintTextField { id: paletteNameField; Layout.fillWidth: true; placeholderText: "Palette name" }
            MintLabel { text: "Category" }
            MintTextField { id: paletteCategoryField; Layout.fillWidth: true; placeholderText: "Custom" }
        }
    }

    FileDialog {
        id: importPaletteDialog
        nameFilters: ["Palette files (*.json *.hex *.txt *.gpl *.pal)", "All files (*)"]
        onAccepted: backend.importPalette(selectedFile.toString())
    }
    FileDialog {
        id: exportJsonDialog
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["RasterMint palette (*.json)"]
        onAccepted: backend.exportPaletteJson(selectedFile.toString())
    }
    FileDialog {
        id: exportHexDialog
        fileMode: FileDialog.SaveFile
        defaultSuffix: "hex"
        nameFilters: ["HEX palette (*.hex)"]
        onAccepted: backend.exportPalette(selectedFile.toString())
    }
}
