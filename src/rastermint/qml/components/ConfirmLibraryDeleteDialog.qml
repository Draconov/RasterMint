import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

MintDialog {
    id: root
    property string itemName: ""
    property string detailText: ""
    signal confirmed()

    title: qsTr("Remove %1").arg(itemName)
    width: Math.min(440, Overlay.overlay ? Overlay.overlay.width - 32 : 440)
    onOpened: cancelButton.forceActiveFocus()

    contentItem: ColumnLayout {
        spacing: 10
        MintLabel {
            Layout.fillWidth: true
            text: qsTr("Remove %1 from library?").arg(root.itemName)
            wrapMode: Text.WordWrap
        }
        MintLabel {
            Layout.fillWidth: true
            text: root.detailText.length > 0 ? root.detailText : qsTr("This cannot be undone.")
            color: theme.mutedTextColor
            wrapMode: Text.WordWrap
        }
    }

    footer: Rectangle {
        implicitHeight: 56
        color: theme.panelRaisedColor
        border.color: theme.borderColor
        border.width: 1
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 8
            Item { Layout.fillWidth: true }
            MintButton {
                id: cancelButton
                text: qsTr("Cancel")
                selected: true
                onClicked: root.close()
            }
            MintButton {
                text: qsTr("Remove")
                onClicked: {
                    root.confirmed()
                    root.close()
                }
            }
        }
    }
}
