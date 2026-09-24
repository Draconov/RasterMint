import QtQuick
import QtQuick.Controls
import "components"

Item {
    id: root
    objectName: "imageCanvas"
    property real zoomFactor: 1.0
    property bool cropSpaceHeld: false
    focus: backend.cropEditing
    onVisibleChanged: { if (!visible) cropSpaceHeld = false }
    Keys.onPressed: function(event) {
        if (backend.cropEditing && event.key === Qt.Key_Space) {
            cropSpaceHeld = true
            event.accepted = true
        }
    }
    Keys.onReleased: function(event) {
        if (event.key === Qt.Key_Space && backend.cropEditing) {
            // Holding Space generates synthetic release/press pairs on systems
            // with keyboard auto-repeat. Only a physical release ends panning:
            // hiding cropPanArea mid-drag would cancel its mouse grab.
            if (!event.isAutoRepeat)
                cropSpaceHeld = false
            event.accepted = true
        }
    }
    // Do not clear Space on focus loss during a grabbed mouse gesture. Focus
    // can briefly move to an overlay during a long pan; the grab still owns it.
    onActiveFocusChanged: { if (!activeFocus && !cropPanArea.pressed) cropSpaceHeld = false }
    readonly property int logicalWidth: backend.cropEditing ? backend.cropDisplayWidth : backend.previewWidth
    readonly property int logicalHeight: backend.cropEditing ? backend.cropDisplayHeight : backend.previewHeight
    property real fitScale: logicalWidth > 0 && logicalHeight > 0 ? Math.max(0.01, Math.min(width / logicalWidth, height / logicalHeight)) : 1.0
    property real effectiveScale: fitScale * zoomFactor

    function clampPan(value, extent, viewport) {
        return Math.max(0, Math.min(Math.max(0, extent - viewport), value))
    }

    function resetView() {
        zoomFactor = 1.0
        flick.contentX = clampPan(imageFrame.x + imageFrame.width / 2 - flick.width / 2,
                                flick.contentWidth, flick.width)
        flick.contentY = clampPan(imageFrame.y + imageFrame.height / 2 - flick.height / 2,
                                flick.contentHeight, flick.height)
        grid.requestPaint()
    }

    function zoomToCrop() {
        if (!backend.cropEditing || !backend.hasSource) return
        var w = Math.max(1e-6, Number(backend.cropDraftNormWidth))
        var h = Math.max(1e-6, Number(backend.cropDraftNormHeight))
        // Fit the whole rectangle with a small margin and preserve the zoom
        // range used by the wheel control. Handle full-image crops as Fit.
        zoomFactor = Math.max(0.15, Math.min(64,
            Math.min(flick.width / Math.max(1, logicalWidth * fitScale * w),
                     flick.height / Math.max(1, logicalHeight * fitScale * h)) * 0.9))
        var cx = Number(backend.cropDraftNormX) + w / 2
        var cy = Number(backend.cropDraftNormY) + h / 2
        // Image/frame dimensions depend on zoomFactor; synchronize geometry
        // before centering instead of centering against the previous frame.
        Qt.callLater(function() {
            flick.contentX = clampPan(imageFrame.x + imageFrame.width * cx - flick.width / 2,
                                     flick.contentWidth, flick.width)
            flick.contentY = clampPan(imageFrame.y + imageFrame.height * cy - flick.height / 2,
                                     flick.contentHeight, flick.height)
            grid.requestPaint()
        })
    }

    Rectangle { anchors.fill: parent; color: theme.canvasColor }

    Flickable {
        id: flick
        objectName: "cropViewport"
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: Math.max(width, imageFrame.width)
        contentHeight: Math.max(height, imageFrame.height)
        // Crop interactions (including Space+drag panning) are handled by
        // dedicated MouseAreas. Flickable otherwise steals their grab once
        // the pointer passes the drag threshold and stops the ongoing drag.
        interactive: backend.hasSource && !backend.cropEditing

        Item {
            id: imageFrame
            width: Math.max(1, root.logicalWidth * root.effectiveScale)
            height: Math.max(1, root.logicalHeight * root.effectiveScale)
            x: Math.max(0, (flick.width - width) / 2)
            y: Math.max(0, (flick.height - height) / 2)

            Image {
                id: previewImage
                anchors.fill: parent
                visible: backend.hasSource
                cache: false
                asynchronous: false
                fillMode: Image.Stretch
                source: backend.hasSource
                        ? (backend.cropEditing
                           ? "image://rastermint/crop-source?r=" + backend.previewRevision
                           : "image://rastermint/preview?r=" + backend.previewRevision)
                        : ""
                smooth: root.effectiveScale < 5
            }

            Item {
                id: comparisonOverlay
                anchors.fill: parent
                visible: backend.comparisonEnabled && !backend.cropEditing
                z: 5

                Item {
                    id: snapshotAClip
                    x: 0; y: 0
                    width: parent.width * backend.comparisonSplit
                    height: parent.height
                    clip: true
                    Image {
                        width: comparisonOverlay.width; height: comparisonOverlay.height
                        cache: false; asynchronous: false; fillMode: Image.Stretch
                        source: "image://rastermint/snapshot-a?r=" + backend.snapshotRevision
                        smooth: root.effectiveScale < 5
                    }
                }
                Item {
                    id: snapshotBClip
                    x: parent.width * backend.comparisonSplit; y: 0
                    width: parent.width - x; height: parent.height
                    clip: true
                    Image {
                        x: -snapshotBClip.x
                        width: comparisonOverlay.width; height: comparisonOverlay.height
                        cache: false; asynchronous: false; fillMode: Image.Stretch
                        source: "image://rastermint/snapshot-b?r=" + backend.snapshotRevision
                        smooth: root.effectiveScale < 5
                    }
                }
                Rectangle {
                    id: comparisonDivider
                    width: 2; height: parent.height
                    x: Math.round(parent.width * backend.comparisonSplit) - 1
                    color: theme.accentColor
                    Rectangle { width: 26; height: 26; radius: 13; anchors.centerIn: parent; color: theme.panelRaisedColor; border.color: theme.accentColor
                        Text { anchors.centerIn: parent; text: "↔"; color: theme.accentColor; font.bold: true }
                    }
                    MouseArea {
                        anchors.centerIn: parent
                        width: 32; height: parent.height
                        cursorShape: Qt.SizeHorCursor
                        function update(mouse) {
                            var point = mapToItem(comparisonOverlay, mouse.x, mouse.y)
                            backend.setComparisonSplit(Math.max(0, Math.min(1, point.x / Math.max(1, comparisonOverlay.width))))
                        }
                        onPressed: function(mouse) { update(mouse) }
                        onPositionChanged: function(mouse) { if (pressed) update(mouse) }
                    }
                }
                Text { anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 8; text: "A"; color: theme.textColor; font.bold: true }
                Text { anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 8; text: "B"; color: theme.textColor; font.bold: true }
            }

            Canvas {
                id: grid
                anchors.fill: parent
                visible: backend.hasSource && !backend.cropEditing && root.effectiveScale >= 8
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
                visible: !backend.cropEditing && Boolean(backend.settingsMap.mirror_horizontal)
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
                    onPressed: function(mouse) { backend.beginHistoryGroup(qsTr("Mirror horizontal axis")); updateAxis(mouse) }
                    onReleased: backend.endHistoryGroup()
                    onCanceled: backend.endHistoryGroup()
                    onPositionChanged: function(mouse) { if (pressed) updateAxis(mouse) }
                }
            }

            Rectangle {
                id: verticalMirrorAxis
                visible: !backend.cropEditing && Boolean(backend.settingsMap.mirror_vertical)
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
                    onPressed: function(mouse) { backend.beginHistoryGroup(qsTr("Mirror vertical axis")); updateAxis(mouse) }
                    onReleased: backend.endHistoryGroup()
                    onCanceled: backend.endHistoryGroup()
                    onPositionChanged: function(mouse) { if (pressed) updateAxis(mouse) }
                }
            }

            CropOverlay {
                id: cropOverlay
                anchors.fill: parent
                visible: backend.cropEditing
                z: 20
            }
        }
    }

    // Space + left-drag pans the viewport instead of editing the crop rectangle.
    // This sits above crop handles while Space is held; the crop geometry stays intact.
    MouseArea {
        id: cropPanArea
        objectName: "cropPanArea"
        anchors.fill: parent
        z: 30
        // Keep the MouseArea alive through the entire mouse gesture. Keyboard
        // focus changes (or a Space release) must not cancel an active drag.
        visible: backend.cropEditing && backend.hasSource && (root.cropSpaceHeld || pressed)
        enabled: backend.cropEditing && backend.hasSource && (root.cropSpaceHeld || pressed)
        acceptedButtons: Qt.LeftButton
        preventStealing: true
        cursorShape: Qt.ClosedHandCursor
        property real anchorX: 0
        property real anchorY: 0
        property real initialContentX: 0
        property real initialContentY: 0
        property bool gestureActive: false
        onPressed: function(mouse) {
            root.forceActiveFocus()
            gestureActive = true
            anchorX = mouse.x
            anchorY = mouse.y
            initialContentX = flick.contentX
            initialContentY = flick.contentY
            mouse.accepted = true
        }
        onPositionChanged: function(mouse) {
            if (!gestureActive || !pressed) return
            // Absolute displacement avoids drift or early interruption when
            // the pointer crosses a crop handle or Qt repeats the Space key.
            flick.contentX = root.clampPan(initialContentX - (mouse.x - anchorX),
                                           flick.contentWidth, flick.width)
            flick.contentY = root.clampPan(initialContentY - (mouse.y - anchorY),
                                           flick.contentHeight, flick.height)
        }
        onReleased: { gestureActive = false }
        onCanceled: { gestureActive = false }
        onWheel: function(wheel) { wheel.accepted = false }
    }

    Rectangle {
        id: emptyPrompt
        objectName: "emptyDropPrompt"
        anchors.centerIn: parent
        visible: !backend.hasSource
        radius: 7
        color: theme.panelRaisedColor
        border.color: theme.borderColor
        implicitWidth: emptyPromptText.implicitWidth + 24
        implicitHeight: 36
        Text {
            id: emptyPromptText
            anchors.centerIn: parent
            text: qsTr("Open or drop an image, GIF, or video to begin")
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
            if (Math.abs(old - root.zoomFactor) > 0.0001) {
                grid.requestPaint()
                backend.reportAction(qsTr("Zoom: %1%").arg(Math.round(root.zoomFactor * 100)))
            }
            wheel.accepted = true
        }
    }

    Rectangle {
        anchors { right: parent.right; bottom: parent.bottom; margins: 10 }
        visible: backend.hasSource
        radius: 6
        color: theme.panelRaisedColor
        border.color: theme.borderColor
        border.width: 1
        width: zoomText.implicitWidth + 16; height: 28
        Text { id: zoomText; anchors.centerIn: parent; text: Math.round(root.zoomFactor * 100) + "%"; color: theme.textColor; font.pixelSize: 11 }
    }

    Connections {
        target: backend
        function onPreviewChanged() { grid.requestPaint() }
        function onSourceChanged() { root.resetView() }
        function onCropChanged() {
            if (backend.cropEditing) {
                root.forceActiveFocus()
                grid.requestPaint()
            } else {
                root.cropSpaceHeld = false
            }
        }
    }
    onEffectiveScaleChanged: grid.requestPaint()
}
