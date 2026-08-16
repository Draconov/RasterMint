import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff
    ColumnLayout {
        width: parent.width
        spacing: 9
        MintLabel { text: "Source Framing"; font.bold: true; font.pixelSize: 15 }
        MintLabel { text: "Crop (%)"; color: theme.mutedTextColor }
        GridLayout {
            Layout.fillWidth: true; columns: 2; columnSpacing: 8; rowSpacing: 8
            Repeater {
                model: [
                    {key:"crop_left", label:"Left"}, {key:"crop_right", label:"Right"},
                    {key:"crop_top", label:"Top"}, {key:"crop_bottom", label:"Bottom"}
                ]
                ColumnLayout {
                    Layout.fillWidth: true
                    MintLabel { text: modelData.label; color: theme.mutedTextColor }
                    Slider {
                        Layout.fillWidth: true; from: 0; to: 0.49; stepSize: 0.01; value: backend.settingsMap[modelData.key]
                        onMoved: backend.setSetting(modelData.key, value)
                    }
                }
            }
        }
        MintLabel { text: "Fill position"; color: theme.mutedTextColor }
        ColumnLayout {
            Layout.fillWidth: true
            MintLabel { text: "Horizontal"; color: theme.mutedTextColor }
            Slider { Layout.fillWidth: true; from: -1; to: 1; stepSize: 0.01; value: backend.settingsMap.position_x; onMoved: backend.setSetting("position_x", value) }
            MintLabel { text: "Vertical"; color: theme.mutedTextColor }
            Slider { Layout.fillWidth: true; from: -1; to: 1; stepSize: 0.01; value: backend.settingsMap.position_y; onMoved: backend.setSetting("position_y", value) }
        }
        MintLabel { Layout.fillWidth: true; color: theme.mutedTextColor; wrapMode: Text.WordWrap; text: "Flip, mirror and rotation tools are in Edit. Mirror tools expose movable blue axes directly on the preview." }
    }
}
