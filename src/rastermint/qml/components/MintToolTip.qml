import QtQuick
import QtQuick.Controls

ToolTip {
    id: control

    delay: 350
    timeout: 10000
    margins: 8
    leftPadding: 10
    rightPadding: 10
    topPadding: 6
    bottomPadding: 6
    closePolicy: Popup.NoAutoClose

    implicitWidth: Math.ceil(contentItem.implicitWidth) + leftPadding + rightPadding
    implicitHeight: Math.ceil(contentItem.implicitHeight) + topPadding + bottomPadding

    contentItem: Text {
        text: control.text
        color: theme.textColor
        font.pixelSize: 11
        wrapMode: Text.NoWrap
        maximumLineCount: 6
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 6
        color: theme.panelColor
        border.width: 1
        border.color: theme.accentColor
        opacity: 0.98
    }
}
