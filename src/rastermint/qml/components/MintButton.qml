import QtQuick
import QtQuick.Controls

Button {
    id: control
    property bool selected: false
    // Icon-only controls should have the same width and height. A text label
    // (including "+ Add colour") retains the ordinary text-button sizing.
    readonly property bool iconOnly: ["+", "−", "-", "×", "✕", "↑", "↓", "←", "→", "‹", "›", "▲", "▼", "|‹", "›|"].indexOf(text) !== -1
    implicitHeight: 34
    leftPadding: iconOnly ? 0 : 12
    rightPadding: iconOnly ? 0 : 12
    implicitWidth: iconOnly ? implicitHeight : Math.max(70, contentItem.implicitWidth + leftPadding + rightPadding)
    font.pixelSize: 13
    palette.buttonText: theme.textColor
    contentItem: Text {
        text: control.text
        color: control.enabled ? theme.textColor : theme.mutedTextColor
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 6
        color: !control.enabled ? theme.panelColor : (control.selected || control.down ? theme.selectionColor : (control.hovered ? theme.panelHoverColor : theme.panelRaisedColor))
        border.color: control.activeFocus ? theme.accentColor : theme.borderColor
        border.width: control.activeFocus ? 2 : 1
        Behavior on color { ColorAnimation { duration: 90 } }
    }
}
