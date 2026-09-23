import QtQuick
import QtQuick.Controls

ScrollBar {
    id: control
    implicitWidth: 9
    implicitHeight: 9
    padding: 2
    contentItem: Rectangle {
        implicitWidth: 5
        implicitHeight: 5
        radius: 3
        color: control.pressed ? theme.accentColor
             : (control.hovered ? theme.accentHoverColor : theme.mutedTextColor)
        opacity: control.enabled && control.size < 1.0 ? 0.85 : 0.0
    }
    background: Rectangle {
        radius: 4
        color: theme.panelRaisedColor
        opacity: control.enabled && control.size < 1.0 ? 0.55 : 0.0
    }
}
