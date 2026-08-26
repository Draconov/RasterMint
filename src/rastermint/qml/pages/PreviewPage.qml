import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root
    contentWidth: availableWidth
    signal fitRequested()
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff
    ColumnLayout {
        width: root.availableWidth
        spacing: 12
        MintLabel { text: qsTr("Preview Render"); font.bold: true; font.pixelSize: 15 }
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            Repeater {
                model: [
                    { "value": "Quick", "label": qsTr("Quick") },
                    { "value": "Stable", "label": qsTr("Stable") },
                    { "value": "Full", "label": qsTr("Full") }
                ]
                MintButton {
                    Layout.fillWidth: true
                    text: modelData.label
                    selected: backend.previewMode === modelData.value
                    onClicked: backend.setPreviewMode(modelData.value)
                }
            }
        }
        MintLabel {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: theme.mutedTextColor
            text: backend.previewMode === "Quick" ? qsTr("Fast draft first, then a stable refinement.") : backend.previewMode === "Stable" ? qsTr("Waits briefly, then renders the refined preview.") : qsTr("Uses the selected raster when safe; very large rasters use a memory-safe full proxy.")
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
        MintButton { text: qsTr("Fit preview"); onClicked: { root.fitRequested(); backend.reportAction(qsTr("Fit preview")) } }
    }
}
