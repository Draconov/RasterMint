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
                "nes", "snes", "master-system", "mega-drive", "playstation",
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
                "apple-ii-hgr", "zx-spectrum", "cga-neon", "ega-crisp",
                "amstrad-cpc", "msx", "ti994a", "mac-classic", "mac-gray",
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
                "crt-ntsc", "crt-pal", "monochrome-lcd",
                "green-crt", "amber-monitor", "white-phosphor"
            ]
        },
        {
            "name": "Stylized & Print",
            "ids": ["halftone-print", "vector", "accurate-1to1", "isolated-dither-glow"]
        },
        {
            "name": "Fantasy Consoles",
            "ids": ["pico-8", "tic-80"]
        }
    ]

    function allPresetItems() {
        return backend.allPresets ? backend.allPresets : []
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
        for (var i = 0; i < presetCategories.length; ++i) {
            var ids = presetCategories[i].ids
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
            // Clean, custom/user presets, and any future preset without an
            // assigned category remain directly accessible above the groups.
            if (Boolean(preset.user) || !grouped[String(preset.id)])
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
            border.color: theme.borderColor

            property bool isUserPreset: Boolean(modelData.user)
            property string descriptionText: modelData.description ? String(modelData.description) : ""
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
                    text: modelData.name + (presetCard.isUserPreset ? " · " + qsTr("custom") : "")
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
                    model: root.presetCategories

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
                                    text: qsTr(categorySection.categoryData.name)
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

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 2
                }
            }
        }
    }

    Dialog {
        id: saveLibraryDialog
        title: qsTr("Save preset to library")
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
