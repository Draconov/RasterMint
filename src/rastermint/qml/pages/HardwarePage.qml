import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

ScrollView {
    id: root
    property var modeValues: ["Visual", "Strict"]
    contentWidth: availableWidth
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff

    property var profileModel: []
    function customProfileRecord() {
        return {
            "id": "custom",
            "name": qsTr("Custom"),
            "category": qsTr("Custom"),
            "summary": qsTr("Current hand-edited RasterMint processing state."),
            "visualTooltip": qsTr("Custom · current hand-edited RasterMint processing state."),
            "strictTooltip": qsTr("Custom · current hand-edited RasterMint processing state.")
        }
    }

    function refreshProfiles() {
        var items = [customProfileRecord()]
        var profiles = backend.hardwareProfiles || []
        for (var i = 0; i < profiles.length; ++i)
            items.push(profiles[i])
        profileModel = items
        Qt.callLater(syncSelection)
    }

    function profileIndex(profileId) {
        var wanted = String(profileId || "custom")
        for (var i = 0; i < profileModel.length; ++i) {
            if (String(profileModel[i].id) === wanted)
                return i
        }
        return 0
    }

    function syncSelection() {
        if (!hwCombo || !modeCombo)
            return
        var settings = backend.settingsMap || {}
        hwCombo.currentIndex = profileIndex(settings.hardware_profile_id)
        modeCombo.currentIndex = String(settings.hardware_mode || "visual").toLowerCase() === "strict" ? 1 : 0
    }

    Component.onCompleted: refreshProfiles()

    Connections {
        target: backend
        function onSettingsChanged() {
            root.syncSelection()
        }
        function onHardwareProfilesChanged() {
            root.refreshProfiles()
        }
    }

    Connections {
        target: localization
        function onLanguageChanged() { root.refreshProfiles() }
    }

    ColumnLayout {
        width: root.availableWidth
        spacing: 10

        MintLabel { text: qsTr("Hardware Profile"); font.bold: true; font.pixelSize: 15 }

        MintComboBox {
            id: hwCombo
            Layout.fillWidth: true
            model: root.profileModel
            textRole: "name"

            delegate: ItemDelegate {
                required property int index
                required property var modelData
                width: hwCombo.width - 8
                height: 32
                highlighted: hwCombo.highlightedIndex === index
                hoverEnabled: true

                contentItem: Text {
                    text: parent.modelData.name
                    color: theme.textColor
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }

                background: Rectangle {
                    radius: 5
                    color: parent.highlighted || parent.hovered ? theme.selectionColor : "transparent"
                }

                ToolTip.visible: hovered && hwCombo.popup.visible
                ToolTip.delay: 250
                ToolTip.timeout: 10000
                ToolTip.text: String(modelData.id) === "custom"
                    ? modelData.visualTooltip
                    : (modeCombo.currentIndex === 1 ? modelData.strictTooltip : modelData.visualTooltip)
            }
        }

        MintLabel {
            Layout.fillWidth: true
            visible: hwCombo.currentIndex === 0
            text: qsTr("Custom means the current processing state no longer exactly matches a named hardware profile.")
            color: theme.mutedTextColor
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }

        MintLabel { text: qsTr("Mode"); color: theme.mutedTextColor }
        MintComboBox {
            id: modeCombo
            Layout.fillWidth: true
            model: [qsTr("Visual"), qsTr("Strict")]
        }

        Flow {
            Layout.fillWidth: true
            spacing: 6
            MintCheckBox { id: applyRaster; text: qsTr("Raster"); checked: true }
            MintCheckBox { id: applyPalette; text: qsTr("Palette"); checked: true }
            MintCheckBox { id: applyPar; text: "PAR"; checked: true }
            MintCheckBox { id: applyLimits; text: qsTr("Limits"); checked: true }
            MintCheckBox { id: applyDisplay; text: qsTr("Display"); checked: true }
        }

        RowLayout {
            Layout.fillWidth: true

            MintButton {
                Layout.fillWidth: true
                text: qsTr("Apply profile")
                enabled: hwCombo.currentIndex > 0 && hwCombo.currentIndex < root.profileModel.length
                onClicked: {
                    var profile = root.profileModel[hwCombo.currentIndex]
                    if (!profile || String(profile.id) === "custom")
                        return
                    backend.applyHardware(
                        String(profile.id),
                        root.modeValues[modeCombo.currentIndex],
                        {
                            "raster": applyRaster.checked,
                            "palette": applyPalette.checked,
                            "pixelAspect": applyPar.checked,
                            "limits": applyLimits.checked,
                            "display": applyDisplay.checked
                        }
                    )
                }
            }

            MintButton { text: qsTr("Load JSON…"); onClicked: hardwareFileDialog.open() }
        }
    }

    FileDialog {
        id: hardwareFileDialog
        title: qsTr("Load hardware profile")
        nameFilters: ["RasterMint hardware profile (*.json)", "JSON (*.json)"]
        onAccepted: backend.loadHardwareProfile(selectedFile.toString())
    }
}
