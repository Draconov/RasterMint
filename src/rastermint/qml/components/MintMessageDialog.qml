import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

MintDialog {
    id: root

    property string text: ""

    width: Math.min(520, Overlay.overlay ? Overlay.overlay.width - 32 : 520)

    contentItem: ColumnLayout {
        spacing: 12

        Text {
            Layout.fillWidth: true
            text: root.text
            color: theme.textColor
            font.pixelSize: 13
            wrapMode: Text.Wrap
            textFormat: Text.PlainText
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
                text: qsTr("Close")
                onClicked: root.close()
            }
        }
    }
}
