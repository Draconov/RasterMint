import QtQuick
import QtQuick.Controls

TextField {
    id: control
    implicitHeight: 34
    color: theme.textColor
    placeholderTextColor: theme.mutedTextColor
    selectionColor: theme.selectionColor
    selectedTextColor: theme.textColor
    background: Rectangle {
        radius: 6
        color: theme.panelRaisedColor
        border.color: control.activeFocus ? theme.accentColor : theme.borderColor
        border.width: control.activeFocus ? 2 : 1
    }
}
