import QtQuick
import QtQuick.Controls

ScrollBar {
    id: control
    // Overlay indicator: no track, border or padding. The control occupies
    // only the final pixels of its scroll viewport.
    implicitWidth: 5
    implicitHeight: 5
    minimumSize: 0.12
    padding: 0
    hoverEnabled: true
    opacity: control.enabled && control.size < 1.0 &&
             (control.active || control.hovered || control.pressed) ? 1.0 : 0.0
    Behavior on opacity { NumberAnimation { duration: 120 } }
    contentItem: Rectangle {
        implicitWidth: 5
        implicitHeight: 5
        radius: 2.5
        color: control.pressed || control.hovered ? theme.accentHoverColor : theme.accentColor
    }
    background: Item { }
}
