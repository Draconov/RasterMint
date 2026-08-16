import QtQuick
import QtQuick.Controls

Button {
    id: control
    implicitHeight: 34
    leftPadding: 12
    rightPadding: 12
    font.pixelSize: 13
    palette.buttonText: theme.textColor
    contentItem: Text {
        text: control.text
        color: control.enabled ? theme.textColor : theme.mutedTextColor
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 6
        color: control.down ? theme.selectionColor : (control.hovered ? theme.panelHoverColor : theme.panelRaisedColor)
        border.color: control.activeFocus ? theme.accentColor : theme.borderColor
        border.width: control.activeFocus ? 2 : 1
        Behavior on color { ColorAnimation { duration: 90 } }
    }
}
