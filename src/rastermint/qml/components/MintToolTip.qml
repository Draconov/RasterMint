import QtQuick
import QtQuick.Controls

ToolTip {
    id: control

    delay: 350
    timeout: 10000
    padding: 8
    leftPadding: 9
    rightPadding: 9

    implicitWidth: Math.min(420, Math.max(80, tooltipText.implicitWidth + leftPadding + rightPadding))
    implicitHeight: tooltipText.implicitHeight + topPadding + bottomPadding

    contentItem: Text {
        id: tooltipText
        text: control.text
        color: theme.textColor
        font.pixelSize: 12
        wrapMode: Text.WordWrap
        width: Math.min(390, implicitWidth)
    }

    background: Rectangle {
        color: theme.panelRaisedColor
        border.color: theme.borderColor
        border.width: 1
        radius: 5
    }
}
