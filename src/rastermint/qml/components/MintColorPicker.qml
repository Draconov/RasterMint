import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtCore

Item {
    id: root

    property string colorValue: "#FFFFFF"
    property string dialogTitle: "Choose colour"
    property bool alphaEnabled: true
    property int recentLimit: 12
    property bool showButton: true
    signal colorPicked(string value)

    // Match the main palette swatches instead of using a tiny colour chip.
    implicitHeight: showButton ? 46 : 0
    implicitWidth: showButton ? 150 : 0

    Settings {
        id: pickerSettings
        category: "MintColorPicker"
        property string recentColorsJson: "[]"
    }

    property var recentColors: []
    property bool _syncing: false
    property real pickerHue: 0.0
    property real pickerSaturation: 0.0
    property real pickerBrightness: 1.0
    property real pickerAlpha: 1.0
    property var _eyedropperDialog: null
    property bool _eyedropperActive: false

    function clamp01(v) {
        return Math.max(0, Math.min(1, Number(v)))
    }

    function normalized(value) {
        var candidate = String(value || "#FFFFFF").trim()
        if (candidate.length === 0)
            return "#FFFFFF"
        if (candidate[0] !== "#")
            candidate = "#" + candidate
        return candidate.toUpperCase()
    }

    function twoHex(v) {
        var n = Math.max(0, Math.min(255, Math.round(v)))
        var s = n.toString(16).toUpperCase()
        return s.length < 2 ? "0" + s : s
    }

    function colorToHex(c, includeAlpha) {
        var prefix = includeAlpha ? ("#" + twoHex(c.a * 255)) : "#"
        return prefix + twoHex(c.r * 255) + twoHex(c.g * 255) + twoHex(c.b * 255)
    }

    function colorFromHex(text, fallbackColor) {
        var value = normalized(text)
        if (/^#[0-9A-F]{6}$/.test(value))
            return value
        if (/^#[0-9A-F]{8}$/.test(value))
            return value
        return fallbackColor || normalized(root.colorValue)
    }

    function rgbToHsv(r, g, b) {
        var maxV = Math.max(r, g, b)
        var minV = Math.min(r, g, b)
        var delta = maxV - minV
        var h = 0
        var s = maxV === 0 ? 0 : delta / maxV
        var v = maxV
        if (delta !== 0) {
            if (maxV === r)
                h = ((g - b) / delta) % 6
            else if (maxV === g)
                h = ((b - r) / delta) + 2
            else
                h = ((r - g) / delta) + 4
            h /= 6
            if (h < 0)
                h += 1
        }
        return { h: h, s: s, v: v }
    }

    function loadRecentColors() {
        try {
            var parsed = JSON.parse(pickerSettings.recentColorsJson || "[]")
            if (Array.isArray(parsed)) {
                recentColors = parsed.filter(function(item) {
                    var value = String(item || "").trim().toUpperCase()
                    return /^#[0-9A-F]{6}$/.test(value) || /^#[0-9A-F]{8}$/.test(value)
                }).slice(0, recentLimit)
                return
            }
        } catch (e) {
        }
        recentColors = []
    }

    function saveRecentColors() {
        pickerSettings.recentColorsJson = JSON.stringify(recentColors)
    }

    function addRecent(value) {
        var normalizedValue = normalized(value)
        var next = [normalizedValue]
        for (var i = 0; i < recentColors.length; ++i) {
            if (recentColors[i] !== normalizedValue)
                next.push(recentColors[i])
        }
        recentColors = next.slice(0, recentLimit)
        saveRecentColors()
    }

    function syncUiFromColor(value) {
        _syncing = true
        popup.workingColor = colorFromHex(value, popup.workingColor)
        var hsv = rgbToHsv(popup.workingColor.r, popup.workingColor.g, popup.workingColor.b)
        pickerHue = hsv.h
        pickerSaturation = hsv.s
        pickerBrightness = hsv.v
        pickerAlpha = popup.workingColor.a
        alphaSlider.value = pickerAlpha * 100
        hexField.text = colorToHex(popup.workingColor, false)
        _syncing = false
        requestPickerPaint()
    }

    function syncColorFromPicker() {
        if (_syncing)
            return
        popup.workingColor = Qt.hsva(clamp01(pickerHue),
                                     clamp01(pickerSaturation),
                                     clamp01(pickerBrightness),
                                     alphaEnabled ? clamp01(pickerAlpha) : 1.0)
        hexField.text = colorToHex(popup.workingColor, false)
        requestPickerPaint()
    }

    function requestPickerPaint() {
        if (pickerSurfaceLoader.item)
            pickerSurfaceLoader.item.requestSvPaint()
    }

    function setHueFromPoint(px, py, size) {
        var center = size / 2
        var angle = Math.atan2(py - center, px - center) + Math.PI / 2
        var hue = angle / (Math.PI * 2)
        if (hue < 0)
            hue += 1
        pickerHue = hue
        syncColorFromPicker()
    }

    function setSaturationValueFromPoint(px, py, width, height) {
        pickerSaturation = clamp01(px / Math.max(1, width))
        pickerBrightness = clamp01(1.0 - (py / Math.max(1, height)))
        syncColorFromPicker()
    }

    function applyHexField() {
        var parsed = colorFromHex(hexField.text, popup.workingColor)
        syncUiFromColor(parsed)
    }

    function commitColor() {
        var includeAlpha = alphaEnabled && popup.workingColor.a < 0.999
        var committedValue = colorToHex(popup.workingColor, includeAlpha)
        addRecent(committedValue)
        colorPicked(committedValue)
        popup.close()
    }

    function openPicker(value) {
        var selectedValue = root.colorValue
        if (value !== undefined && value !== null && String(value).length > 0)
            selectedValue = root.normalized(value)
        root.syncUiFromColor(selectedValue)
        popup.open()
    }

    function openEyedropper() {
        if (!_eyedropperDialog)
            _eyedropperDialog = eyedropperComponent.createObject(root)
        if (!_eyedropperDialog)
            return
        _eyedropperDialog.selectedColor = popup.workingColor
        _eyedropperActive = true
        popup.close()
        _eyedropperDialog.open()
    }

    Connections {
        target: backend

        function onScreenColorPicked(value) {
            if (!root._eyedropperActive)
                return
            root._eyedropperActive = false
            root.syncUiFromColor(value)
            popup.open()
        }

        function onScreenEyedropperCancelled() {
            if (!root._eyedropperActive)
                return
            root._eyedropperActive = false
            popup.open()
        }
    }

    function positionPopupInViewport() {
        if (!popup.parent)
            return

        var margin = 8
        var gap = 4
        var origin = root.mapToItem(popup.parent, 0, 0)
        var maxX = Math.max(margin, popup.parent.width - popup.width - margin)
        var belowY = origin.y + root.height + gap
        var aboveY = origin.y - popup.height - gap
        var maxY = Math.max(margin, popup.parent.height - popup.height - margin)

        popup.x = Math.max(margin, Math.min(origin.x, maxX))

        if (belowY + popup.height <= popup.parent.height - margin)
            popup.y = belowY
        else if (aboveY >= margin)
            popup.y = aboveY
        else
            popup.y = Math.max(margin, Math.min(belowY, maxY))
    }

    Component {
        id: pickerSurfaceComponent

        Item {
            implicitWidth: 246
            implicitHeight: 246

            function requestSvPaint() {
                svCanvas.requestPaint()
            }

            function requestAllPaint() {
                wheelCanvas.requestPaint()
                svCanvas.requestPaint()
            }

            Canvas {
                id: wheelCanvas
                anchors.fill: parent
                property real ringWidth: 20
                property real innerRadius: Math.min(width, height) / 2 - ringWidth - 2

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    var cx = width / 2
                    var cy = height / 2
                    var radius = Math.min(width, height) / 2 - ringWidth / 2 - 2
                    for (var i = 0; i < 360; ++i) {
                        var start = (i - 90) * Math.PI / 180
                        var end = (i + 1.5 - 90) * Math.PI / 180
                        ctx.beginPath()
                        ctx.strokeStyle = Qt.hsla(i / 360.0, 1.0, 0.5, 1.0)
                        ctx.lineWidth = ringWidth
                        ctx.arc(cx, cy, radius, start, end, false)
                        ctx.stroke()
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.CrossCursor
                    onPressed: function(mouse) {
                        root.setHueFromPoint(mouse.x, mouse.y, wheelCanvas.width)
                    }
                    onPositionChanged: function(mouse) {
                        if (pressed)
                            root.setHueFromPoint(mouse.x, mouse.y, wheelCanvas.width)
                    }
                }
            }

            // Hue marker on the outer ring.
            Rectangle {
                width: 12
                height: 12
                radius: 6
                color: "transparent"
                border.color: "#FFFFFF"
                border.width: 2
                property real markerRadius: wheelCanvas.width / 2 - wheelCanvas.ringWidth / 2 - 2
                property real markerAngle: root.pickerHue * Math.PI * 2 - Math.PI / 2
                x: wheelCanvas.width / 2 + Math.cos(markerAngle) * markerRadius - width / 2
                y: wheelCanvas.height / 2 + Math.sin(markerAngle) * markerRadius - height / 2
            }

            Canvas {
                id: svCanvas
                // Keep every corner safely inside the hue ring's inner edge.
                // The old 146 px square had a diagonal slightly larger than
                // the available inner diameter, so its corners touched the ring.
                property real ringGap: 5
                width: Math.floor(Math.SQRT2 * Math.max(1, wheelCanvas.innerRadius - ringGap))
                height: width
                anchors.centerIn: parent

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)

                    var hueColor = Qt.hsva(root.pickerHue, 1.0, 1.0, 1.0)
                    var horizontal = ctx.createLinearGradient(0, 0, width, 0)
                    horizontal.addColorStop(0.0, "#FFFFFF")
                    horizontal.addColorStop(1.0, hueColor)
                    ctx.fillStyle = horizontal
                    ctx.fillRect(0, 0, width, height)

                    var vertical = ctx.createLinearGradient(0, 0, 0, height)
                    vertical.addColorStop(0.0, Qt.rgba(0, 0, 0, 0))
                    vertical.addColorStop(1.0, "#000000")
                    ctx.fillStyle = vertical
                    ctx.fillRect(0, 0, width, height)
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.CrossCursor
                    onPressed: function(mouse) {
                        root.setSaturationValueFromPoint(mouse.x, mouse.y, svCanvas.width, svCanvas.height)
                    }
                    onPositionChanged: function(mouse) {
                        if (pressed)
                            root.setSaturationValueFromPoint(mouse.x, mouse.y, svCanvas.width, svCanvas.height)
                    }
                }

                Rectangle {
                    width: 12
                    height: 12
                    radius: 6
                    color: "transparent"
                    border.color: "#FFFFFF"
                    border.width: 2
                    x: Math.max(-width / 2, Math.min(svCanvas.width - width / 2, root.pickerSaturation * svCanvas.width - width / 2))
                    y: Math.max(-height / 2, Math.min(svCanvas.height - height / 2, (1.0 - root.pickerBrightness) * svCanvas.height - height / 2))
                }
            }
        }
    }

    Component.onCompleted: loadRecentColors()

    Button {
        id: button
        anchors.fill: parent
        enabled: root.enabled
        visible: root.showButton
        hoverEnabled: true
        leftPadding: 8
        rightPadding: 8

        contentItem: RowLayout {
            spacing: 8

            Rectangle {
                Layout.preferredWidth: 38
                Layout.preferredHeight: 38
                radius: 5
                border.color: theme.borderColor
                border.width: 1
                color: "#FFFFFF"

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: 4
                    color: root.normalized(root.colorValue)
                }
            }

            Text {
                Layout.fillWidth: true
                text: root.normalized(root.colorValue).toUpperCase()
                color: root.enabled ? theme.textColor : theme.mutedTextColor
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                font.pixelSize: 12
            }
        }

        background: Rectangle {
            radius: 6
            color: button.down ? theme.selectionColor : (button.hovered ? theme.panelHoverColor : theme.panelRaisedColor)
            border.color: button.activeFocus ? theme.accentColor : theme.borderColor
            border.width: button.activeFocus ? 2 : 1
        }

        onClicked: root.openPicker(root.colorValue)
    }

    Popup {
        id: popup
        parent: Overlay.overlay
        width: Math.min(354, Math.max(220, parent ? parent.width - 16 : 354))
        height: Math.min(pickerColumn.implicitHeight + topPadding + bottomPadding,
                         Math.max(180, parent ? parent.height - 16 : pickerColumn.implicitHeight + topPadding + bottomPadding))
        padding: 12
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        property color workingColor: root.normalized(root.colorValue)

        onAboutToShow: Qt.callLater(root.positionPopupInViewport)
        onWidthChanged: {
            if (visible)
                Qt.callLater(root.positionPopupInViewport)
        }
        onHeightChanged: {
            if (visible)
                Qt.callLater(root.positionPopupInViewport)
        }

        background: Rectangle {
            radius: 8
            color: theme.panelRaisedColor
            border.color: theme.borderColor
        }

        contentItem: ScrollView {
            id: pickerScroll
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                id: pickerColumn
                width: pickerScroll.availableWidth
                spacing: 10

                Text {
                    text: root.dialogTitle
                color: theme.textColor
                font.bold: true
                font.pixelSize: 13
            }

            // Advanced wheel + saturation/value square. This is the primary
            // custom colour selection surface; the sliders below are only for
            // alpha, where precision is useful.
            Loader {
                id: pickerSurfaceLoader
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 246
                Layout.preferredHeight: 246
                active: popup.visible
                sourceComponent: pickerSurfaceComponent

                onLoaded: {
                    if (item)
                        item.requestAllPaint()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    Layout.preferredWidth: 44
                    Layout.preferredHeight: 44
                    radius: 6
                    border.color: theme.borderColor
                    border.width: 1
                    color: "#FFFFFF"

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 1
                        radius: 5
                        color: popup.workingColor
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    Text {
                        Layout.fillWidth: true
                        text: root.colorToHex(popup.workingColor, root.alphaEnabled && popup.workingColor.a < 0.999)
                        color: theme.textColor
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: qsTr("H ") + Math.round(root.pickerHue * 359)
                              + "°   S " + Math.round(root.pickerSaturation * 100)
                              + "%   V " + Math.round(root.pickerBrightness * 100) + "%"
                        color: theme.mutedTextColor
                        font.pixelSize: 10
                    }
                }

                Button {
                    text: qsTr("Eyedropper")
                    onClicked: root.openEyedropper()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: root.alphaEnabled
                spacing: 8

                Text {
                    text: qsTr("Alpha")
                    color: theme.mutedTextColor
                    font.pixelSize: 11
                }

                Slider {
                    id: alphaSlider
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: 100
                    onValueChanged: {
                        if (!root._syncing) {
                            root.pickerAlpha = value / 100.0
                            root.syncColorFromPicker()
                        }
                    }
                }

                Text {
                    text: Math.round(alphaSlider.value) + "%"
                    color: theme.textColor
                    font.pixelSize: 11
                    Layout.preferredWidth: 34
                    horizontalAlignment: Text.AlignRight
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Text {
                    text: "HEX"
                    color: theme.mutedTextColor
                    font.pixelSize: 11
                }

                TextField {
                    id: hexField
                    Layout.fillWidth: true
                    placeholderText: "#RRGGBB"
                    color: theme.textColor
                    selectedTextColor: theme.canvasColor
                    selectionColor: theme.accentColor
                    onEditingFinished: root.applyHexField()

                    background: Rectangle {
                        radius: 6
                        color: theme.panelHoverColor
                        border.color: hexField.activeFocus ? theme.accentColor : theme.borderColor
                        border.width: hexField.activeFocus ? 2 : 1
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: qsTr("Recent colours")
                        color: theme.mutedTextColor
                        font.pixelSize: 11
                        Layout.fillWidth: true
                    }
                    Button {
                        visible: root.recentColors.length > 0
                        text: qsTr("Clear")
                        onClicked: {
                            root.recentColors = []
                            root.saveRecentColors()
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 6
                    columnSpacing: 6
                    rowSpacing: 6

                    Repeater {
                        model: root.recentColors
                        delegate: Button {
                            required property string modelData
                            implicitWidth: 46
                            implicitHeight: 30
                            leftPadding: 0
                            rightPadding: 0
                            topPadding: 0
                            bottomPadding: 0
                            onClicked: root.syncUiFromColor(modelData)

                            contentItem: Rectangle {
                                radius: 4
                                color: modelData
                                border.color: theme.borderColor
                                border.width: 1
                            }

                            background: Rectangle {
                                radius: 5
                                color: hovered ? theme.panelHoverColor : theme.panelRaisedColor
                                border.color: theme.borderColor
                            }

                            ToolTip.visible: hovered
                            ToolTip.text: modelData
                        }
                    }
                }
            }

                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    Button {
                        text: qsTr("Cancel")
                        onClicked: popup.close()
                    }
                    Button {
                        text: qsTr("Apply")
                        onClicked: root.commitColor()
                    }
                }
            }
        }
    }

    // Keep the eyedropper controller lazy so every picker does not allocate
    // screen-sampling state during Main.qml startup. The backend owns the
    // transparent top-level capture windows because they must receive the next
    // click even when it happens outside RasterMint.
    Component {
        id: eyedropperComponent

        QtObject {
            property color selectedColor: popup.workingColor
            function open() { backend.startScreenEyedropper() }
        }
    }

    // Retain a lazy native colour dialog component for platform fallback paths.
    // It is never instantiated by the screen eyedropper and therefore adds no
    // startup cost.
    Component {
        id: colorDialogComponent

        ColorDialog {
            title: qsTr("Sample colour")
            options: root.alphaEnabled ? ColorDialog.ShowAlphaChannel : 0
            onAccepted: root.syncUiFromColor(selectedColor)
        }
    }
}
