import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root

    modal: true
    popupType: Popup.Item
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.NoButton
    padding: 16
    closePolicy: Popup.CloseOnEscape

    background: Rectangle {
        color: theme.panelColor
        border.color: theme.borderColor
        border.width: 1
        radius: 8
    }

    Overlay.modal: Rectangle {
        color: Qt.rgba(0, 0, 0, 0.45)
    }

    header: Rectangle {
        implicitHeight: 44
        color: theme.panelRaisedColor

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: theme.borderColor
        }

        Text {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            text: root.title
            color: theme.textColor
            font.bold: true
            font.pixelSize: 14
            elide: Text.ElideRight
        }
    }
}
