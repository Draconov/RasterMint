import QtQuick
import QtQuick.Controls

ScrollBar {
    id: control

    // Thin overlay indicator with no track, border, or surrounding padding.
    // Attached vertical scrollbars keep Qt's normal right-edge placement.
    implicitWidth: 4
    implicitHeight: 4
    minimumSize: 0.08
    padding: 0
    hoverEnabled: true

    property bool indicatorVisible: false

    function revealIndicator() {
        hideDelay.stop()
        indicatorVisible = true
    }

    function scheduleHide() {
        if (!active && !pressed && !hovered && indicatorVisible)
            hideDelay.restart()
    }

    onActiveChanged: active ? revealIndicator() : scheduleHide()
    onPressedChanged: pressed ? revealIndicator() : scheduleHide()
    onHoveredChanged: hovered ? revealIndicator() : scheduleHide()
    // Some wheel/touchpad paths can update the attached scrollbar position
    // without keeping `active` true for a full frame. Treat any real scroll
    // movement as activity so the thumb is always revealed to the user.
    onPositionChanged: {
        if (enabled && size < 1.0) {
            revealIndicator()
            scheduleHide()
        }
    }
    onSizeChanged: {
        if (size >= 1.0) {
            hideDelay.stop()
            indicatorVisible = false
        }
    }

    Timer {
        id: hideDelay
        interval: 300
        repeat: false
        onTriggered: {
            if (!control.active && !control.pressed && !control.hovered)
                control.indicatorVisible = false
        }
    }

    contentItem: Rectangle {
        implicitWidth: 4
        implicitHeight: 4
        radius: 2
        color: control.hovered || control.pressed
               ? theme.accentHoverColor
               : theme.accentColor
        opacity: control.enabled && control.size < 1.0 && control.indicatorVisible ? 1.0 : 0.0

        Behavior on opacity {
            NumberAnimation { duration: 80 }
        }
    }

    background: Item { }
}
