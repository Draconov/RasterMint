import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    property var playbackModeValues: ["Quick", "Rendered"]

    ColumnLayout {
        anchors.fill: parent
        spacing: 9
        MintLabel { text: qsTr("Media"); font.bold: true; font.pixelSize: 15 }
        MintLabel { Layout.fillWidth: true; text: backend.currentFileName || qsTr("No source"); font.bold: true; elide: Text.ElideMiddle }
        MintLabel { Layout.fillWidth: true; text: backend.sourceInfo; color: theme.mutedTextColor; wrapMode: Text.WordWrap }

        RowLayout {
            Layout.fillWidth: true
            MintButton { text: backend.playing ? qsTr("Pause") : qsTr("Play"); enabled: backend.hasSource; onClicked: backend.togglePlay() }
            MintComboBox {
                Layout.fillWidth: true
                model: ["0.5×", "1×", "1.5×", "2×"]
                currentIndex: 1
                onActivated: backend.setPlaybackSpeed([0.5, 1, 1.5, 2][currentIndex])
            }
        }
        MintSlider { Layout.fillWidth: true; from: 0; to: backend.timelineDuration; value: backend.currentTime; onUserMoved: function(newValue) { backend.setCurrentTime(newValue) } }

        RowLayout {
            Layout.fillWidth: true
            MintComboBox {
                id: mode
                Layout.fillWidth: true
                model: [qsTr("Quick"), qsTr("Rendered")]
                Component.onCompleted: currentIndex = backend.playbackMode === "Rendered" ? 1 : 0
                onActivated: backend.setPlaybackMode(root.playbackModeValues[currentIndex])
            }
            MintButton { text: qsTr("Render 5 s"); enabled: backend.hasSource; onClicked: backend.renderPreviewCache() }
        }
        MintLabel { text: backend.renderedPreviewReady ? qsTr("Rendered preview ready") : qsTr("No rendered cache"); color: backend.renderedPreviewReady ? theme.accentColor : theme.mutedTextColor }
        MintCheckBox { text: qsTr("Preserve source audio on MP4 export"); checked: backend.preserveAudio; onToggled: backend.setPreserveAudio(checked) }
        Item { Layout.fillHeight: true }
    }
}
