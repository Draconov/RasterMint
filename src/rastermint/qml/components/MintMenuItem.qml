import QtQuick
import QtQuick.Controls

MenuItem {
    id: control

    implicitHeight: 32
    implicitWidth: Math.max(220, implicitContentWidth + leftPadding + rightPadding + 12)
    leftPadding: 12
    rightPadding: 10
    spacing: 6

    // Keep Qt Quick Controls' own MenuItem indicator so the checkmark remains
    // style-native and follows the active RasterMint theme through the palette.
    // Reposition/scale that Qt-owned indicator into the small gutter at the
    // far left so checkable actions keep the same text alignment as every
    // other menu action instead of jumping noticeably to the right.
    palette.windowText: control.enabled ? theme.accentColor : theme.mutedTextColor

    Binding {
        target: control.indicator
        property: "x"
        value: 1
        when: control.indicator !== null
    }

    Binding {
        target: control.indicator
        property: "width"
        value: 10
        when: control.indicator !== null
    }

    Binding {
        target: control.indicator
        property: "height"
        value: 10
        when: control.indicator !== null
    }

    // Action.shortcut is a keysequence. A disabled Shortcut is used only as a
    // formatter so the label follows the platform's native key naming without
    // registering a second active shortcut.
    Shortcut {
        id: shortcutFormatter
        enabled: false
        sequence: control.action ? control.action.shortcut : ""
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
            color: theme.mutedTextColor
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
