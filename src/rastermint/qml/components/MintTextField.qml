import QtQuick
import QtQuick.Controls

TextField {
    id: control
    implicitHeight: 34
    color: control.enabled ? theme.textColor : theme.mutedTextColor
    placeholderTextColor: theme.mutedTextColor
    selectionColor: theme.selectionColor
    selectedTextColor: theme.textColor
    background: Rectangle {
        radius: 6
        color: control.enabled ? theme.panelRaisedColor : theme.panelColor
        border.color: control.activeFocus ? theme.accentColor : theme.borderColor
        border.width: control.activeFocus ? 2 : 1
    }
}
