import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root
    contentWidth: availableWidth
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff

    ColumnLayout {
        width: root.availableWidth
        spacing: 10

        MintLabel { text: qsTr("Crop"); font.bold: true; font.pixelSize: 15 }
        MintLabel {
            text: qsTr("Drag the image handles, then Apply. Preview rendering waits until the crop is accepted.")
            color: theme.mutedTextColor
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        MintLabel { text: qsTr("Aspect"); color: theme.mutedTextColor }
        RowLayout {
            Layout.fillWidth: true
            MintComboBox {
                id: aspectCombo
                Layout.fillWidth: true
                model: ["Free", "Original", "1:1", "4:3", "3:2", "16:9", "Custom"]
                translateModel: true
                currentIndex: Math.max(0, model.indexOf(backend.cropAspectMode))
                onActivated: backend.setCropAspectMode(String(model[index]))
            }
            MintButton {
                id: swapAspectButton
                text: "↔"
                enabled: backend.cropAspectMode !== "Free"
                onClicked: backend.toggleCropAspectOrientation()
                MintToolTip { visible: swapAspectButton.hovered; text: qsTr("Swap aspect orientation") }
            }
        }

        GridLayout {
            visible: backend.cropAspectMode === "Custom"
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 4
            MintLabel { text: qsTr("Ratio Width"); color: theme.mutedTextColor }
            MintLabel { text: qsTr("Ratio Height"); color: theme.mutedTextColor }
            MintSpinBox {
                Layout.fillWidth: true; from: 1; to: 999
                value: backend.cropCustomRatioWidth
                onValueModified: backend.setCropCustomRatio(value, backend.cropCustomRatioHeight)
            }
            MintSpinBox {
                Layout.fillWidth: true; from: 1; to: 999
                value: backend.cropCustomRatioHeight
                onValueModified: backend.setCropCustomRatio(backend.cropCustomRatioWidth, value)
            }
        }

        MintLabel { text: qsTr("Crop rectangle (pixels)"); color: theme.mutedTextColor }
        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 4
            MintLabel { text: "X"; color: theme.mutedTextColor }
            MintLabel { text: "Y"; color: theme.mutedTextColor }
            MintSpinBox {
                Layout.fillWidth: true; from: 0; to: Math.max(0, backend.cropDisplayWidth - 1)
                value: backend.cropDraftX
                onValueModified: backend.setCropDraftPixelValue("x", value)
            }
            MintSpinBox {
                Layout.fillWidth: true; from: 0; to: Math.max(0, backend.cropDisplayHeight - 1)
                value: backend.cropDraftY
                onValueModified: backend.setCropDraftPixelValue("y", value)
            }
            MintLabel { text: qsTr("Width"); color: theme.mutedTextColor }
            MintLabel { text: qsTr("Height"); color: theme.mutedTextColor }
            MintSpinBox {
                Layout.fillWidth: true; from: 1; to: Math.max(1, backend.cropDisplayWidth - backend.cropDraftX)
                value: backend.cropDraftWidth
                onValueModified: backend.setCropDraftPixelValue("width", value)
            }
            MintSpinBox {
                Layout.fillWidth: true; from: 1; to: Math.max(1, backend.cropDisplayHeight - backend.cropDraftY)
                value: backend.cropDraftHeight
                onValueModified: backend.setCropDraftPixelValue("height", value)
            }
        }

        MintLabel { text: qsTr("Overlay"); color: theme.mutedTextColor }
        MintComboBox {
            Layout.fillWidth: true
            model: ["None", "Rule of Thirds", "Grid", "Center"]
            translateModel: true
            currentIndex: Math.max(0, model.indexOf(backend.cropOverlay))
            onActivated: backend.setCropOverlay(String(model[index]))
        }

        MintButton {
            Layout.fillWidth: true
            text: qsTr("Reset to Full Image")
            onClicked: backend.resetCropDraft()
        }

        Item { Layout.preferredHeight: 4 }
        RowLayout {
            Layout.fillWidth: true
            MintButton { Layout.fillWidth: true; text: qsTr("Cancel"); onClicked: backend.cancelCropEdit() }
            MintButton { Layout.fillWidth: true; text: qsTr("Apply"); selected: true; onClicked: backend.applyCropEdit() }
        }

        MintLabel {
            text: qsTr("Enter applies · Esc cancels · Double-click inside the crop applies")
            color: theme.mutedTextColor
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Item { Layout.fillHeight: true }
    }
}
