import QtQuick
import QtQuick.Controls

MenuItem {
    id: control

    implicitHeight: 32
    implicitWidth: Math.max(220, implicitContentWidth + leftPadding + rightPadding + 24)
    leftPadding: 12
    rightPadding: 20

    contentItem: Text {
        text: control.text
        color: control.enabled ? theme.textColor : theme.mutedTextColor
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        implicitWidth: 220
        implicitHeight: 32
        radius: 5
        color: control.highlighted || control.hovered ? theme.selectionColor : "transparent"
        Behavior on color { ColorAnimation { duration: 70 } }
    }
}
