import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Item {
    id: root
    property int colorEditIndex: -1
    property var expandedPaletteCategories: ({})
    property string lastAppliedPaletteSignature: ""
    property var optimizedPaletteCounts: [2, 3, 6, 8, 12, 16, 32, 256]
    property var gradientStops: ["#163B2A", "#F1E66B"]
    property var gradientStopPositions: [0.0, 1.0]
    property bool gradientPresetsExpanded: false
    property var gradientPresets: backend.gradientPresets || []
    property bool gradientDirty: false

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
        gradientDirty = true
    }

    function addGradientStop() {
        if (gradientStops.length >= 10)
            return
        var next = gradientStops.slice(0)
        next.push(next.length ? next[next.length - 1] : "#FFFFFF")
        gradientStops = next
        gradientStopPositions = evenGradientPositions(next.length)
        gradientDirty = true
    }

    function removeGradientStop(index) {
        if (gradientStops.length <= 2)
            return
        var next = gradientStops.slice(0)
        next.splice(index, 1)
        gradientStops = next
        gradientStopPositions = evenGradientPositions(next.length)
        gradientDirty = true
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
        gradientDirty = true
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
        gradientDirty = false
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

    function paletteSignature() {
        var settings = backend.settingsMap || {}
        return String(settings.palette_name || "") + "|" + JSON.stringify(settings.palette || [])
    }

    function samePaletteColors(left, right) {
        var a = left || []
        var b = right || []
        if (a.length !== b.length)
            return false
        for (var i = 0; i < a.length; ++i) {
            if (String(a[i]).toUpperCase() !== String(b[i]).toUpperCase())
                return false
        }
        return a.length > 0
    }

    function appliedPaletteCategory() {
        var settings = backend.settingsMap || {}
        var currentName = String(settings.palette_name || "")
        var currentColors = settings.palette || []
        var palettes = allPaletteItems()

        // Prefer the explicit palette name. This covers normal palette-library
        // selections and dynamic Optimized N palettes used by presets.
        for (var i = 0; i < palettes.length; ++i) {
            if (String(palettes[i].name || "") === currentName)
                return paletteDisplayCategory(palettes[i])
        }

        // Hardware profiles sometimes use a descriptive hardware palette name
        // that differs from the equivalent library entry (for example C64 16
        // versus Commodore 64). Match exact colour lists as a useful fallback.
        for (var j = 0; j < palettes.length; ++j) {
            if (!Boolean(palettes[j].optimized) && samePaletteColors(palettes[j].colors, currentColors))
                return paletteDisplayCategory(palettes[j])
        }
        return ""
    }

    function expandAppliedPaletteCategory() {
        var signature = paletteSignature()
        if (signature === lastAppliedPaletteSignature)
            return
        lastAppliedPaletteSignature = signature

        var category = appliedPaletteCategory()
        if (category.length === 0)
            return
        var next = {}
        for (var key in expandedPaletteCategories)
            next[key] = expandedPaletteCategories[key]
        next[category] = true
        expandedPaletteCategories = next
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
                "name": qsTr("Optimized %1").arg(count),
                "category": "Optimized",
                "description": qsTr("Extract %1 colours from the current source image.").arg(count),
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

    Component.onCompleted: Qt.callLater(root.expandAppliedPaletteCategory)

    Connections {
        target: backend
        function onSettingsChanged() {
            Qt.callLater(root.expandAppliedPaletteCategory)
        }
        function onPaletteLibraryChanged() {
            // A newly loaded/user palette may make the currently applied
            // palette resolvable to a category for the first time.
            root.lastAppliedPaletteSignature = ""
            Qt.callLater(root.expandAppliedPaletteCategory)
        }
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

            MintLabel { text: qsTr("Palette"); font.bold: true; font.pixelSize: 15 }
            MintLabel {
                Layout.fillWidth: true
                text: (backend.settingsMap.palette_name || qsTr("Custom")) + " · " + qsTr("%1 colours").arg((backend.settingsMap.palette || []).length)
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
                                acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                                cursorShape: Qt.PointingHandCursor
                                onClicked: function(mouse) {
                                    if (mouse.button === Qt.RightButton) {
                                        backend.setPaletteLock(index, !parent.locked)
                                    } else if (mouse.button === Qt.MiddleButton) {
                                        backend.removePaletteColor(index)
                                    } else {
                                        root.colorEditIndex = index
                                        paletteColorPicker.dialogTitle = "Edit palette color"
                                        paletteColorPicker.openPicker(modelData)
                                    }
                                }
                            }

                            ToolTip.visible: swatchMouse.containsMouse
                            ToolTip.text: (index + 1) + ": " + modelData
                                          + (locked
                                             ? " · locked · right-click to unlock"
                                             : " · right-click to lock · middle-click to delete")
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
                    text: qsTr("Randomize unlocked")
                    onClicked: backend.randomizePaletteUnlocked()
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
            MintLabel { text: qsTr("Palette Library"); font.bold: true }

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
                        placeholderText: qsTr("Search palettes…")
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
                                                                  ? qsTr("Pull %1 colours from source").arg(modelData.count)
                                                                  : qsTr("%1 colours").arg(modelData.colors.length)
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
                                                              ? qsTr("Load an image to extract this optimized palette.")
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

                MintButton { Layout.fillWidth: true; text: qsTr("Import…"); onClicked: importPaletteDialog.open() }
                MintButton { Layout.fillWidth: true; text: qsTr("Save to Library"); onClicked: savePaletteLibraryDialog.open() }
                MintButton { Layout.fillWidth: true; text: qsTr("Export JSON…"); onClicked: exportPaletteJsonDialog.open() }
                MintButton { Layout.fillWidth: true; text: qsTr("Export HEX…"); onClicked: exportPaletteDialog.open() }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
            MintLabel { text: qsTr("Optimize from image"); font.bold: true }
            RowLayout {
                Layout.fillWidth: true
                MintSpinBox { id: colorCount; from: 2; to: 256; value: 8; editable: true; Layout.preferredWidth: 90 }
                MintComboBox { id: optimizer; Layout.fillWidth: true; model: backend.paletteOptimizerNames }
                MintButton {
                    text: qsTr("Optimize")
                    enabled: backend.hasSource
                    onClicked: backend.optimizePalette(colorCount.value, optimizer.currentText)
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
            MintLabel { text: qsTr("Palette & Dither Lab"); font.bold: true }
            MintLabel {
                Layout.fillWidth: true
                text: qsTr("Analyse palette usage, ramps, colour distance, duplicates and custom ordered-dither matrices.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.fillWidth: true
                MintButton { text: qsTr("Analyse"); onClicked: backend.refreshPaletteLab() }
                MintButton { text: qsTr("Remove unused"); enabled: Number((backend.paletteLabData || {}).unused_count || 0) > 0; onClicked: backend.removeUnusedPaletteColors() }
                MintButton { text: qsTr("Reduce suggestion"); enabled: Number((backend.paletteLabData || {}).suggested_count || 0) > 0; onClicked: backend.applyPaletteReductionSuggestion() }
            }
            MintLabel {
                Layout.fillWidth: true
                visible: Object.keys(backend.paletteLabData || {}).length > 0
                text: qsTr("Sampled %1 pixels · %2 unused · suggested %3 colours")
                    .arg(Number((backend.paletteLabData || {}).sample_count || 0))
                    .arg(Number((backend.paletteLabData || {}).unused_count || 0))
                    .arg(Number((backend.paletteLabData || {}).suggested_count || 0))
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
            }
            Flow {
                Layout.fillWidth: true
                spacing: 6
                MintButton { text: qsTr("Sort luminance"); onClicked: backend.sortPalette("luminance") }
                MintButton { text: qsTr("Sort hue"); onClicked: backend.sortPalette("hue") }
                MintButton { text: qsTr("Sort saturation"); onClicked: backend.sortPalette("saturation") }
                MintButton { text: qsTr("Sort value"); onClicked: backend.sortPalette("value") }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: paletteUsageColumn.implicitHeight + 14
                visible: ((backend.paletteLabData || {}).colors || []).length > 0
                radius: 6
                color: theme.panelRaisedColor
                border.color: theme.borderColor
                ColumnLayout {
                    id: paletteUsageColumn
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.margins: 7
                    spacing: 3
                    MintLabel { text: qsTr("Colour usage histogram"); font.bold: true }
                    Repeater {
                        model: ((backend.paletteLabData || {}).colors || []).slice(0, 32)
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 5
                            Rectangle { width: 16; height: 16; radius: 2; color: modelData.color; border.color: theme.borderColor }
                            MintLabel { Layout.preferredWidth: 62; text: modelData.color; font.pixelSize: 9 }
                            Rectangle {
                                Layout.fillWidth: true; height: 8; radius: 4; color: theme.panelColor
                                Rectangle {
                                    width: parent.width * Math.min(1.0, Number(modelData.usage_percent || 0) / 100.0)
                                    height: parent.height; radius: parent.radius; color: modelData.unused ? theme.mutedTextColor : theme.accentColor
                                }
                            }
                            MintLabel { Layout.preferredWidth: 45; horizontalAlignment: Text.AlignRight; text: Number(modelData.usage_percent || 0).toFixed(1) + "%"; font.pixelSize: 9 }
                        }
                    }
                    MintLabel {
                        Layout.fillWidth: true
                        visible: ((backend.paletteLabData || {}).near_duplicates || []).length > 0
                        text: qsTr("Near-duplicate pairs: %1").arg(((backend.paletteLabData || {}).near_duplicates || []).length)
                        color: theme.mutedTextColor
                    }
                    MintLabel {
                        Layout.fillWidth: true
                        visible: ((backend.paletteLabData || {}).ramps || []).length > 0
                        text: qsTr("Detected ramps: %1").arg(((backend.paletteLabData || {}).ramps || []).length)
                        color: theme.mutedTextColor
                    }
                }
            }

            MintLabel { text: qsTr("Dither Matrix Designer"); font.bold: true }
            RowLayout {
                Layout.fillWidth: true
                MintLabel { text: qsTr("Size"); color: theme.mutedTextColor }
                MintSpinBox {
                    from: 2; to: 16; value: backend.customDitherMatrixSize
                    onValueModified: backend.setCustomDitherMatrixSize(value)
                }
                MintButton { text: qsTr("Reset Bayer 4×4"); onClicked: backend.resetCustomDitherMatrix() }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(84, Math.min(360, matrixGrid.implicitHeight + 14))
                radius: 6
                color: theme.panelRaisedColor
                border.color: theme.borderColor
                clip: true
                Flickable {
                    anchors.fill: parent; anchors.margins: 7
                    contentWidth: matrixGrid.implicitWidth; contentHeight: matrixGrid.implicitHeight
                    clip: true
                    GridLayout {
                        id: matrixGrid
                        columns: Math.max(2, backend.customDitherMatrixSize)
                        rowSpacing: 3; columnSpacing: 3
                        Repeater {
                            model: {
                                var result = []
                                var matrix = backend.customDitherMatrix || []
                                for (var y = 0; y < matrix.length; ++y)
                                    for (var x = 0; x < matrix[y].length; ++x)
                                        result.push({"row": y, "column": x, "value": matrix[y][x]})
                                return result
                            }
                            delegate: MintTextField {
                                Layout.preferredWidth: 48
                                Layout.preferredHeight: 30
                                text: Number(modelData.value).toString()
                                validator: DoubleValidator {}
                                horizontalAlignment: Text.AlignHCenter
                                onEditingFinished: backend.setCustomDitherMatrixCell(modelData.row, modelData.column, Number(text))
                            }
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                MintTextField { id: matrixNameField; Layout.fillWidth: true; placeholderText: qsTr("Matrix name") }
                MintButton { text: qsTr("Save matrix"); onClicked: backend.saveCustomDitherMatrix(matrixNameField.text) }
            }
            RowLayout {
                Layout.fillWidth: true
                MintComboBox {
                    id: savedMatrixCombo
                    Layout.fillWidth: true
                    model: (backend.ditherMatrixLibrary || []).map(function(item) { return item.name })
                }
                MintButton { text: qsTr("Load matrix"); enabled: savedMatrixCombo.currentIndex >= 0; onClicked: backend.loadCustomDitherMatrix(savedMatrixCombo.currentText) }
            }

            MintLabel { text: qsTr("Lospec"); font.bold: true }
            RowLayout {
                Layout.fillWidth: true
                MintTextField { id: lospecField; Layout.fillWidth: true; placeholderText: qsTr("slug or Lospec URL") }
                MintButton { text: qsTr("Fetch"); enabled: lospecField.text.length > 0; onClicked: backend.fetchLospec(lospecField.text) }
            }

            MintLabel { text: qsTr("Gradient"); font.bold: true }
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
                        text: qsTr("Gradient Presets")
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
                text: qsTr("Anchor colours")
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
                            dialogTitle: qsTr("Gradient colour %1").arg(index + 1)
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
                        text: qsTr("+ Add colour")
                        enabled: root.gradientStops.length < 10
                        onClicked: root.addGradientStop()
                    }
                    Text {
                        Layout.fillWidth: true
                        text: qsTr("%1 / 10 anchor colours").arg(root.gradientStops.length)
                        color: theme.mutedTextColor
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 11
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                MintSpinBox {
                    id: gradientCount
                    from: 2
                    to: 256
                    value: 8
                    Layout.preferredWidth: 90
                    onValueModified: root.gradientDirty = true
                }
                MintComboBox {
                    id: colorSpace
                    Layout.fillWidth: true
                    model: ["OKLab", "RGB", "Linear RGB", "HSV", "HSL"]
                    onActivated: root.gradientDirty = true
                }
                MintButton {
                    text: qsTr("Generate")
                    selected: root.gradientDirty
                    onClicked: {
                        backend.generatePaletteFromPositionedStops(root.gradientStops, root.gradientStopPositions, gradientCount.value, colorSpace.currentText)
                        root.gradientDirty = false
                    }
                }
            }

            Item { Layout.preferredHeight: 4 }
        }
    }

    Dialog {
        id: savePaletteLibraryDialog
        title: qsTr("Save palette to library")
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

            MintLabel { text: qsTr("Name") }
            MintTextField {
                id: savePaletteName
                Layout.fillWidth: true
                placeholderText: qsTr("Palette name")
            }

            MintLabel { text: qsTr("Category") }
            MintComboBox {
                id: saveCategoryCombo
                Layout.fillWidth: true
                model: root.paletteLibraryCategoryChoices()
            }

            MintTextField {
                id: saveCustomCategory
                Layout.fillWidth: true
                visible: saveCategoryCombo.currentText === "New category…"
                placeholderText: qsTr("New category name")
            }
        }

        footer: RowLayout {
            spacing: 6
            Item { Layout.fillWidth: true }
            MintButton { text: qsTr("Cancel"); onClicked: savePaletteLibraryDialog.close() }
            MintButton {
                text: qsTr("Save")
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
        title: qsTr("Export RasterMint palette as JSON")
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
