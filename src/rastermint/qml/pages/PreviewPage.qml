import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root
    signal fitRequested()
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff
    ColumnLayout {
        width: parent.width
        spacing: 12
        MintLabel { text: "Preview Render"; font.bold: true; font.pixelSize: 15 }
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            Repeater {
                model: ["Quick", "Stable", "Full"]
                MintButton {
                    Layout.fillWidth: true
                    text: modelData
                    selected: backend.previewMode === modelData
                    onClicked: backend.setPreviewMode(modelData)
                }
            }
        }
        MintLabel {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: theme.mutedTextColor
            text: backend.previewMode === "Quick" ? "Fast draft first, then a stable refinement." : backend.previewMode === "Stable" ? "Waits briefly, then renders the refined preview." : "Uses the selected raster when safe; very large rasters use a memory-safe full proxy."
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
        MintButton { text: "Fit preview"; onClicked: root.fitRequested() }
    }
}
