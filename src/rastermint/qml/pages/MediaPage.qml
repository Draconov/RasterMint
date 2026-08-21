import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    ColumnLayout {
        anchors.fill: parent
        spacing: 9
        MintLabel { text: "Media"; font.bold: true; font.pixelSize: 15 }
        MintLabel { Layout.fillWidth: true; text: backend.currentFileName || "No source"; font.bold: true; elide: Text.ElideMiddle }
        MintLabel { Layout.fillWidth: true; text: backend.sourceInfo; color: theme.mutedTextColor; wrapMode: Text.WordWrap }

        RowLayout {
            Layout.fillWidth: true
            MintButton { text: backend.playing ? "Pause" : "Play"; enabled: backend.hasSource; onClicked: backend.togglePlay() }
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
                model: ["Quick", "Rendered"]
                Component.onCompleted: currentIndex = backend.playbackMode === "Rendered" ? 1 : 0
                onActivated: backend.setPlaybackMode(currentText)
            }
            MintButton { text: "Render 5 s"; enabled: backend.hasSource; onClicked: backend.renderPreviewCache() }
        }
        MintLabel { text: backend.renderedPreviewReady ? "Rendered preview ready" : "No rendered cache"; color: backend.renderedPreviewReady ? theme.accentColor : theme.mutedTextColor }
        MintCheckBox { text: "Preserve source audio on MP4 export"; checked: backend.preserveAudio; onToggled: backend.setPreserveAudio(checked) }
        Item { Layout.fillHeight: true }
    }
}
