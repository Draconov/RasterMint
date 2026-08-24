import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Item {
    id: root
    property int colorEditIndex: -1
    property var expandedPaletteCategories: ({})
    property var optimizedPaletteCounts: [2, 3, 6, 8, 12, 16, 32, 256]
    property var gradientStops: ["#163B2A", "#F1E66B"]
    property var gradientStopPositions: [0.0, 1.0]
    property bool gradientPresetsExpanded: false
    property var gradientPresets: backend.gradientPresets || []

    function evenGradientPositions(count) {
        var positions = []
        for (var i = 0; i < count; ++i)
            positions.push(count <= 1 ? 0.0 : i / (count - 1))
        return positions
    }

    function updateGradientStop(index, value) {
        var next = gradientStops.slice(0)
        next[index] = value
        gradientStops = next
    }

    function addGradientStop() {
        if (gradientStops.length >= 10)
            return
        var next = gradientStops.slice(0)
        next.push(next.length ? next[next.length - 1] : "#FFFFFF")
        gradientStops = next
        gradientStopPositions = evenGradientPositions(next.length)
    }

    function removeGradientStop(index) {
        if (gradientStops.length <= 2)
            return
        var next = gradientStops.slice(0)
        next.splice(index, 1)
        gradientStops = next
        gradientStopPositions = evenGradientPositions(next.length)
    }

    function moveGradientStop(index, delta) {
        var target = index + delta
        if (target < 0 || target >= gradientStops.length)
            return
        var next = gradientStops.slice(0)
        var value = next[index]
        next.splice(index, 1)
        next.splice(target, 0, value)
        gradientStops = next
    }

    function applyGradientPreset(preset) {
        var colors = (preset.colors || []).slice(0)
        var positions = preset.positions || []
        var resolvedPositions = positions.length === colors.length
            ? positions.slice(0) : evenGradientPositions(colors.length)

        gradientStops = colors
        gradientStopPositions = resolvedPositions

        // The reference presets are CSS-style sRGB gradients. Selecting one
        // updates the editor and immediately applies the generated palette to
        // the active image, matching the custom Gradient > Generate workflow.
        colorSpace.currentIndex = 1
        backend.generatePaletteFromPositionedStops(colors, resolvedPositions, gradientCount.value, "RGB")
    }

    function gradientPresetSelected(preset) {
        var positions = preset.positions || []
        return JSON.stringify(gradientStops) === JSON.stringify(preset.colors || [])
            && JSON.stringify(gradientStopPositions) === JSON.stringify(positions.length === gradientStops.length
                ? positions : evenGradientPositions(gradientStops.length))
    }

    function paletteLibraryCategoryChoices() {
        var result = ["Custom"]
        var seen = {"Custom": true}
        var library = backend.paletteLibrary || []
        for (var i = 0; i < library.length; ++i) {
            var category = paletteDisplayCategory(library[i])
            if (category.length > 0 && !seen[category]) {
                seen[category] = true
                result.push(category)
            }
        }
        result.sort(function(a, b) { return a.localeCompare(b) })
        result.push("New category…")
        return result
    }

    function categoryForSaveDialog() {
        if (saveCategoryCombo.currentText === "New category…")
            return saveCustomCategory.text.trim()
        return saveCategoryCombo.currentText.trim()
    }


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

    function paletteDisplayCategory(palette) {
        var category = String(palette.category || "Other")
        switch (category) {
        case "RasterMint":
            return "RasterMint"
        case "Nintendo":
            return "Nintendo"
        case "Sega":
            return "Sega"
        case "Commodore":
            return "Commodore & Amiga"
        case "IBM PC":
            return "IBM PC"
        case "Monochrome Monitor":
            return "Monochrome Displays"
        case "NEC":
        case "Sharp":
        case "Fujitsu":
            return "Japanese Computers"
        case "Mattel":
        case "Coleco":
        case "SNK":
        case "Bandai":
            return "Other Consoles & Handhelds"
        case "Fantasy Console":
            return "Fantasy Consoles"
        case "Sinclair":
        case "Amstrad":
        case "MSX":
        case "Texas Instruments":
        case "Apple":
        case "Atari":
        case "Acorn":
        case "Broadcast":
        case "Oric":
        case "Motorola 6847":
        case "Tandy":
        case "MGT":
        case "Thomson":
            return "Home Computers"
        default:
            return category
        }
    }

    function allPaletteItems() {
        // Optimized entries are dynamic library actions: choosing one extracts
        // that many colours from the currently loaded source image using the
        // optimizer selected below the library.
        var result = []
        for (var i = 0; i < optimizedPaletteCounts.length; ++i) {
            var count = optimizedPaletteCounts[i]
            result.push({
                "id": "optimized-" + count,
                "name": "Optimized " + count,
                "category": "Optimized",
                "description": "Extract " + count + " colours from the current source image.",
                "colors": [],
                "optimized": true,
                "count": count
            })
        }

        var library = backend.paletteLibrary || []
        for (var j = 0; j < library.length; ++j)
            result.push(library[j])
        return result
    }

    function palettesForCategory(categoryName) {
        var result = []
        var palettes = allPaletteItems()
        for (var i = 0; i < palettes.length; ++i) {
            var palette = palettes[i]
            if (paletteDisplayCategory(palette) === categoryName && paletteMatches(palette))
                result.push(palette)
        }
        return result
    }

    function visiblePaletteCategories() {
        var result = []
        var seen = {}
        var palettes = allPaletteItems()
        for (var i = 0; i < palettes.length; ++i) {
            var palette = palettes[i]
            var category = paletteDisplayCategory(palette)
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

            Rectangle {
                id: paletteLibraryPanel
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(330, Math.max(220, root.height * 0.42))
                Layout.minimumHeight: 220
                Layout.maximumHeight: 330
                radius: 8
                color: theme.panelRaisedColor
                border.color: theme.borderColor
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 7

                    MintTextField {
                        id: searchField
                        Layout.fillWidth: true
                        placeholderText: "Search palettes…"
                    }

                    ScrollView {
                        id: libraryScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: availableWidth
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded

                        ColumnLayout {
                            id: libraryColumn
                            width: libraryScroll.availableWidth
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
                                        color: categoryMouse.containsMouse ? theme.panelHoverColor : theme.panelColor
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
                                                property bool isCurrentPalette: String(backend.settingsMap.palette_name || "") === String(modelData.name || "")
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 46
                                                radius: 6
                                                color: isCurrentPalette
                                                       ? theme.selectionColor
                                                       : (paletteMouse.containsMouse ? theme.panelHoverColor : "transparent")
                                                border.color: isCurrentPalette ? theme.accentColor : "transparent"
                                                border.width: isCurrentPalette ? 1 : 0

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
                                                            text: modelData.optimized
                                                                  ? ("Pull " + modelData.count + " colors from source")
                                                                  : (modelData.colors.length + " colors")
                                                            color: theme.mutedTextColor
                                                            font.pixelSize: 10
                                                            elide: Text.ElideRight
                                                        }
                                                    }

                                                    Row {
                                                        visible: !Boolean(modelData.optimized)
                                                        spacing: 0
                                                        Repeater {
                                                            model: modelData.optimized ? [] : modelData.colors.slice(0, 8)
                                                            Rectangle { width: 11; height: 24; color: modelData }
                                                        }
                                                    }

                                                    Text {
                                                        visible: Boolean(modelData.optimized)
                                                        text: "IMAGE"
                                                        color: backend.hasSource ? theme.accentColor : theme.mutedTextColor
                                                        font.bold: true
                                                        font.pixelSize: 9
                                                    }
                                                }

                                                MouseArea {
                                                    id: paletteMouse
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    enabled: !Boolean(modelData.optimized) || backend.hasSource
                                                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                                    onClicked: {
                                                        if (modelData.optimized)
                                                            backend.optimizePalette(modelData.count, optimizer.currentText)
                                                        else
                                                            backend.applyPalette(modelData.id)
                                                    }
                                                }

                                                ToolTip.visible: paletteMouse.containsMouse
                                                ToolTip.text: modelData.optimized && !backend.hasSource
                                                              ? "Load an image to extract this optimized palette."
                                                              : modelData.description
                                            }
                                        }
                                    }
                                }
                            }

                            Item {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 2
                            }
                        }
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width >= 520 ? 4 : 2
                columnSpacing: 6
                rowSpacing: 6

                MintButton { Layout.fillWidth: true; text: "Import…"; onClicked: importPaletteDialog.open() }
                MintButton { Layout.fillWidth: true; text: "Save to Library"; onClicked: savePaletteLibraryDialog.open() }
                MintButton { Layout.fillWidth: true; text: "Export JSON…"; onClicked: exportPaletteJsonDialog.open() }
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
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                radius: 7
                color: gradientPresetMouse.containsMouse ? theme.panelHoverColor : theme.panelRaisedColor
                border.color: theme.borderColor

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8
                    Text {
                        text: root.gradientPresetsExpanded ? "▾" : "▸"
                        color: theme.accentColor
                        font.pixelSize: 14
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Gradient Presets"
                        color: theme.textColor
                        font.bold: true
                        font.pixelSize: 12
                    }
                    Text {
                        text: String(root.gradientPresets.length)
                        color: theme.mutedTextColor
                        font.pixelSize: 10
                    }
                }
                MouseArea {
                    id: gradientPresetMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.gradientPresetsExpanded = !root.gradientPresetsExpanded
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: root.gradientPresetsExpanded ? 176 : 0
                visible: root.gradientPresetsExpanded
                radius: 7
                color: theme.panelRaisedColor
                border.color: theme.borderColor
                clip: true

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 7
                    clip: true
                    contentWidth: availableWidth
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                    GridLayout {
                        width: parent.width
                        columns: width >= 500 ? 4 : (width >= 350 ? 3 : 2)
                        columnSpacing: 6
                        rowSpacing: 6

                        Repeater {
                            model: root.gradientPresets

                            delegate: Rectangle {
                                id: presetCard
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: 38
                                radius: 5
                                color: theme.canvasColor
                                border.color: root.gradientPresetSelected(modelData) ? theme.accentColor : theme.borderColor
                                border.width: root.gradientPresetSelected(modelData) ? 2 : 1
                                clip: true

                                Canvas {
                                    id: presetCanvas
                                    anchors.fill: parent
                                    anchors.margins: 3
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.clearRect(0, 0, width, height)
                                        var gradient = ctx.createLinearGradient(0, 0, width, 0)
                                        var colors = presetCard.modelData.colors
                                        var positions = presetCard.modelData.positions || []
                                        for (var i = 0; i < colors.length; ++i) {
                                            var position = positions.length === colors.length
                                                ? positions[i] : (colors.length === 1 ? 0 : i / (colors.length - 1))
                                            gradient.addColorStop(position, colors[i])
                                        }
                                        ctx.fillStyle = gradient
                                        ctx.fillRect(0, 0, width, height)
                                    }
                                    Component.onCompleted: requestPaint()
                                    onWidthChanged: requestPaint()
                                    onHeightChanged: requestPaint()
                                }

                                MouseArea {
                                    id: presetMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.applyGradientPreset(presetCard.modelData)
                                }

                                ToolTip.visible: presetMouse.containsMouse
                                ToolTip.text: presetCard.modelData.name
                            }
                        }
                    }
                }
            }

            MintLabel {
                text: "Anchor colours"
                color: theme.mutedTextColor
                font.pixelSize: 11
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Repeater {
                    model: root.gradientStops.length

                    delegate: RowLayout {
                        required property int index
                        Layout.fillWidth: true
                        spacing: 6

                        MintColorPicker {
                            Layout.fillWidth: true
                            alphaEnabled: false
                            colorValue: root.gradientStops[index]
                            dialogTitle: "Gradient colour " + (index + 1)
                            onColorPicked: function(value) { root.updateGradientStop(index, value) }
                        }
                        MintButton {
                            text: "↑"
                            enabled: index > 0
                            onClicked: root.moveGradientStop(index, -1)
                        }
                        MintButton {
                            text: "↓"
                            enabled: index < root.gradientStops.length - 1
                            onClicked: root.moveGradientStop(index, 1)
                        }
                        MintButton {
                            text: "−"
                            enabled: root.gradientStops.length > 2
                            onClicked: root.removeGradientStop(index)
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    MintButton {
                        text: "+ Add colour"
                        enabled: root.gradientStops.length < 10
                        onClicked: root.addGradientStop()
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.gradientStops.length + " / 10 anchor colours"
                        color: theme.mutedTextColor
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 11
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                MintSpinBox { id: gradientCount; from: 2; to: 256; value: 8; Layout.preferredWidth: 90 }
                MintComboBox { id: colorSpace; Layout.fillWidth: true; model: ["OKLab", "RGB", "Linear RGB", "HSV", "HSL"] }
                MintButton {
                    text: "Generate"
                    onClicked: backend.generatePaletteFromPositionedStops(root.gradientStops, root.gradientStopPositions, gradientCount.value, colorSpace.currentText)
                }
            }

            Item { Layout.preferredHeight: 4 }
        }
    }

    Dialog {
        id: savePaletteLibraryDialog
        title: "Save palette to library"
        modal: true
        width: Math.min(430, root.width - 24)
        x: Math.round((root.width - width) / 2)
        y: Math.max(12, Math.round((root.height - height) / 2))
        padding: 12

        onOpened: {
            var currentName = String(backend.settingsMap.palette_name || "Custom Palette")
            savePaletteName.text = currentName.length > 0 ? currentName : "Custom Palette"
            saveCustomCategory.text = ""
            var choices = root.paletteLibraryCategoryChoices()
            var customIndex = choices.indexOf("Custom")
            saveCategoryCombo.currentIndex = customIndex >= 0 ? customIndex : 0
            savePaletteName.forceActiveFocus()
            savePaletteName.selectAll()
        }

        contentItem: ColumnLayout {
            spacing: 8

            MintLabel { text: "Name" }
            MintTextField {
                id: savePaletteName
                Layout.fillWidth: true
                placeholderText: "Palette name"
            }

            MintLabel { text: "Category" }
            MintComboBox {
                id: saveCategoryCombo
                Layout.fillWidth: true
                model: root.paletteLibraryCategoryChoices()
            }

            MintTextField {
                id: saveCustomCategory
                Layout.fillWidth: true
                visible: saveCategoryCombo.currentText === "New category…"
                placeholderText: "New category name"
            }
        }

        footer: RowLayout {
            spacing: 6
            Item { Layout.fillWidth: true }
            MintButton { text: "Cancel"; onClicked: savePaletteLibraryDialog.close() }
            MintButton {
                text: "Save"
                enabled: savePaletteName.text.trim().length > 0 && root.categoryForSaveDialog().length > 0
                onClicked: {
                    backend.savePaletteToLibrary(savePaletteName.text.trim(), root.categoryForSaveDialog())
                    savePaletteLibraryDialog.close()
                }
            }
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
        id: exportPaletteJsonDialog
        title: "Export RasterMint palette as JSON"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["JSON palette (*.json)"]
        onAccepted: backend.exportPaletteJson(selectedFile.toString())
    }

    FileDialog {
        id: exportPaletteDialog
        fileMode: FileDialog.SaveFile
        defaultSuffix: "hex"
        nameFilters: ["HEX palette (*.hex)"]
        onAccepted: backend.exportPalette(selectedFile.toString())
    }
}
