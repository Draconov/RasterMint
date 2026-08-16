import QtQuick
import QtQuick.Controls

Button {
    id: control
    property bool selected: false
    implicitWidth: 104
    implicitHeight: 36
    flat: true
    contentItem: Text {
        text: control.text
        color: control.selected ? theme.textColor : theme.mutedTextColor
        font.pixelSize: 12
        font.bold: control.selected
        horizontalAlignment: Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
        leftPadding: 12
    }
    background: Rectangle {
        radius: 6
        color: control.selected ? theme.selectionColor : (control.hovered ? theme.panelHoverColor : "transparent")
        Rectangle {
            visible: control.selected
            width: 3
            radius: 2
            color: theme.accentColor
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom; margins: 5 }
        }
        Behavior on color { ColorAnimation { duration: 90 } }
    }
}
