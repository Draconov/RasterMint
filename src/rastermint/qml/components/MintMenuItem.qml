import QtQuick
import QtQuick.Controls

MenuItem {
    id: control

    implicitHeight: 32
    implicitWidth: Math.max(220, implicitContentWidth + leftPadding + rightPadding + 12)
    leftPadding: 10
    rightPadding: 10

    // Action.shortcut is a keysequence. A disabled Shortcut is used only as a
    // formatter so the label follows the platform's native key naming without
    // registering a second active shortcut.
    Shortcut {
        id: shortcutFormatter
        enabled: false
        sequence: control.action ? control.action.shortcut : ""
    }

    contentItem: Item {
        implicitWidth: checkSlot.width + label.implicitWidth
                       + (shortcutLabel.visible ? shortcutLabel.implicitWidth + 18 : 0)
        implicitHeight: 32

        Text {
            id: checkSlot
            width: 18
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            text: control.checkable && control.checked ? "✓" : ""
            color: control.enabled ? theme.accentColor : theme.mutedTextColor
            font.bold: true
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignLeft
        }

        Text {
            id: label
            anchors.left: checkSlot.right
            anchors.right: shortcutLabel.visible ? shortcutLabel.left : parent.right
            anchors.rightMargin: shortcutLabel.visible ? 18 : 0
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            text: control.text
            color: control.enabled ? theme.textColor : theme.mutedTextColor
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        Text {
            id: shortcutLabel
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            visible: backend.showHotkeys && text.length > 0
            text: shortcutFormatter.nativeText
            color: control.enabled ? theme.mutedTextColor : theme.mutedTextColor
            font.pixelSize: 11
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignRight
        }
    }

    background: Rectangle {
        implicitWidth: 220
        implicitHeight: 32
        radius: 5
        color: control.highlighted || control.hovered ? theme.selectionColor : "transparent"
        Behavior on color { ColorAnimation { duration: 70 } }
    }
}
