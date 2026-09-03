import QtQuick
import QtQuick.Controls

ToolTip {
    id: control

    readonly property color safeTextColor: theme ? theme.textColor : "#f3f7ff"
    readonly property color safePanelColor: theme ? theme.panelColor : "#2b2b2b"
    readonly property color safeAccentColor: theme ? theme.accentColor : "#4da3ff"

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
        color: control.safeTextColor
        font.pixelSize: 11
        wrapMode: Text.NoWrap
        maximumLineCount: 6
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 6
        color: control.safePanelColor
        border.width: 1
        border.color: control.safeAccentColor
        opacity: 0.98
    }
}
