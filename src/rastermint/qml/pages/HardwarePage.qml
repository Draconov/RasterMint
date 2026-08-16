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
            model: backend.hardwareProfileNames
            ToolTip.visible: hovered && currentIndex >= 0
            ToolTip.delay: 350
            ToolTip.text: currentIndex >= 0 ? (modeCombo.currentText === "Strict" ? backend.hardwareProfiles[currentIndex].strictTooltip : backend.hardwareProfiles[currentIndex].visualTooltip) : ""
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
                    backend.hardwareProfileIds[hwCombo.currentIndex],
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
        MintLabel {
            Layout.fillWidth: true
            text: "Hover the profile selector to see raster, pixel aspect, palette and strict-limit information."
            color: theme.mutedTextColor
            wrapMode: Text.WordWrap
        }
    }

    FileDialog {
        id: hardwareFileDialog
        title: "Load hardware profile"
        nameFilters: ["RasterMint hardware profile (*.json)", "JSON (*.json)"]
        onAccepted: backend.loadHardwareProfile(selectedFile.toString())
    }
}
