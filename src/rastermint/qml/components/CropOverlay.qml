import QtQuick

Item {
    id: root
    visible: backend.cropEditing

    readonly property real minNormW: 1.0 / Math.max(1, backend.cropDisplayWidth)
    readonly property real minNormH: 1.0 / Math.max(1, backend.cropDisplayHeight)
    readonly property real nx: backend.cropDraftNormX
    readonly property real ny: backend.cropDraftNormY
    readonly property real nw: backend.cropDraftNormWidth
    readonly property real nh: backend.cropDraftNormHeight

    function clamp(value, low, high) { return Math.max(low, Math.min(high, value)) }
    function ratioNorm() {
        var ratio = Number(backend.cropAspectRatio)
        if (!isFinite(ratio) || ratio <= 0)
            return 0
        return ratio * Math.max(1, backend.cropDisplayHeight) / Math.max(1, backend.cropDisplayWidth)
    }
    function commit(x, y, w, h) {
        w = Math.max(minNormW, Math.min(1, w))
        h = Math.max(minNormH, Math.min(1, h))
        x = clamp(x, 0, 1 - w)
        y = clamp(y, 0, 1 - h)
        backend.setCropDraftRect(x, y, w, h)
    }
    function constrainedCorner(anchorX, anchorY, pointerX, pointerY, role) {
        var leftSide = role.indexOf("left") >= 0
        var topSide = role.indexOf("top") >= 0
        var rawW = Math.max(minNormW, Math.abs(pointerX - anchorX))
        var rawH = Math.max(minNormH, Math.abs(pointerY - anchorY))
        var ratio = ratioNorm()
        if (ratio > 0) {
            if (rawW / rawH > ratio)
                rawH = rawW / ratio
            else
                rawW = rawH * ratio
        }
        rawW = Math.min(rawW, leftSide ? anchorX : 1 - anchorX)
        rawH = Math.min(rawH, topSide ? anchorY : 1 - anchorY)
        if (ratio > 0) {
            if (rawW / rawH > ratio)
                rawW = rawH * ratio
            else
                rawH = rawW / ratio
        }
        var x = leftSide ? anchorX - rawW : anchorX
        var y = topSide ? anchorY - rawH : anchorY
        commit(x, y, rawW, rawH)
    }
    function resizeFromHandle(role, pointerX, pointerY, sx, sy, sw, sh) {
        var right = sx + sw
        var bottom = sy + sh
        var ratio = ratioNorm()
        if (role.indexOf("left") >= 0 && role.indexOf("top") >= 0) {
            constrainedCorner(right, bottom, pointerX, pointerY, "left-top"); return
        }
        if (role.indexOf("right") >= 0 && role.indexOf("top") >= 0) {
            constrainedCorner(sx, bottom, pointerX, pointerY, "right-top"); return
        }
        if (role.indexOf("left") >= 0 && role.indexOf("bottom") >= 0) {
            constrainedCorner(right, sy, pointerX, pointerY, "left-bottom"); return
        }
        if (role.indexOf("right") >= 0 && role.indexOf("bottom") >= 0) {
            constrainedCorner(sx, sy, pointerX, pointerY, "right-bottom"); return
        }

        if (role === "left" || role === "right") {
            var anchorX = role === "left" ? right : sx
            var newW = Math.max(minNormW, Math.abs(pointerX - anchorX))
            newW = Math.min(newW, role === "left" ? anchorX : 1 - anchorX)
            var newH = sh
            var newY = sy
            if (ratio > 0) {
                newH = Math.max(minNormH, newW / ratio)
                var centerY = sy + sh / 2
                newY = centerY - newH / 2
                if (newY < 0) newY = 0
                if (newY + newH > 1) newY = 1 - newH
            }
            commit(role === "left" ? anchorX - newW : anchorX, newY, newW, newH)
            return
        }

        if (role === "top" || role === "bottom") {
            var anchorY = role === "top" ? bottom : sy
            var newH2 = Math.max(minNormH, Math.abs(pointerY - anchorY))
            newH2 = Math.min(newH2, role === "top" ? anchorY : 1 - anchorY)
            var newW2 = sw
            var newX = sx
            if (ratio > 0) {
                newW2 = Math.max(minNormW, newH2 * ratio)
                var centerX = sx + sw / 2
                newX = centerX - newW2 / 2
                if (newX < 0) newX = 0
                if (newX + newW2 > 1) newX = 1 - newW2
            }
            commit(newX, role === "top" ? anchorY - newH2 : anchorY, newW2, newH2)
        }
    }

    // Dim everything outside the draft rectangle without obscuring the source.
    Rectangle { x: 0; y: 0; width: parent.width; height: cropBox.y; color: theme.canvasColor; opacity: 0.72 }
    Rectangle { x: 0; y: cropBox.y + cropBox.height; width: parent.width; height: Math.max(0, parent.height - y); color: theme.canvasColor; opacity: 0.72 }
    Rectangle { x: 0; y: cropBox.y; width: cropBox.x; height: cropBox.height; color: theme.canvasColor; opacity: 0.72 }
    Rectangle { x: cropBox.x + cropBox.width; y: cropBox.y; width: Math.max(0, parent.width - x); height: cropBox.height; color: theme.canvasColor; opacity: 0.72 }

    // Click-drag outside the current crop to create a fresh rectangle.
    MouseArea {
        id: createArea
        anchors.fill: parent
        z: 1
        acceptedButtons: Qt.LeftButton
        property real startX: 0
        property real startY: 0
        onPressed: function(mouse) {
            var px = root.clamp(mouse.x / Math.max(1, width), 0, 1)
            var py = root.clamp(mouse.y / Math.max(1, height), 0, 1)
            if (px >= root.nx && px <= root.nx + root.nw && py >= root.ny && py <= root.ny + root.nh) {
                mouse.accepted = false
                return
            }
            startX = px; startY = py
            root.commit(px, py, root.minNormW, root.minNormH)
        }
        onPositionChanged: function(mouse) {
            if (!pressed) return
            var px = root.clamp(mouse.x / Math.max(1, width), 0, 1)
            var py = root.clamp(mouse.y / Math.max(1, height), 0, 1)
            var left = Math.min(startX, px)
            var top = Math.min(startY, py)
            var w = Math.max(root.minNormW, Math.abs(px - startX))
            var h = Math.max(root.minNormH, Math.abs(py - startY))
            var ratio = root.ratioNorm()
            if (ratio > 0) {
                if (w / h > ratio) h = w / ratio
                else w = h * ratio
                if (left + w > 1) w = 1 - left
                if (top + h > 1) h = 1 - top
            }
            root.commit(left, top, w, h)
        }
    }

    Item {
        id: cropBox
        z: 5
        x: root.nx * root.width
        y: root.ny * root.height
        width: Math.max(1, root.nw * root.width)
        height: Math.max(1, root.nh * root.height)

        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.width: 2
            border.color: theme.accentColor
        }

        Canvas {
            id: guideCanvas
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                var mode = String(backend.cropOverlay)
                if (mode === "None") return
                ctx.strokeStyle = theme.textColor
                ctx.globalAlpha = 0.62
                ctx.lineWidth = 1
                function v(frac) { ctx.beginPath(); ctx.moveTo(width * frac, 0); ctx.lineTo(width * frac, height); ctx.stroke() }
                function h(frac) { ctx.beginPath(); ctx.moveTo(0, height * frac); ctx.lineTo(width, height * frac); ctx.stroke() }
                if (mode === "Rule of Thirds") { v(1/3); v(2/3); h(1/3); h(2/3) }
                else if (mode === "Grid") { v(0.25); v(0.5); v(0.75); h(0.25); h(0.5); h(0.75) }
                else if (mode === "Center") { v(0.5); h(0.5) }
            }
            Connections { target: backend; function onCropChanged() { guideCanvas.requestPaint() } }
        }

        MouseArea {
            id: moveArea
            anchors.fill: parent
            z: 3
            cursorShape: Qt.SizeAllCursor
            acceptedButtons: Qt.LeftButton
            property real pressX: 0
            property real pressY: 0
            property real startX: 0
            property real startY: 0
            property real startW: 1
            property real startH: 1
            onPressed: function(mouse) {
                var point = mapToItem(root, mouse.x, mouse.y)
                pressX = point.x / Math.max(1, root.width)
                pressY = point.y / Math.max(1, root.height)
                startX = root.nx; startY = root.ny; startW = root.nw; startH = root.nh
            }
            onPositionChanged: function(mouse) {
                if (!pressed) return
                var point = mapToItem(root, mouse.x, mouse.y)
                var px = point.x / Math.max(1, root.width)
                var py = point.y / Math.max(1, root.height)
                root.commit(startX + px - pressX, startY + py - pressY, startW, startH)
            }
            onDoubleClicked: backend.applyCropEdit()
        }

        Repeater {
            model: ["left-top", "top", "right-top", "right", "right-bottom", "bottom", "left-bottom", "left"]
            delegate: Rectangle {
                id: handle
                required property string modelData
                property bool isLeft: modelData.indexOf("left") >= 0
                property bool isRight: modelData.indexOf("right") >= 0
                property bool isTop: modelData.indexOf("top") >= 0
                property bool isBottom: modelData.indexOf("bottom") >= 0
                width: 10; height: 10; radius: 2; z: 10
                color: theme.accentColor
                border.width: 1
                border.color: theme.textColor
                x: isLeft ? -width / 2 : isRight ? cropBox.width - width / 2 : cropBox.width / 2 - width / 2
                y: isTop ? -height / 2 : isBottom ? cropBox.height - height / 2 : cropBox.height / 2 - height / 2

                MouseArea {
                    anchors.centerIn: parent
                    width: 26; height: 26
                    acceptedButtons: Qt.LeftButton
                    cursorShape: handle.modelData === "left" || handle.modelData === "right" ? Qt.SizeHorCursor
                               : handle.modelData === "top" || handle.modelData === "bottom" ? Qt.SizeVerCursor
                               : handle.modelData === "left-top" || handle.modelData === "right-bottom" ? Qt.SizeFDiagCursor
                               : Qt.SizeBDiagCursor
                    property real sx: 0
                    property real sy: 0
                    property real sw: 1
                    property real sh: 1
                    onPressed: { sx = root.nx; sy = root.ny; sw = root.nw; sh = root.nh }
                    onPositionChanged: function(mouse) {
                        if (!pressed) return
                        var point = mapToItem(root, mouse.x, mouse.y)
                        root.resizeFromHandle(
                            handle.modelData,
                            root.clamp(point.x / Math.max(1, root.width), 0, 1),
                            root.clamp(point.y / Math.max(1, root.height), 0, 1),
                            sx, sy, sw, sh
                        )
                    }
                }
            }
        }
    }
}
