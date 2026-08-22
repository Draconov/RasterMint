import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

ScrollView {
    id: root
    contentWidth: availableWidth
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff

    ColumnLayout {
        width: root.availableWidth
        spacing: 10

        MintLabel { text: "Hardware Profile"; font.bold: true; font.pixelSize: 15 }
        MintComboBox {
            id: hwCombo
            Layout.fillWidth: true
            model: backend.hardwareProfiles
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
                ToolTip.text: modeCombo.currentText === "Strict"
                    ? modelData.strictTooltip
                    : modelData.visualTooltip
            }
        }
        MintLabel { text: "Mode"; color: theme.mutedTextColor }
        MintComboBox { id: modeCombo; Layout.fillWidth: true; model: ["Visual", "Strict"] }

        Flow {
            Layout.fillWidth: true
            spacing: 6
            MintCheckBox { id: applyRaster; text: "Raster"; checked: true }
            MintCheckBox { id: applyPalette; text: "Palette"; checked: true }
            MintCheckBox { id: applyPar; text: "PAR"; checked: true }
            MintCheckBox { id: applyLimits; text: "Limits"; checked: true }
            MintCheckBox { id: applyDisplay; text: "Display"; checked: true }
        }

        RowLayout {
            Layout.fillWidth: true
            MintButton {
                Layout.fillWidth: true
                text: "Apply profile"
                enabled: hwCombo.currentIndex >= 0
                onClicked: backend.applyHardware(
                    backend.hardwareProfiles[hwCombo.currentIndex].id,
                    modeCombo.currentText,
                    {
                        "raster": applyRaster.checked,
                        "palette": applyPalette.checked,
                        "pixelAspect": applyPar.checked,
                        "limits": applyLimits.checked,
                        "display": applyDisplay.checked
                    }
                )
            }
            MintButton { text: "Load JSON…"; onClicked: hardwareFileDialog.open() }
        }
    }

    FileDialog {
        id: hardwareFileDialog
        title: "Load hardware profile"
        nameFilters: ["RasterMint hardware profile (*.json)", "JSON (*.json)"]
        onAccepted: backend.loadHardwareProfile(selectedFile.toString())
    }
}
