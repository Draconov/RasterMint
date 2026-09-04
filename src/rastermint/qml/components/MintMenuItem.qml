import QtQuick
import QtQuick.Controls

MenuItem {
    id: control

    readonly property color safeTextColor: theme ? theme.textColor : "#f3f7ff"
    readonly property color safeMutedTextColor: theme ? theme.mutedTextColor : "#a0a7b4"
    readonly property color safeSelectionColor: theme ? theme.selectionColor : "#3a4f6e"
    readonly property color safeAccentColor: theme ? theme.accentColor : "#b8ff3b"

    implicitHeight: 32
    implicitWidth: Math.max(220, implicitContentWidth + leftPadding + rightPadding + 12)
    leftPadding: 12
    rightPadding: 10
    spacing: 6

    // RasterMint handles checked-state visuals itself.
    // Do not show the native Qt menu indicator/checkmark.
    indicator: null

    Shortcut {
        id: shortcutFormatter
        enabled: false
        sequences: control.action && control.action.shortcut ? [control.action.shortcut] : []
    }

    contentItem: Item {
        id: content
        implicitWidth: label.implicitWidth
                       + (shortcutLabel.visible ? shortcutLabel.implicitWidth + 18 : 0)
        implicitHeight: 32

        Text {
            id: label
            anchors.left: parent.left
            anchors.right: shortcutLabel.visible ? shortcutLabel.left : parent.right
            anchors.rightMargin: shortcutLabel.visible ? 18 : 0
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            text: control.text
            color: control.enabled ? control.safeTextColor : control.safeMutedTextColor
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
            color: control.safeMutedTextColor
            font.pixelSize: 11
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignRight
        }
    }

    background: Rectangle {
        implicitWidth: 220
        implicitHeight: 32
        radius: 5
        color: control.enabled && (control.highlighted || control.hovered)
               ? control.safeSelectionColor
               : (control.checkable && control.checked
                  ? Qt.rgba(control.safeAccentColor.r, control.safeAccentColor.g, control.safeAccentColor.b, 0.14)
                  : "transparent")
        border.color: control.checkable && control.checked
                      ? Qt.rgba(control.safeAccentColor.r, control.safeAccentColor.g, control.safeAccentColor.b, 0.42)
                      : "transparent"
        border.width: control.checkable && control.checked ? 1 : 0
        Behavior on color { ColorAnimation { duration: 70 } }
        Behavior on border.color { ColorAnimation { duration: 70 } }

        Rectangle {
            anchors.left: parent.left
            anchors.leftMargin: 3
            anchors.verticalCenter: parent.verticalCenter
            width: 3
            height: 18
            radius: 2
            visible: control.checkable && control.checked
            color: control.safeAccentColor
        }
    }
}
