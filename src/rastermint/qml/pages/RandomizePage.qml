import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff
    ColumnLayout {
        width: parent.width
        spacing: 10
        MintLabel { text: "Creative Randomize"; font.bold: true; font.pixelSize: 15 }
        MintLabel { text: "Locked categories stay unchanged."; color: theme.mutedTextColor }
        Repeater {
            model: [
                {key:"palette", label:"Palette"}, {key:"dither", label:"Dither"},
                {key:"effects", label:"Effects"}, {key:"resolution", label:"Raster"},
                {key:"parameters", label:"Parameters"}
            ]
            MintCheckBox {
                text: "Lock " + modelData.label
                checked: Boolean((backend.settingsMap.random_locks || {})[modelData.key])
                onToggled: {
                    var locks = backend.settingsMap.random_locks
                    locks[modelData.key] = checked
                    backend.setSetting("random_locks", locks)
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            MintButton { text: "←"; onClicked: backend.randomHistory(-1) }
            MintButton { Layout.fillWidth: true; text: "Randomize"; onClicked: backend.randomizeUnlocked() }
            MintButton { text: "→"; onClicked: backend.randomHistory(1) }
        }
    }
}
