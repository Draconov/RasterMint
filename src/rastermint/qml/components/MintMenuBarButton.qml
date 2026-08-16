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
        color: theme.textColor
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignHCenter
        font.pixelSize: 13
    }

    background: Rectangle {
        radius: 4
        color: control.menuOpen || control.hovered || control.down
               ? theme.selectionColor
               : "transparent"
        border.color: control.visualFocus ? theme.accentColor : "transparent"
        border.width: control.visualFocus ? 1 : 0
        Behavior on color { ColorAnimation { duration: 70 } }
    }
}
