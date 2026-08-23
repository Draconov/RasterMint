import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Item {
    id: root
    property int colorEditIndex: -1
    property var expandedPaletteCategories: ({})

    function paletteCategoryExpanded(name) {
        // Search results should be immediately visible without forcing the user
        // to manually open every matching category.
        return searchField.text.trim().length > 0 || Boolean(expandedPaletteCategories[name])
    }

    function togglePaletteCategory(name) {
        var next = {}
        for (var key in expandedPaletteCategories)
            next[key] = expandedPaletteCategories[key]
        next[name] = !Boolean(next[name])
        expandedPaletteCategories = next
    }

    function paletteMatches(palette) {
        var query = searchField.text.trim().toLowerCase()
        if (query.length === 0)
            return true
        var haystack = String(palette.name || "") + " "
                     + String(palette.category || "") + " "
                     + String(palette.description || "")
        return haystack.toLowerCase().indexOf(query) >= 0
    }

    function palettesForCategory(categoryName) {
        var result = []
        var palettes = backend.paletteLibrary || []
        for (var i = 0; i < palettes.length; ++i) {
            var palette = palettes[i]
            if (String(palette.category || "") === categoryName && paletteMatches(palette))
                result.push(palette)
        }
        return result
    }

    function visiblePaletteCategories() {
        var result = []
        var seen = {}
        var palettes = backend.paletteLibrary || []
        for (var i = 0; i < palettes.length; ++i) {
            var palette = palettes[i]
            var category = String(palette.category || "Other")
            if (!seen[category] && paletteMatches(palette)) {
                seen[category] = true
                result.push(category)
            }
        }
        return result
    }

    ScrollView {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        ColumnLayout {
            width: pageScroll.availableWidth
            spacing: 9

            MintLabel { text: "Palette"; font.bold: true; font.pixelSize: 15 }
            MintLabel {
                Layout.fillWidth: true
                text: (backend.settingsMap.palette_name || "Custom") + " · " + (backend.settingsMap.palette || []).length + " colors"
                color: theme.mutedTextColor
                elide: Text.ElideRight
            }

            Flickable {
                id: swatchFlick
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                contentWidth: swatches.width
                contentHeight: height
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }

                Row {
                    id: swatches
                    spacing: 4
                    Repeater {
                        model: backend.settingsMap.palette || []
                        Rectangle {
                            width: 38
                            height: 38
                            radius: 5
                            color: modelData
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
                                        paletteColorPicker.dialogTitle = "Edit palette color"
                                        paletteColorPicker.openPicker(modelData)
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
                        paletteColorPicker.dialogTitle = "Add palette color"
                        paletteColorPicker.openPicker(colors.length ? colors[colors.length - 1] : "#FFFFFF")
                    }
                }
                MintButton {
                    text: "−"
                    enabled: (backend.settingsMap.palette || []).length > 1
                    onClicked: backend.removePaletteColor(-1)
                }
                MintButton {
                    Layout.fillWidth: true
                    text: "Shuffle unlocked"
                    onClicked: backend.shufflePaletteUnlocked()
                }
                MintButton {
                    Layout.fillWidth: true
                    text: "Randomize unlocked"
                    onClicked: backend.randomizePaletteUnlocked()
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
            MintLabel { text: "Palette Library"; font.bold: true }

            MintTextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: "Search palettes…"
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Repeater {
                    model: root.visiblePaletteCategories()

                    delegate: ColumnLayout {
                        id: categorySection
                        required property string modelData
                        property string categoryName: modelData
                        property var categoryPalettes: root.palettesForCategory(categoryName)
                        Layout.fillWidth: true
                        spacing: 4

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 38
                            radius: 7
                            color: categoryMouse.containsMouse ? theme.panelHoverColor : theme.panelRaisedColor
                            border.color: theme.borderColor

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: 8

                                Text {
                                    text: root.paletteCategoryExpanded(categorySection.categoryName) ? "▾" : "▸"
                                    color: theme.accentColor
                                    font.pixelSize: 14
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: categorySection.categoryName
                                    color: theme.textColor
                                    font.bold: true
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: String(categorySection.categoryPalettes.length)
                                    color: theme.mutedTextColor
                                    font.pixelSize: 10
                                }
                            }

                            MouseArea {
                                id: categoryMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.togglePaletteCategory(categorySection.categoryName)
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            visible: root.paletteCategoryExpanded(categorySection.categoryName)

                            Repeater {
                                model: root.paletteCategoryExpanded(categorySection.categoryName)
                                       ? categorySection.categoryPalettes : []

                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 46
                                    radius: 6
                                    color: paletteMouse.containsMouse ? theme.panelHoverColor : "transparent"

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 6
                                        anchors.rightMargin: 6
                                        spacing: 8

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
                                                Layout.fillWidth: true
                                                text: modelData.colors.length + " colors"
                                                color: theme.mutedTextColor
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                            }
                                        }

                                        Row {
                                            spacing: 0
                                            Repeater {
                                                model: modelData.colors.slice(0, 8)
                                                Rectangle { width: 11; height: 24; color: modelData }
                                            }
                                        }
                                    }

                                    MouseArea {
                                        id: paletteMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: backend.applyPalette(modelData.id)
                                    }

                                    ToolTip.visible: paletteMouse.containsMouse
                                    ToolTip.text: modelData.description
                                }
                            }
                        }
                    }
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
                MintSpinBox { id: colorCount; from: 2; to: 256; value: 8; editable: true; Layout.preferredWidth: 90 }
                MintComboBox { id: optimizer; Layout.fillWidth: true; model: backend.paletteOptimizerNames }
                MintButton {
                    text: "Optimize"
                    enabled: backend.hasSource
                    onClicked: backend.optimizePalette(colorCount.value, optimizer.currentText)
                }
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
                MintColorPicker {
                    id: startColor
                    Layout.fillWidth: true
                    colorValue: "#163B2A"
                    dialogTitle: "Gradient start colour"
                }
                MintColorPicker {
                    id: endColor
                    Layout.fillWidth: true
                    colorValue: "#F1E66B"
                    dialogTitle: "Gradient end colour"
                }
            }
            RowLayout {
                Layout.fillWidth: true
                MintSpinBox { id: gradientCount; from: 2; to: 256; value: 8; Layout.preferredWidth: 90 }
                MintComboBox { id: colorSpace; Layout.fillWidth: true; model: ["OKLab", "RGB", "Linear RGB", "HSV", "HSL"] }
                MintButton {
                    text: "Generate"
                    onClicked: backend.generatePalette(startColor.colorValue, endColor.colorValue, gradientCount.value, colorSpace.currentText)
                }
            }

            Item { Layout.preferredHeight: 4 }
        }
    }

    MintColorPicker {
        id: paletteColorPicker
        showButton: false
        width: 1
        height: 1
        x: Math.max(0, Math.round((root.width - 324) / 2))
        y: 48
        alphaEnabled: false
        onColorPicked: function(value) {
            if (root.colorEditIndex >= 0)
                backend.setPaletteColor(root.colorEditIndex, value)
            else
                backend.addPaletteColor(value)
        }
    }

    FileDialog {
        id: importPaletteDialog
        nameFilters: ["Palette files (*.hex *.txt *.gpl *.pal)", "All files (*)"]
        onAccepted: backend.importPalette(selectedFile.toString())
    }

    FileDialog {
        id: exportPaletteDialog
        fileMode: FileDialog.SaveFile
        defaultSuffix: "hex"
        nameFilters: ["HEX palette (*.hex)"]
        onAccepted: backend.exportPalette(selectedFile.toString())
    }
}
