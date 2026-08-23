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

    implicitHeight: showButton ? 34 : 0
    implicitWidth: showButton ? 150 : 0

    Settings {
        id: pickerSettings
        category: "MintColorPicker"
        property string recentColorsJson: "[]"
    }

    property var recentColors: []
    property bool _syncing: false

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
        hueSlider.value = hsv.h * 359
        saturationSlider.value = hsv.s * 100
        valueSlider.value = hsv.v * 100
        alphaSlider.value = popup.workingColor.a * 100
        hexField.text = colorToHex(popup.workingColor, false)
        _syncing = false
    }

    function syncColorFromControls() {
        if (_syncing)
            return
        popup.workingColor = Qt.hsva(hueSlider.value / 359.0,
                                     saturationSlider.value / 100.0,
                                     valueSlider.value / 100.0,
                                     alphaEnabled ? alphaSlider.value / 100.0 : 1.0)
        hexField.text = colorToHex(popup.workingColor, false)
    }

    function applyHexField() {
        var parsed = colorFromHex(hexField.text, popup.workingColor)
        syncUiFromColor(parsed)
    }

    function commitColor() {
        var includeAlpha = alphaEnabled && popup.workingColor.a < 0.999
        root.colorValue = colorToHex(popup.workingColor, includeAlpha)
        addRecent(root.colorValue)
        colorPicked(root.colorValue)
        popup.close()
    }

    function openPicker(value) {
        if (value !== undefined && value !== null && String(value).length > 0)
            root.colorValue = root.normalized(value)
        root.syncUiFromColor(root.colorValue)
        popup.open()
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
                Layout.preferredWidth: 24
                Layout.preferredHeight: 20
                radius: 4
                border.color: theme.borderColor
                border.width: 1

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: 3
                    color: "#FFFFFF"
                    opacity: 1
                }
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: 3
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
            Text {
                text: "▾"
                color: theme.mutedTextColor
                verticalAlignment: Text.AlignVCenter
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
        y: root.height + 4
        width: 324
        padding: 10
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

        property color workingColor: root.normalized(root.colorValue)

        background: Rectangle {
            radius: 8
            color: theme.panelRaisedColor
            border.color: theme.borderColor
        }

        contentItem: ColumnLayout {
            spacing: 10

            Text {
                text: root.dialogTitle
                color: theme.textColor
                font.bold: true
                font.pixelSize: 13
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    Layout.preferredWidth: 58
                    Layout.preferredHeight: 58
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
                    spacing: 4

                    Text {
                        Layout.fillWidth: true
                        text: root.colorToHex(popup.workingColor, root.alphaEnabled && popup.workingColor.a < 0.999)
                        color: theme.textColor
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.alphaEnabled ? ("Alpha: " + Math.round(alphaSlider.value) + "%") : "Alpha: 100%"
                        color: theme.mutedTextColor
                        font.pixelSize: 11
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Button {
                            text: "Eyedropper"
                            onClicked: {
                                eyedropperDialog.selectedColor = popup.workingColor
                                eyedropperDialog.open()
                            }
                        }
                        Button {
                            text: "Copy HEX"
                            onClicked: hexField.selectAll()
                        }
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 8
                columnSpacing: 8

                Text { text: "Hue"; color: theme.mutedTextColor }
                Slider {
                    id: hueSlider
                    Layout.fillWidth: true
                    from: 0
                    to: 359
                    onValueChanged: root.syncColorFromControls()
                }

                Text { text: "Saturation"; color: theme.mutedTextColor }
                Slider {
                    id: saturationSlider
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    onValueChanged: root.syncColorFromControls()
                }

                Text { text: "Brightness"; color: theme.mutedTextColor }
                Slider {
                    id: valueSlider
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    onValueChanged: root.syncColorFromControls()
                }

                Text { text: "Alpha"; color: theme.mutedTextColor; visible: root.alphaEnabled }
                Slider {
                    id: alphaSlider
                    Layout.fillWidth: true
                    visible: root.alphaEnabled
                    from: 0
                    to: 100
                    value: 100
                    onValueChanged: root.syncColorFromControls()
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
                        text: "Recent colours"
                        color: theme.mutedTextColor
                        font.pixelSize: 11
                        Layout.fillWidth: true
                    }
                    Button {
                        visible: root.recentColors.length > 0
                        text: "Clear"
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
                            implicitWidth: 42
                            implicitHeight: 28
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
                    text: "Cancel"
                    onClicked: popup.close()
                }
                Button {
                    text: "Apply"
                    onClicked: root.commitColor()
                }
            }
        }
    }

    ColorDialog {
        id: eyedropperDialog
        title: "Pick colour"
        options: root.alphaEnabled ? ColorDialog.ShowAlphaChannel : 0
        onAccepted: root.syncUiFromColor(selectedColor)
    }
}
