import QtQuick
import QtQuick.Controls

Button {
    id: control

    property bool menuOpen: false

    implicitHeight: 34
    implicitWidth: Math.max(48, contentItem.implicitWidth + leftPadding + rightPadding)
    leftPadding: 12
    rightPadding: 12
    topPadding: 0
    bottomPadding: 0
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus

    contentItem: Text {
        text: control.text
        color: control.menuOpen ? theme.accentColor : theme.textColor
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignHCenter
        font.pixelSize: 13
    }

    background: Rectangle {
        radius: 4
        color: control.menuOpen
               ? Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.22)
               : (control.hovered || control.down ? theme.selectionColor : "transparent")
        border.color: control.menuOpen || control.visualFocus
                      ? theme.accentColor
                      : "transparent"
        border.width: control.menuOpen || control.visualFocus ? 1 : 0

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 2
            visible: control.menuOpen
            color: theme.accentColor
        }

        Behavior on color { ColorAnimation { duration: 70 } }
        Behavior on border.color { ColorAnimation { duration: 70 } }
    }
}
