import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root
    signal cropRequested()
    contentWidth: availableWidth
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff
    ColumnLayout {
        width: root.availableWidth
        spacing: 9
        MintLabel { text: qsTr("Source Framing"); font.bold: true; font.pixelSize: 15 }
        MintLabel { text: qsTr("Crop"); color: theme.mutedTextColor }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: cropSummary.implicitHeight + 18
            radius: 6
            color: theme.panelRaisedColor
            border.color: theme.borderColor
            MintLabel {
                id: cropSummary
                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 9 }
                color: theme.textColor
                wrapMode: Text.WordWrap
                readonly property var rect: backend.appliedCropPixels
                readonly property bool fullImage: Math.abs(Number(backend.settingsMap.crop_x)) < 0.000001
                                                    && Math.abs(Number(backend.settingsMap.crop_y)) < 0.000001
                                                    && Math.abs(Number(backend.settingsMap.crop_width) - 1) < 0.000001
                                                    && Math.abs(Number(backend.settingsMap.crop_height) - 1) < 0.000001
                text: fullImage
                      ? qsTr("Full image · %1 × %2").arg(backend.sourceWidth).arg(backend.sourceHeight)
                      : qsTr("%1 × %2 px · X %3 · Y %4").arg(rect.width).arg(rect.height).arg(rect.x).arg(rect.y)
            }
        }
        RowLayout {
            Layout.fillWidth: true
            MintButton { Layout.fillWidth: true; text: qsTr("Edit Crop…"); enabled: backend.hasSource; onClicked: root.cropRequested() }
            MintButton {
                Layout.fillWidth: true
                text: qsTr("Reset")
                enabled: backend.hasSource && !(Math.abs(Number(backend.settingsMap.crop_x)) < 0.000001
                                               && Math.abs(Number(backend.settingsMap.crop_y)) < 0.000001
                                               && Math.abs(Number(backend.settingsMap.crop_width) - 1) < 0.000001
                                               && Math.abs(Number(backend.settingsMap.crop_height) - 1) < 0.000001)
                onClicked: backend.resetCrop()
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
