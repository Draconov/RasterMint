import QtQuick
import QtQuick.Controls

Button {
    id: control

    property bool menuOpen: false

    implicitHeight: 34
    implicitWidth: Math.max(48, contentItem.implicitWidth + leftPadding + rightPadding)
    leftPadding: 12
    rightPadding: 12
    topPadding: 0
    bottomPadding: 0
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus

    contentItem: Text {
        text: control.text
        color: theme.textColor
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignHCenter
        font.pixelSize: 13
    }

    background: Rectangle {
        radius: 4
        // Keep the clicked/open menu visually active, but do not use focus as
        // an active-state signal. Main.qml clears focus when the popup closes.
        color: control.menuOpen || control.down
               ? theme.selectionColor
               : (control.hovered ? theme.panelHoverColor : "transparent")
        border.color: control.visualFocus ? theme.accentColor : "transparent"
        border.width: control.visualFocus ? 1 : 0
        Behavior on color { ColorAnimation { duration: 70 } }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 2
            visible: control.menuOpen
            color: theme.accentColor
        }
    }
}
