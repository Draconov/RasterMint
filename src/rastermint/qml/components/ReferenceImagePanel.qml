import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Floating, source-synchronised reference viewport.  The header moves the
// panel; dragging the picture pans it without moving the panel itself.
Rectangle {
    id: root
    objectName: "referenceImagePanel"
    focus: false
    z: 50
    visible: backend.referenceVisible

    property real zoomFactor: 1.0
    readonly property real sourceAspect: backend.referenceHeight > 0
                                         ? backend.referenceWidth / backend.referenceHeight : 1.0
    readonly property real desiredImageWidth: sourceAspect >= 1.25 ? 440
                                              : sourceAspect <= 0.8 ? 255 : 320
    readonly property bool pointerOverPanel: panelHover.hovered
    property int lastReferenceWidth: 0
    property int lastReferenceHeight: 0
    readonly property bool pointerOverImageArea: Boolean(imageDragArea.containsMouse)

    width: Math.min(Math.max(205, parent ? parent.width - 24 : 440), desiredImageWidth + 18)
    height: Math.min(Math.max(210, parent ? parent.height - 24 : 520),
                     Math.max(205, Math.min(555, sourceAspect >= 0.85 && sourceAspect <= 1.2
                                           ? width : 76 + (width - 18) / Math.max(0.1, sourceAspect))))

    color: theme.panelColor
    border.color: theme.borderColor
    border.width: 1
    radius: 7
    clip: true

    function clampPan(value, extent, viewportSize) {
        return Math.max(0, Math.min(Math.max(0, extent - viewportSize), value))
    }

    function keepInWorkspace() {
        if (!parent)
            return
        x = Math.max(0, Math.min(x, Math.max(0, parent.width - width)))
        y = Math.max(0, Math.min(y, Math.max(0, parent.height - height)))
    }

    function fitImage() {
        zoomFactor = 1.0
        Qt.callLater(function() {
            imageViewport.contentX = clampPan(imageFrame.x + imageFrame.width / 2 - imageViewport.width / 2,
                                               imageViewport.contentWidth, imageViewport.width)
            imageViewport.contentY = clampPan(imageFrame.y + imageFrame.height / 2 - imageViewport.height / 2,
                                               imageViewport.contentHeight, imageViewport.height)
        })
    }

    function zoomAt(factor, x, y) {
        if (!backend.hasSource)
            return
        var originalWidth = Math.max(1, imageFrame.width)
        var originalHeight = Math.max(1, imageFrame.height)
        var anchorX = (imageViewport.contentX + x - imageFrame.x) / originalWidth
        var anchorY = (imageViewport.contentY + y - imageFrame.y) / originalHeight
        var next = Math.max(0.15, Math.min(64, zoomFactor * factor))
        if (Math.abs(next - zoomFactor) < 0.000001)
            return
        zoomFactor = next
        Qt.callLater(function() {
            imageViewport.contentX = clampPan(imageFrame.x + imageFrame.width * anchorX - x,
                                               imageViewport.contentWidth, imageViewport.width)
            imageViewport.contentY = clampPan(imageFrame.y + imageFrame.height * anchorY - y,
                                               imageViewport.contentHeight, imageViewport.height)
        })
    }

    Component.onCompleted: Qt.callLater(function() {
        if (root.parent) {
            root.x = Math.max(0, root.parent.width - root.width - 16)
            root.y = 16
        }
        root.fitImage()
    })
    onWidthChanged: Qt.callLater(keepInWorkspace)
    onHeightChanged: Qt.callLater(keepInWorkspace)
    onVisibleChanged: {
        if (visible) {
            Qt.callLater(keepInWorkspace)
            fitImage()
        }
    }

    Connections {
        target: root.parent
        function onWidthChanged() { root.keepInWorkspace() }
        function onHeightChanged() { root.keepInWorkspace() }
    }
    Connections {
        target: backend
        function onReferenceChanged() {
            // Do not reset pan/zoom on every video frame: only when the
            // source geometry changes (or when opening a new panel).
            if (root.lastReferenceWidth !== backend.referenceWidth
                    || root.lastReferenceHeight !== backend.referenceHeight) {
                root.lastReferenceWidth = backend.referenceWidth
                root.lastReferenceHeight = backend.referenceHeight
                root.fitImage()
            }
            root.keepInWorkspace()
        }
    }

    HoverHandler { id: panelHover }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        Rectangle {
            id: moveHandle
            Layout.fillWidth: true
            Layout.preferredHeight: 29
            color: theme.panelRaisedColor
            radius: 5

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 8

                Text {
                    text: qsTr("Reference Image")
                    color: theme.textColor
                    font.bold: true
                    font.pixelSize: 12
                }
                Text {
                    Layout.fillWidth: true
                    text: backend.referenceSourceName.length > 0
                          ? backend.referenceSourceName : qsTr("Source")
                    color: theme.mutedTextColor
                    font.pixelSize: 10
                    elide: Text.ElideMiddle
                    horizontalAlignment: Text.AlignRight
                }
            }

            MouseArea {
                id: panelDragHandle
                objectName: "referencePanelDragHandle"
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                cursorShape: Qt.SizeAllCursor
                property real pressedX: 0
                property real pressedY: 0
                property real originX: 0
                property real originY: 0
                onPressed: function(mouse) {
                    root.forceActiveFocus()
                    var point = mapToItem(root.parent, mouse.x, mouse.y)
                    pressedX = point.x
                    pressedY = point.y
                    originX = root.x
                    originY = root.y
                }
                onPositionChanged: function(mouse) {
                    if (!pressed || !root.parent)
                        return
                    var point = mapToItem(root.parent, mouse.x, mouse.y)
                    root.x = Math.max(0, Math.min(root.parent.width - root.width,
                                                  originX + point.x - pressedX))
                    root.y = Math.max(0, Math.min(root.parent.height - root.height,
                                                  originY + point.y - pressedY))
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: theme.canvasColor
            border.color: theme.borderColor
            border.width: 1
            radius: 5
            clip: true

            Text {
                anchors.centerIn: parent
                width: parent.width - 22
                visible: !backend.hasSource
                text: qsTr("Open or drop an image, GIF, or video to begin")
                color: theme.mutedTextColor
                font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }

            Flickable {
                id: imageViewport
                objectName: "referenceViewport"
                anchors.fill: parent
                anchors.margins: 2
                clip: true
                interactive: false
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: Math.max(width, imageFrame.width)
                contentHeight: Math.max(height, imageFrame.height)

                readonly property real fittedScale: backend.referenceWidth > 0 && backend.referenceHeight > 0
                                                    ? Math.max(0.001, Math.min(width / backend.referenceWidth,
                                                                               height / backend.referenceHeight))
                                                    : 1.0

                Item {
                    id: imageFrame
                    width: Math.max(1, backend.referenceWidth * imageViewport.fittedScale * root.zoomFactor)
                    height: Math.max(1, backend.referenceHeight * imageViewport.fittedScale * root.zoomFactor)
                    x: Math.max(0, (imageViewport.width - width) / 2)
                    y: Math.max(0, (imageViewport.height - height) / 2)

                    Image {
                        anchors.fill: parent
                        visible: backend.hasSource
                        source: backend.hasSource
                                ? "image://rastermint/reference?r=" + backend.referenceRevision : ""
                        cache: false
                        asynchronous: false
                        smooth: root.zoomFactor < 4
                        fillMode: Image.Stretch
                    }
                }
            }

            MouseArea {
                    id: imageDragArea
                    objectName: "referenceViewportDragArea"
                    anchors.fill: imageViewport
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton
                    cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                    property real pressedX: 0
                    property real pressedY: 0
                    property real originX: 0
                    property real originY: 0
                    onPressed: function(mouse) {
                        root.forceActiveFocus()
                        pressedX = mouse.x
                        pressedY = mouse.y
                        originX = imageViewport.contentX
                        originY = imageViewport.contentY
                    }
                    onPositionChanged: function(mouse) {
                        if (!pressed)
                            return
                        imageViewport.contentX = root.clampPan(originX - (mouse.x - pressedX),
                                                               imageViewport.contentWidth, imageViewport.width)
                        imageViewport.contentY = root.clampPan(originY - (mouse.y - pressedY),
                                                               imageViewport.contentHeight, imageViewport.height)
                    }
                    onWheel: function(wheel) {
                        root.forceActiveFocus()
                        if (wheel.angleDelta.y !== 0)
                            root.zoomAt(wheel.angleDelta.y > 0 ? 1.15 : 1 / 1.15, wheel.x, wheel.y)
                        wheel.accepted = true
                    }
                    onDoubleClicked: root.fitImage()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            MintButton {
                text: "−"
                onClicked: root.zoomAt(1 / 1.25, imageViewport.width / 2, imageViewport.height / 2)
            }
            Text {
                Layout.fillWidth: true
                text: Math.round(root.zoomFactor * 100) + "%"
                color: theme.mutedTextColor
                font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
            }
            MintButton {
                text: "+"
                onClicked: root.zoomAt(1.25, imageViewport.width / 2, imageViewport.height / 2)
            }
            MintButton {
                text: qsTr("Fit Preview")
                onClicked: root.fitImage()
            }
        }
    }
}
