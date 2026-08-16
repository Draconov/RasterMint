import QtQuick
import QtQuick.Controls

CheckBox {
    id: control
    spacing: 8
    indicator: Rectangle {
        implicitWidth: 18
        implicitHeight: 18
        x: control.leftPadding
        y: parent.height / 2 - height / 2
        radius: 4
        color: control.checked ? theme.accentColor : theme.panelRaisedColor
        border.color: control.hovered ? theme.accentHoverColor : theme.borderColor
        Text {
            anchors.centerIn: parent
            text: control.checked ? "✓" : ""
            color: theme.accentTextColor
            font.bold: true
            font.pixelSize: 12
        }
    }
    contentItem: Text {
        text: control.text
        color: theme.textColor
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + control.spacing
        elide: Text.ElideRight
    }
}
