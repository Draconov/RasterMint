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
        MintLabel { text: qsTr("Creative Randomize"); font.bold: true; font.pixelSize: 15 }
        MintLabel { text: qsTr("Locked categories stay unchanged."); color: theme.mutedTextColor }
        Repeater {
            model: [
                {key:"palette", label:"Palette"}, {key:"dither", label:"Dither"},
                {key:"effects", label:"Effects"}, {key:"resolution", label:"Raster"},
                {key:"parameters", label:"Parameters"}
            ]
            MintCheckBox {
                text: qsTr("Lock ") + qsTr(modelData.label)
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
            MintButton { Layout.fillWidth: true; text: qsTr("Randomize"); onClicked: backend.randomizeUnlocked() }
            MintButton { text: "→"; onClicked: backend.randomHistory(1) }
        }
    }
}
