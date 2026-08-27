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
        spacing: 9
        MintLabel { text: qsTr("Source Framing"); font.bold: true; font.pixelSize: 15 }
        MintLabel { text: qsTr("Crop (%)"); color: theme.mutedTextColor }
        GridLayout {
            Layout.fillWidth: true; columns: 2; columnSpacing: 8; rowSpacing: 8
            Repeater {
                model: [
                    {key:"crop_left", label:"Left"}, {key:"crop_right", label:"Right"},
                    {key:"crop_top", label:"Top"}, {key:"crop_bottom", label:"Bottom"}
                ]
                ColumnLayout {
                    Layout.fillWidth: true
                    MintLabel { text: localization.translateRuntime(localization.effectiveLanguageId, String(modelData.label)); color: theme.mutedTextColor }
                    MintSlider {
                        Layout.fillWidth: true; from: 0; to: 0.49; stepSize: 0.01; value: backend.settingsMap[modelData.key]
                        onInteractionActiveChanged: {
                            if (interactionActive) backend.beginHistoryGroup(qsTr("Crop %1").arg(localization.translateRuntime(localization.effectiveLanguageId, String(modelData.label)).toLowerCase()))
                            else backend.endHistoryGroup()
                        }
                        onUserMoved: function(newValue) { backend.setSetting(modelData.key, newValue) }
                    }
                }
            }
        }
        MintLabel { text: qsTr("Fill position"); color: theme.mutedTextColor }
        ColumnLayout {
            Layout.fillWidth: true
            MintLabel { text: qsTr("Horizontal"); color: theme.mutedTextColor }
            MintSlider {
                Layout.fillWidth: true; from: -1; to: 1; stepSize: 0.01; value: backend.settingsMap.position_x
                onInteractionActiveChanged: { if (interactionActive) backend.beginHistoryGroup(qsTr("Fill position X")); else backend.endHistoryGroup() }
                onUserMoved: function(newValue) { backend.setSetting("position_x", newValue) }
            }
            MintLabel { text: qsTr("Vertical"); color: theme.mutedTextColor }
            MintSlider {
                Layout.fillWidth: true; from: -1; to: 1; stepSize: 0.01; value: backend.settingsMap.position_y
                onInteractionActiveChanged: { if (interactionActive) backend.beginHistoryGroup(qsTr("Fill position Y")); else backend.endHistoryGroup() }
                onUserMoved: function(newValue) { backend.setSetting("position_y", newValue) }
            }
        }
        MintLabel { Layout.fillWidth: true; color: theme.mutedTextColor; wrapMode: Text.WordWrap; text: qsTr("Flip, mirror and rotation tools are in Edit. Mirror tools expose movable blue axes directly on the preview.") }
    }
}
