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
            MintButton { text: "−"; enabled: (backend.settingsMap.palette || []).length > 1; onClicked: backend.removePaletteColor(-1) }
            MintButton { Layout.fillWidth: true; text: "Shuffle unlocked"; onClicked: backend.shufflePaletteUnlocked() }
            MintButton { Layout.fillWidth: true; text: "Randomize unlocked"; onClicked: backend.randomizePaletteUnlocked() }
        }

        MintTextField { id: searchField; Layout.fillWidth: true; placeholderText: "Search palettes…" }
        ListView {
            Layout.fillWidth: true
            Layout.preferredHeight: 190
            clip: true
            spacing: 3
            model: backend.paletteLibrary
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOff }
            delegate: Rectangle {
                width: ListView.view.width
                property bool matches: searchField.text.length === 0 || (modelData.name + " " + modelData.category + " " + modelData.description).toLowerCase().indexOf(searchField.text.toLowerCase()) >= 0
                height: matches ? 44 : 0
                visible: matches
                radius: 6
                color: paletteMouse.containsMouse ? theme.panelHoverColor : "transparent"
                RowLayout {
                    anchors.fill: parent; anchors.margins: 5
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 0
                        Text { text: modelData.name; color: theme.textColor; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                        Text { text: modelData.category + " · " + modelData.colors.length + " colors"; color: theme.mutedTextColor; font.pixelSize: 10 }
                    }
                    Row {
                        spacing: 0
                        Repeater {
                            model: modelData.colors.slice(0, 8)
                            Rectangle { width: 11; height: 24; color: modelData }
                        }
                    }
                }
                MouseArea { id: paletteMouse; anchors.fill: parent; hoverEnabled: true; onClicked: backend.applyPalette(modelData.id) }
                ToolTip.visible: paletteMouse.containsMouse
                ToolTip.text: modelData.description
            }
        }

        RowLayout {
            Layout.fillWidth: true
            MintButton { Layout.fillWidth: true; text: "Import…"; onClicked: importPaletteDialog.open() }
            MintButton { Layout.fillWidth: true; text: "Export HEX…"; onClicked: exportPaletteDialog.open() }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
        MintLabel { text: "Optimize from image"; font.bold: true }
        RowLayout {
            Layout.fillWidth: true
            SpinBox { id: colorCount; from: 2; to: 256; value: 8; editable: true; Layout.preferredWidth: 90 }
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
            SpinBox { id: gradientCount; from: 2; to: 256; value: 8; Layout.preferredWidth: 90 }
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
    FileDialog { id: importPaletteDialog; nameFilters: ["Palette files (*.hex *.txt *.gpl *.pal)", "All files (*)"]; onAccepted: backend.importPalette(selectedFile) }
    FileDialog { id: exportPaletteDialog; fileMode: FileDialog.SaveFile; defaultSuffix: "hex"; nameFilters: ["HEX palette (*.hex)"]; onAccepted: backend.exportPalette(selectedFile) }
}
