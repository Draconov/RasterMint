import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Item {
    id: root

    // Keep the familiar two-card layout when the inspector has enough room,
    // but collapse to one card per row instead of squeezing cards too narrow.
    property int presetColumns: width >= 500 ? 2 : 1

    property var expandedPresetCategories: ({})
    property string managePresetId: ""
    property string managePresetName: ""
    property int mutationCount: 8
    property int mutationAmountPercent: 35
    property string selectedPresetId: ""
    property string selectedPresetName: ""

    function presetCategoryExpanded(name) {
        return Boolean(expandedPresetCategories[name])
    }

    function togglePresetCategory(name) {
        var next = {}
        for (var key in expandedPresetCategories)
            next[key] = expandedPresetCategories[key]
        next[name] = !Boolean(next[name])
        expandedPresetCategories = next
    }

    function setPresetCategoryExpanded(name, expanded) {
        var next = {}
        for (var key in expandedPresetCategories)
            next[key] = expandedPresetCategories[key]
        next[name] = Boolean(expanded)
        expandedPresetCategories = next
    }

    function selectPreset(presetId, presetName) {
        selectedPresetId = String(presetId || "")
        selectedPresetName = String(presetName || "")
    }

    property var presetCategories: [
        {
            "name": "Handhelds",
            "ids": [
                "game-boy", "game-boy-pocket", "game-boy-light", "game-boy-color",
                "game-boy-advance", "virtual-boy", "game-gear", "neo-geo-pocket", "wonderswan"
            ]
        },
        {
            "name": "Consoles",
            "ids": [
                "nes", "snes", "snes-svideo", "master-system", "mega-drive", "playstation",
                "intellivision", "colecovision"
            ]
        },
        {
            "name": "Commodore & Amiga",
            "ids": [
                "c64-multicolor", "vic-20", "plus4", "amiga-ocs",
                "amiga-wb13", "amiga-wb2", "amiga-wb3"
            ]
        },
        {
            "name": "Home Computers",
            "ids": [
                "apple-ii-hgr", "zx-spectrum", "cga-neon", "ega-crisp", "dos-vga", "vga-320",
                "amstrad-cpc", "msx", "ti994a", "mac-classic", "mac-gray", "macintosh-monochrome",
                "atari-st", "atari-8bit", "teletext", "oric-atmos",
                "dragon-coco", "coco3", "sam-coupe", "thomson"
            ]
        },
        {
            "name": "Japanese Computers",
            "ids": ["pc98", "x68000", "fmtowns"]
        },
        {
            "name": "Displays & Monochrome",
            "ids": [
                "crt-ntsc", "crt-pal", "consumer-crt", "pvm-crt", "arcade-crt", "cheap-rf-tv",
                "monochrome-lcd", "early-lcd", "game-boy-lcd", "oled-ghosting", "security-camera",
                "green-crt", "amber-monitor", "white-phosphor"
            ]
        },
        {
            "name": "VHS & Analog",
            "ids": [
                "vhs-clean", "vhs-sp", "vhs-ep", "vhs-home-video", "vhs-c-camcorder", "camcorder",
                "vhs-rental-tape", "vhs-damaged", "vhs-crt", "crt-vhs"
            ]
        },
        {
            "name": "Modulated Diffusion",
            "ids": [
                "mod-smooth-bloom", "mod-circuit-cyan", "mod-stucki-wire",
                "mod-contour-bend", "mod-waveform-bloom", "particle-star-field"
            ]
        },
        {
            "name": "Stylized & Print",
            "ids": ["halftone-print", "print-clean-cmyk", "print-vintage-screen", "print-2color-poster", "print-3color-riso", "print-newspaper-cmyk", "print-misregistered", "print-cheap-tshirt", "print-heavy-dot-gain", "vector", "accurate-1to1", "isolated-dither-glow"]
        },
        {
            "name": "Fantasy Consoles",
            "ids": ["pico-8", "tic-80"]
        }
    ]

    function resolvedPresetCategories() {
        // Built-in categories keep their curated order. User-created categories
        // are appended afterwards, while the separate Mutations category stays
        // last in the page below the repeater. If a user deliberately uses the
        // exact name of a built-in category, merge those presets into that
        // section instead of rendering a duplicate heading.
        var result = []
        var byName = {}
        for (var i = 0; i < presetCategories.length; ++i) {
            var source = presetCategories[i]
            var copy = {
                "name": String(source.name || ""),
                "ids": (source.ids || []).slice(0),
                "userCategory": false
            }
            byName[copy.name.toLowerCase()] = result.length
            result.push(copy)
        }

        var userCategories = backend.presetUserCategories || []
        var presets = allPresetItems()
        for (var j = 0; j < userCategories.length; ++j) {
            var categoryName = String(userCategories[j] || "").trim()
            if (categoryName.length === 0)
                continue
            var ids = []
            for (var k = 0; k < presets.length; ++k) {
                var preset = presets[k]
                if (Boolean(preset.user) && String(preset.userCategory || "") === categoryName)
                    ids.push(String(preset.id))
            }
            if (ids.length === 0)
                continue

            var key = categoryName.toLowerCase()
            if (byName[key] !== undefined) {
                var existing = result[byName[key]]
                existing.ids = existing.ids.concat(ids)
            } else {
                result.push({
                    "name": categoryName,
                    "ids": ids,
                    "userCategory": true
                })
                byName[key] = result.length - 1
            }
        }
        return result
    }

    function allPresetItems() {
        var source = backend.allPresets ? backend.allPresets : []
        var result = []
        var query = presetSearch.text.trim().toLowerCase()
        var filter = presetFilter.currentText
        for (var i = 0; i < source.length; ++i) {
            var item = source[i]
            var searchName = Boolean(item.user) ? String(item.name || "") : localization.translateRuntime(localization.effectiveLanguageId, String(item.name || ""))
            var searchDescription = Boolean(item.user) ? String(item.description || "") : localization.translateRuntime(localization.effectiveLanguageId, String(item.description || ""))
            var haystack = (searchName + " " + searchDescription + " " + String(item.userCategory || "")).toLowerCase()
            if (query.length > 0 && haystack.indexOf(query) < 0) continue
            if (filter === qsTr("Favorites") && !Boolean(item.favorite)) continue
            if (filter === qsTr("Recent") && Number(item.recentRank) < 0) continue
            if (filter === qsTr("Custom") && !Boolean(item.user)) continue
            result.push(item)
        }
        if (filter === qsTr("Recent"))
            result.sort(function(a, b) { return Number(a.recentRank) - Number(b.recentRank) })
        return result
    }

    function presetsForIds(ids) {
        var wanted = {}
        for (var i = 0; i < ids.length; ++i)
            wanted[ids[i]] = true

        var result = []
        var presets = allPresetItems()
        for (var j = 0; j < presets.length; ++j) {
            var preset = presets[j]
            if (wanted[String(preset.id)])
                result.push(preset)
        }
        return result
    }

    function categorizedIds() {
        var result = {}
        var categories = resolvedPresetCategories()
        for (var i = 0; i < categories.length; ++i) {
            var ids = categories[i].ids
            for (var j = 0; j < ids.length; ++j)
                result[ids[j]] = true
        }
        return result
    }

    function ungroupedPresets() {
        var grouped = categorizedIds()
        var result = []
        var presets = allPresetItems()
        for (var i = 0; i < presets.length; ++i) {
            var preset = presets[i]
            // Presets without a category stay directly accessible above the
            // grouped sections. Categorized user presets are rendered in their
            // user-created category after all built-in categories.
            if (!grouped[String(preset.id)])
                result.push(preset)
        }
        return result
    }

    Component {
        id: presetCardDelegate

        Rectangle {
            id: presetCard
            width: GridView.view.cellWidth - 8
            height: GridView.view.cellHeight - 8
            radius: 8
            clip: true
            color: presetMouse.containsMouse ? theme.panelHoverColor : theme.panelRaisedColor
            border.color: (!Boolean(modelData.mutation) && root.selectedPresetId === String(modelData.id)) ? theme.accentColor : theme.borderColor

            property bool isUserPreset: Boolean(modelData.user)
            property bool isMutation: Boolean(modelData.mutation)
            property string displayName: isUserPreset
                ? String(modelData.name || "")
                : localization.translateRuntime(localization.effectiveLanguageId, String(modelData.name || ""))
            property string descriptionText: isUserPreset
                ? String(modelData.description || "")
                : localization.translateRuntime(localization.effectiveLanguageId, String(modelData.description || ""))
            property string hardwareName: modelData.hardwareProfileName ? String(modelData.hardwareProfileName) : ""
            property string hardwareMode: modelData.hardwareMode ? String(modelData.hardwareMode) : ""
            property string hardwareText: hardwareName !== "" ? qsTr("Hardware: %1").arg(hardwareName) : ""

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 5

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 112
                    Layout.maximumHeight: 112
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
                    Layout.fillWidth: true
                    text: presetCard.displayName + (presetCard.isUserPreset ? " · " + qsTr("custom") : "")
                    color: theme.textColor
                    font.bold: true
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: presetCard.descriptionText
                    color: theme.mutedTextColor
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    maximumLineCount: presetCard.hardwareText !== "" ? 3 : 4
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    visible: presetCard.hardwareText !== ""
                    text: presetCard.hardwareText
                    color: theme.accentColor
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }

                Item { Layout.fillHeight: true }
            }

            MouseArea {
                id: presetMouse
                anchors.fill: parent
                hoverEnabled: true
                onClicked: {
                    if (presetCard.isMutation) {
                        backend.applyPresetMutation(modelData.id)
                    } else {
                        root.selectPreset(modelData.id, presetCard.displayName)
                        backend.applyPreset(modelData.id)
                    }
                }
            }

            MintButton {
                visible: !presetCard.isMutation
                z: 3
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 7
                width: 30; height: 28
                text: Boolean(modelData.favorite) ? "★" : "☆"
                onClicked: backend.togglePresetFavorite(modelData.id)
                ToolTip.visible: hovered
                ToolTip.text: Boolean(modelData.favorite) ? qsTr("Remove from favourites") : qsTr("Add to favourites")
            }

            MintButton {
                visible: presetCard.isUserPreset
                z: 2
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.margins: 7
                width: 30; height: 28
                text: "⋯"
                onClicked: {
                    root.managePresetId = String(modelData.id)
                    root.managePresetName = String(modelData.name)
                    managePresetNameField.text = root.managePresetName
                    managePresetDescriptionField.text = String(modelData.description || "")
                    managePresetCategoryField.text = String(modelData.userCategory || "")
                    managePresetDialog.open()
                }
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Manage custom preset")
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
                onClicked: {
                    if (root.selectedPresetId === String(modelData.id))
                        root.selectPreset("", "")
                    backend.deletePresetFromLibrary(modelData.id)
                }

                ToolTip.visible: hovered
                ToolTip.text: qsTr("Remove custom preset from library")
            }

            ToolTip.visible: presetMouse.containsMouse
            ToolTip.text: presetCard.hardwareText !== ""
                ? (presetCard.descriptionText + "\n" + presetCard.hardwareText
                   + (presetCard.hardwareMode !== "" ? (" · " + presetCard.hardwareMode) : ""))
                : presetCard.descriptionText
        }
    }

    component PresetGrid: GridView {
        id: grid
        property var presetModel: []

        model: presetModel
        cellWidth: width / root.presetColumns
        cellHeight: 204
        interactive: false
        clip: false
        implicitHeight: Math.ceil(presetModel.length / root.presetColumns) * cellHeight
        delegate: presetCardDelegate
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            MintLabel {
                text: qsTr("Presets")
                font.bold: true
                font.pixelSize: 15
                Layout.fillWidth: true
                Layout.minimumWidth: 62
            }

            MintButton {
                text: qsTr("Load JSON")
                Layout.minimumWidth: implicitWidth
                onClicked: loadPresetDialog.open()
            }

            MintButton {
                text: qsTr("Save JSON")
                Layout.minimumWidth: implicitWidth
                onClicked: savePresetDialog.open()
            }

            MintButton {
                text: qsTr("Save to Library")
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
                ToolTip.text: qsTr("Refresh preset thumbnails")
            }
        }

        RowLayout {
            Layout.fillWidth: true
            MintTextField { id: presetSearch; Layout.fillWidth: true; placeholderText: qsTr("Search presets…") }
            MintComboBox { id: presetFilter; Layout.preferredWidth: 126; model: [qsTr("All"), qsTr("Favorites"), qsTr("Recent"), qsTr("Custom")] }
            MintButton { text: qsTr("Import pack"); onClicked: importPresetPackDialog.open() }
            MintButton { text: qsTr("Export pack"); onClicked: exportPresetPackDialog.open() }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 76
            radius: 7
            color: theme.panelRaisedColor
            border.color: theme.borderColor

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 9
                spacing: 5

                RowLayout {
                    Layout.fillWidth: true
                    MintLabel { text: qsTr("Preset Mutation"); font.bold: true }
                    Item { Layout.fillWidth: true }
                    MintLabel {
                        visible: root.selectedPresetName !== ""
                        text: root.selectedPresetName
                        color: theme.accentColor
                        font.pixelSize: 10
                        elide: Text.ElideRight
                        Layout.maximumWidth: Math.max(120, parent.width * 0.42)
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 7
                    MintLabel { text: qsTr("Variants"); color: theme.mutedTextColor }
                    MintSpinBox {
                        from: 6; to: 12; value: root.mutationCount
                        onValueModified: root.mutationCount = value
                        Layout.preferredWidth: 72
                    }
                    Item { Layout.fillWidth: true }
                    MintLabel { text: qsTr("Mutation amount"); color: theme.mutedTextColor }
                    MintSpinBox {
                        from: 10; to: 100; stepSize: 5; value: root.mutationAmountPercent
                        onValueModified: root.mutationAmountPercent = value
                        Layout.preferredWidth: 82
                    }
                    MintLabel { text: "%"; color: theme.mutedTextColor }
                    MintButton {
                        text: qsTr("Mutate")
                        enabled: root.selectedPresetId !== ""
                        onClicked: {
                            backend.generatePresetMutations(
                                root.selectedPresetId,
                                root.mutationCount,
                                root.mutationAmountPercent / 100.0
                            )
                            root.setPresetCategoryExpanded("Mutations", true)
                        }
                        ToolTip.visible: hovered
                        ToolTip.text: enabled
                            ? qsTr("Generate controlled variations of this preset")
                            : qsTr("Select a preset first")
                    }
                }
            }
        }

        ScrollView {
            id: presetScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: presetScroll.availableWidth
                spacing: 8

                PresetGrid {
                    id: ungroupedGrid
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? implicitHeight : 0
                    visible: presetModel.length > 0
                    presetModel: root.ungroupedPresets()
                }

                Repeater {
                    model: root.resolvedPresetCategories()

                    delegate: ColumnLayout {
                        id: categorySection
                        Layout.fillWidth: true
                        spacing: 6

                        property var categoryData: modelData
                        property var categoryPresets: root.presetsForIds(categoryData.ids)

                        visible: categoryPresets.length > 0

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
                                    text: root.presetCategoryExpanded(categorySection.categoryData.name) ? "▾" : "▸"
                                    color: theme.accentColor
                                    font.pixelSize: 14
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: Boolean(categorySection.categoryData.userCategory)
                                        ? String(categorySection.categoryData.name)
                                        : localization.translateRuntime(localization.effectiveLanguageId, String(categorySection.categoryData.name))
                                    color: theme.textColor
                                    font.bold: true
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: String(categorySection.categoryPresets.length)
                                    color: theme.mutedTextColor
                                    font.pixelSize: 10
                                }
                            }

                            MouseArea {
                                id: categoryMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: root.togglePresetCategory(categorySection.categoryData.name)
                            }
                        }

                        PresetGrid {
                            Layout.fillWidth: true
                            Layout.preferredHeight: root.presetCategoryExpanded(categorySection.categoryData.name) ? implicitHeight : 0
                            visible: root.presetCategoryExpanded(categorySection.categoryData.name)
                            presetModel: categorySection.categoryPresets
                        }
                    }
                }

                ColumnLayout {
                    id: mutationCategorySection
                    Layout.fillWidth: true
                    spacing: 6
                    visible: backend.presetMutations && backend.presetMutations.length > 0

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        radius: 7
                        color: mutationCategoryMouse.containsMouse ? theme.panelHoverColor : theme.panelRaisedColor
                        border.color: theme.borderColor

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 8

                            Text {
                                text: root.presetCategoryExpanded("Mutations") ? "▾" : "▸"
                                color: theme.accentColor
                                font.pixelSize: 14
                            }

                            Text {
                                Layout.fillWidth: true
                                text: localization.translateRuntime(localization.effectiveLanguageId, "Mutations")
                                color: theme.textColor
                                font.bold: true
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }

                            Text {
                                text: String((backend.presetMutations || []).length)
                                color: theme.mutedTextColor
                                font.pixelSize: 10
                            }
                        }

                        MouseArea {
                            id: mutationCategoryMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: root.togglePresetCategory("Mutations")
                        }
                    }

                    PresetGrid {
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.presetCategoryExpanded("Mutations") ? implicitHeight : 0
                        visible: root.presetCategoryExpanded("Mutations")
                        presetModel: backend.presetMutations || []
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 2
                }
            }
        }
    }

    MintDialog {
        id: saveLibraryDialog
        title: qsTr("Save preset to library")
        width: Math.min(380, Overlay.overlay ? Overlay.overlay.width - 24 : root.width - 24)

        onOpened: {
            presetNameField.text = "Custom Preset"
            presetDescriptionField.text = ""
            presetNameField.forceActiveFocus()
            presetNameField.selectAll()
        }

        contentItem: ColumnLayout {
            spacing: 8
            MintLabel { text: qsTr("Name") }
            MintTextField {
                id: presetNameField
                Layout.fillWidth: true
                placeholderText: qsTr("Preset name")
            }
            MintLabel { text: qsTr("Description") }
            MintTextField {
                id: presetDescriptionField
                Layout.fillWidth: true
                placeholderText: qsTr("Optional description")
            }
        }

        footer: Rectangle {
            implicitHeight: 56
            color: theme.panelRaisedColor
            border.color: theme.borderColor
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8
                Item { Layout.fillWidth: true }
                MintButton {
                    text: qsTr("Save")
                    enabled: presetNameField.text.trim().length > 0
                    onClicked: {
                        backend.savePresetToLibrary(presetNameField.text, presetDescriptionField.text)
                        saveLibraryDialog.close()
                    }
                }
                MintButton { text: qsTr("Close"); onClicked: saveLibraryDialog.close() }
            }
        }
    }

    MintDialog {
        id: managePresetDialog
        title: qsTr("Manage custom preset")
        width: Math.min(440, Overlay.overlay ? Overlay.overlay.width - 24 : root.width - 24)

        contentItem: ColumnLayout {
            spacing: 8
            MintLabel { text: qsTr("Name") }
            MintTextField {
                id: managePresetNameField
                Layout.fillWidth: true
                placeholderText: qsTr("Preset name")
            }
            MintLabel { text: qsTr("Description") }
            MintTextField {
                id: managePresetDescriptionField
                Layout.fillWidth: true
                placeholderText: qsTr("Optional description")
            }
            MintLabel { text: qsTr("Category") }
            MintTextField {
                id: managePresetCategoryField
                Layout.fillWidth: true
                placeholderText: qsTr("Optional user category")
            }
            RowLayout {
                Layout.fillWidth: true
                MintButton {
                    text: qsTr("Duplicate")
                    onClicked: {
                        backend.duplicatePresetInLibrary(root.managePresetId, managePresetNameField.text + " Copy")
                        managePresetDialog.close()
                    }
                }
                MintButton {
                    text: qsTr("Set category")
                    onClicked: backend.setPresetCategory(root.managePresetId, managePresetCategoryField.text)
                }
                Item { Layout.fillWidth: true }
            }
        }

        footer: Rectangle {
            implicitHeight: 56
            color: theme.panelRaisedColor
            border.color: theme.borderColor
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8
                Item { Layout.fillWidth: true }
                MintButton {
                    text: qsTr("Save")
                    enabled: managePresetNameField.text.trim().length > 0
                    onClicked: {
                        var updatedId = backend.updatePresetInLibrary(
                            root.managePresetId,
                            managePresetNameField.text,
                            managePresetDescriptionField.text,
                            managePresetCategoryField.text
                        )
                        if (updatedId && updatedId.length > 0) {
                            root.managePresetId = updatedId
                            root.selectPreset(updatedId, managePresetNameField.text.trim())
                            managePresetDialog.close()
                        }
                    }
                }
                MintButton { text: qsTr("Close"); onClicked: managePresetDialog.close() }
            }
        }
    }

    FileDialog {
        id: importPresetPackDialog
        title: qsTr("Import preset pack")
        nameFilters: ["RasterMint preset pack (*.json)"]
        onAccepted: backend.importPresetPack(selectedFile.toString())
    }
    FileDialog {
        id: exportPresetPackDialog
        title: qsTr("Export preset pack")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["RasterMint preset pack (*.json)"]
        onAccepted: backend.exportPresetPack(selectedFile.toString())
    }

    FileDialog {
        id: loadPresetDialog
        title: qsTr("Load RasterMint preset")
        nameFilters: ["JSON preset (*.json)", "All files (*)"]
        onAccepted: backend.loadPreset(selectedFile.toString())
    }

    FileDialog {
        id: savePresetDialog
        title: qsTr("Save RasterMint preset")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["JSON preset (*.json)"]
        onAccepted: backend.savePreset(selectedFile.toString())
    }
}
