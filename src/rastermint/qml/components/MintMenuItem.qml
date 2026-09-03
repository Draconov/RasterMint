import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

MenuItem {
    id: control

    implicitHeight: 32
    implicitWidth: Math.max(220, implicitContentWidth + leftPadding + rightPadding + 24)
    leftPadding: 12
    rightPadding: 12
    topPadding: 0
    bottomPadding: 0

    // This Shortcut is only a formatter for the menu's visible hotkey label.
    // Action already owns the real shortcut, so keep this helper disabled.
    Shortcut {
        id: shortcutDisplay
        enabled: false
        sequences: control.action && control.action.shortcut ? [control.action.shortcut] : []
    }

    contentItem: RowLayout {
        spacing: 16

        Text {
            Layout.fillWidth: true
            text: control.text
            color: control.enabled ? theme.textColor : theme.mutedTextColor
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        Text {
            visible: backend.showHotkeys && shortcutDisplay.nativeText.length > 0
            text: shortcutDisplay.nativeText
            color: theme.mutedTextColor
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignRight
            font.pixelSize: 11
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
