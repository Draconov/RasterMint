import QtQuick
import QtQuick.Controls

Slider {
    id: control

    implicitWidth: 260
    implicitHeight: 28

    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: 5
        radius: 3
        color: theme.borderColor

        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: parent.radius
            color: control.enabled ? theme.accentColor : theme.mutedTextColor
            opacity: control.enabled ? 1.0 : 0.5
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: 18
        height: 18
        radius: 9
        color: control.pressed ? theme.accentHoverColor : theme.accentColor
        border.color: theme.panelColor
        border.width: 2
        opacity: control.enabled ? 1.0 : 0.55
    }
}
