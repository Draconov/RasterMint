import QtQuick
import QtQuick.Controls

Item {
    id: root
    property real zoomFactor: 1.0
    property real fitScale: backend.previewWidth > 0 && backend.previewHeight > 0 ? Math.max(0.01, Math.min(width / backend.previewWidth, height / backend.previewHeight)) : 1.0
    property real effectiveScale: fitScale * zoomFactor

    function resetView() {
        zoomFactor = 1.0
        flick.contentX = Math.max(0, (flick.contentWidth - flick.width) / 2)
        flick.contentY = Math.max(0, (flick.contentHeight - flick.height) / 2)
        grid.requestPaint()
    }

    Rectangle { anchors.fill: parent; color: theme.canvasColor }

    Flickable {
        id: flick
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: Math.max(width, imageFrame.width)
        contentHeight: Math.max(height, imageFrame.height)
        interactive: backend.hasSource

        Item {
            id: imageFrame
            width: Math.max(1, backend.previewWidth * root.effectiveScale)
            height: Math.max(1, backend.previewHeight * root.effectiveScale)
            x: Math.max(0, (flick.width - width) / 2)
            y: Math.max(0, (flick.height - height) / 2)

            Image {
                id: previewImage
                anchors.fill: parent
                visible: backend.hasSource
                cache: false
                asynchronous: false
                fillMode: Image.Stretch
                source: backend.hasSource ? "image://rastermint/preview?r=" + backend.previewRevision : ""
                smooth: root.effectiveScale < 5
            }

            Canvas {
                id: grid
                anchors.fill: parent
                visible: backend.hasSource && root.effectiveScale >= 8
                opacity: Math.min(0.65, 0.22 + (root.effectiveScale - 8) * 0.015)
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    if (!visible) return
                    var step = root.effectiveScale
                    var countX = backend.previewWidth
                    var countY = backend.previewHeight
                    for (var x = 0; x <= countX; ++x) {
                        ctx.beginPath()
                        ctx.lineWidth = (x % 8 === 0) ? 1.2 : 0.55
                        ctx.strokeStyle = (x % 8 === 0) ? "#8AA0B8" : "#596674"
                        ctx.moveTo(x * step, 0)
                        ctx.lineTo(x * step, height)
                        ctx.stroke()
                    }
                    for (var y = 0; y <= countY; ++y) {
                        ctx.beginPath()
                        ctx.lineWidth = (y % 8 === 0) ? 1.2 : 0.55
                        ctx.strokeStyle = (y % 8 === 0) ? "#8AA0B8" : "#596674"
                        ctx.moveTo(0, y * step)
                        ctx.lineTo(width, y * step)
                        ctx.stroke()
                    }
                }
            }

            Rectangle {
                id: horizontalMirrorAxis
                visible: Boolean(backend.settingsMap.mirror_horizontal)
                width: 2; height: parent.height
                x: Math.round(Number(backend.settingsMap.mirror_horizontal_axis) * parent.width) - 1
                color: theme.mirrorAxisColor
                z: 10
                Rectangle { width: 10; height: 26; radius: 5; color: theme.mirrorAxisColor; anchors.horizontalCenter: parent.horizontalCenter; anchors.verticalCenter: parent.verticalCenter; opacity: 0.75 }
                MouseArea {
                    id: horizontalAxisMouse
                    anchors.centerIn: parent
                    width: 18
                    height: parent.height
                    cursorShape: Qt.SizeHorCursor
                    function updateAxis(mouse) {
                        var point = mapToItem(imageFrame, mouse.x, mouse.y)
                        backend.setMirrorAxis("horizontal", Math.max(0, Math.min(1, point.x / Math.max(1, imageFrame.width))))
                    }
                    onPressed: function(mouse) { updateAxis(mouse) }
                    onPositionChanged: function(mouse) { if (pressed) updateAxis(mouse) }
                }
            }

            Rectangle {
                id: verticalMirrorAxis
                visible: Boolean(backend.settingsMap.mirror_vertical)
                width: parent.width; height: 2
                y: Math.round(Number(backend.settingsMap.mirror_vertical_axis) * parent.height) - 1
                color: theme.mirrorAxisColor
                z: 10
                Rectangle { width: 26; height: 10; radius: 5; color: theme.mirrorAxisColor; anchors.horizontalCenter: parent.horizontalCenter; anchors.verticalCenter: parent.verticalCenter; opacity: 0.75 }
                MouseArea {
                    id: verticalAxisMouse
                    anchors.centerIn: parent
                    width: parent.width
                    height: 18
                    cursorShape: Qt.SizeVerCursor
                    function updateAxis(mouse) {
                        var point = mapToItem(imageFrame, mouse.x, mouse.y)
                        backend.setMirrorAxis("vertical", Math.max(0, Math.min(1, point.y / Math.max(1, imageFrame.height))))
                    }
                    onPressed: function(mouse) { updateAxis(mouse) }
                    onPositionChanged: function(mouse) { if (pressed) updateAxis(mouse) }
                }
            }
        }
    }

    Rectangle {
        id: emptyPrompt
        objectName: "emptyDropPrompt"
        anchors.centerIn: parent
        visible: !backend.hasSource
        radius: 7
        color: Qt.rgba(0, 0, 0, 0.58)
        border.color: theme.borderColor
        implicitWidth: emptyPromptText.implicitWidth + 24
        implicitHeight: 36
        Text {
            id: emptyPromptText
            anchors.centerIn: parent
            text: "Open or drop an image, GIF, or video to begin"
            color: theme.textColor
            font.pixelSize: 12
        }
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.NoButton
        hoverEnabled: true
        onWheel: function(wheel) {
            if (!backend.hasSource) return
            var old = root.zoomFactor
            root.zoomFactor = Math.max(0.15, Math.min(64, root.zoomFactor * (wheel.angleDelta.y > 0 ? 1.15 : 1 / 1.15)))
            if (Math.abs(old - root.zoomFactor) > 0.0001) grid.requestPaint()
            wheel.accepted = true
        }
    }

    Rectangle {
        anchors { left: parent.left; bottom: parent.bottom; margins: 10 }
        visible: backend.hasSource
        radius: 6
        color: Qt.rgba(0, 0, 0, 0.55)
        width: zoomText.implicitWidth + 16; height: 28
        Text { id: zoomText; anchors.centerIn: parent; text: Math.round(root.zoomFactor * 100) + "%"; color: "white"; font.pixelSize: 11 }
    }

    Connections {
        target: backend
        function onPreviewChanged() { grid.requestPaint() }
        function onSourceChanged() { root.resetView() }
    }
    onEffectiveScaleChanged: grid.requestPaint()
}
