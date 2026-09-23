import QtQuick
import QtQuick.Controls

ScrollBar {
    id: control
    implicitWidth: 10
    implicitHeight: 10
    minimumSize: 0.12
    padding: 1
    contentItem: Rectangle {
        implicitWidth: 8
        implicitHeight: 8
        radius: 4
        // The idle thumb is also theme-accented, not generic muted grey.
        color: control.hovered || control.pressed ? theme.accentHoverColor : theme.accentColor
        opacity: control.enabled && control.size < 1.0
                 ? (control.hovered || control.pressed ? 1.0 : 0.8) : 0.0
    }
    background: Rectangle {
        radius: 4
        color: theme.panelRaisedColor
        opacity: control.enabled && control.size < 1.0 ? 0.55 : 0.0
    }
}
