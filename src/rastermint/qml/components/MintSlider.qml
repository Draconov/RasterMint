import QtQuick
import QtQuick.Controls

Slider {
    id: control

    implicitWidth: 260
    implicitHeight: 28
    live: true
    snapMode: Slider.SnapAlways

    // Mouse dragging is handled across the whole slider surface, not just the knob.
    // Keep this separate from Slider.pressed so ScrollView cannot steal the gesture.
    readonly property bool interactionActive: pointerArea.pressed
    property real dragValue: value

    readonly property real displayValue: interactionActive ? dragValue : value
    readonly property real displayPosition: {
        var span = to - from
        if (Math.abs(span) < 1e-12)
            return 0
        return Math.max(0, Math.min(1, (displayValue - from) / span))
    }
    readonly property real displayVisualPosition: mirrored ? 1 - displayPosition : displayPosition

    signal userMoved(real newValue)

    function decimalPlaces(number) {
        var numeric = Math.abs(Number(number))
        if (!isFinite(numeric) || numeric === 0)
            return 0

        var text = numeric.toString().toLowerCase()
        var exponentMarker = text.indexOf("e")
        if (exponentMarker >= 0) {
            var coefficient = text.substring(0, exponentMarker)
            var exponent = Number(text.substring(exponentMarker + 1))
            var decimalMarker = coefficient.indexOf(".")
            var fractionDigits = decimalMarker >= 0 ? coefficient.length - decimalMarker - 1 : 0
            return Math.max(0, fractionDigits - exponent)
        }

        var decimalMarker = text.indexOf(".")
        return decimalMarker >= 0 ? text.length - decimalMarker - 1 : 0
    }

    function smartRound(rawValue) {
        var low = Math.min(from, to)
        var high = Math.max(from, to)
        var nextValue = Math.max(low, Math.min(high, Number(rawValue)))

        if (stepSize > 0) {
            var steps = Math.round((nextValue - from) / stepSize)
            nextValue = from + steps * stepSize

            // Round to the precision implied by the slider's own scale.
            // This removes binary float noise such as 1.4000000000000001.
            var precision = Math.min(
                12,
                Math.max(
                    decimalPlaces(stepSize),
                    decimalPlaces(from),
                    decimalPlaces(to)
                )
            )
            var factor = Math.pow(10, precision)
            nextValue = Math.round(nextValue * factor) / factor
        } else {
            // Continuous sliders (timeline) still get floating-point noise cleanup.
            nextValue = Number(nextValue.toFixed(9))
        }

        if (Math.abs(nextValue) < 1e-12)
            nextValue = 0

        return Math.max(low, Math.min(high, nextValue))
    }

    function valueForPointerX(pointerX) {
        var handleWidth = handle ? handle.width : 0
        var start = leftPadding + handleWidth / 2
        var span = Math.max(1, availableWidth - handleWidth)
        var position = Math.max(0, Math.min(1, (pointerX - start) / span))

        if (mirrored)
            position = 1 - position

        return smartRound(from + position * (to - from))
    }

    function updateFromPointer(pointerX) {
        if (!enabled)
            return

        var nextValue = valueForPointerX(pointerX)
        if (Math.abs(nextValue - dragValue) <= 1e-12)
            return

        dragValue = nextValue
        userMoved(nextValue)
    }

    // Preserve keyboard-driven Slider behavior as well.
    Connections {
        target: control
        function onMoved() {
            if (!pointerArea.pressed)
                control.userMoved(control.smartRound(control.value))
        }
    }

    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: 5
        radius: 3
        color: theme.borderColor

        Rectangle {
            width: control.displayVisualPosition * parent.width
            height: parent.height
            radius: parent.radius
            color: control.enabled ? theme.accentColor : theme.mutedTextColor
            opacity: control.enabled ? 1.0 : 0.5
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.displayVisualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: 18
        height: 18
        radius: 9
        color: (control.pressed || control.interactionActive) ? theme.accentHoverColor : theme.accentColor
        border.color: theme.panelColor
        border.width: 2
        opacity: control.enabled ? 1.0 : 0.55
    }

    MouseArea {
        id: pointerArea
        anchors.fill: parent
        enabled: control.enabled
        acceptedButtons: Qt.LeftButton
        hoverEnabled: true
        preventStealing: true
        cursorShape: Qt.SizeHorCursor

        property real dragOffsetX: 0

        onPressed: function(mouse) {
            control.forceActiveFocus(Qt.MouseFocusReason)
            control.dragValue = control.smartRound(control.value)

            var handleCenter = control.handle.x + control.handle.width / 2
            var hitPadding = Math.max(4, control.handle.width * 0.35)

            if (Math.abs(mouse.x - handleCenter) <= control.handle.width / 2 + hitPadding) {
                // Preserve the exact point where the user grabbed the knob.
                dragOffsetX = mouse.x - handleCenter
            } else {
                // Press anywhere on the track, jump there, then scrub freely while held.
                dragOffsetX = 0
                control.updateFromPointer(mouse.x)
            }
        }

        onPositionChanged: function(mouse) {
            if (pressed)
                control.updateFromPointer(mouse.x - dragOffsetX)
        }

        onReleased: dragOffsetX = 0
        onCanceled: dragOffsetX = 0
    }
}
