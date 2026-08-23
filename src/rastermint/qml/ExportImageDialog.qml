import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "components"

Dialog {
    id: root

    title: "Export Image"
    modal: true
    popupType: Popup.Item
    readonly property real overlayWidth: Overlay.overlay ? Overlay.overlay.width : 900
    readonly property real overlayHeight: Overlay.overlay ? Overlay.overlay.height : 700
    readonly property real desiredBodyHeight: Math.max(500, settingsColumn.implicitHeight)
    readonly property real desiredDialogHeight: 46 + (padding * 2) + desiredBodyHeight

    width: Math.max(560, Math.min(760, overlayWidth - 32))
    height: Math.max(360, Math.min(desiredDialogHeight, overlayHeight - 32))
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.NoButton
    padding: 16

    property var urlNormalizer: function(value) { return value ? value.toString() : "" }

    property int sourceWidth: 1
    property int sourceHeight: 1
    property int baseWidth: 1
    property int baseHeight: 1
    property int exportWidth: 1
    property int exportHeight: 1
    property int exportQuality: 90
    property bool updatingDimensions: false
    property bool sourceHasTransparency: false
    property bool sourceHasAsciiLayer: false

    readonly property real baseAspect: baseHeight > 0 ? baseWidth / baseHeight : 1.0
    readonly property string selectedFormat: formatCombo.currentText
    readonly property bool lossyFormat: selectedFormat === "JPEG" || selectedFormat === "WebP"
    readonly property bool textFormat: selectedFormat === "TXT"
    readonly property bool transparencySupported: selectedFormat === "PNG"
                                               || selectedFormat === "WebP"
                                               || selectedFormat === "TIFF"
                                               || selectedFormat === "SVG"

    function clampDimension(value) {
        return Math.max(1, Math.min(32768, Math.round(Number(value))))
    }

    function setDimensions(width, height) {
        updatingDimensions = true
        exportWidth = clampDimension(width)
        exportHeight = clampDimension(height)
        widthInput.text = String(exportWidth)
        heightInput.text = String(exportHeight)
        updatingDimensions = false
    }

    function applyScale(scale) {
        setDimensions(baseWidth * scale, baseHeight * scale)
    }

    function commitWidth() {
        var width = parseInt(widthInput.text, 10)
        if (isNaN(width))
            width = exportWidth
        width = clampDimension(width)
        if (aspectLock.checked)
            setDimensions(width, Math.max(1, Math.round(width / Math.max(0.000001, baseAspect))))
        else
            setDimensions(width, exportHeight)
        scaleCombo.currentIndex = scaleCombo.count - 1
    }

    function commitHeight() {
        var height = parseInt(heightInput.text, 10)
        if (isNaN(height))
            height = exportHeight
        height = clampDimension(height)
        if (aspectLock.checked)
            setDimensions(Math.max(1, Math.round(height * baseAspect)), height)
        else
            setDimensions(exportWidth, height)
        scaleCombo.currentIndex = scaleCombo.count - 1
    }

    function resetFromCurrentImage() {
        var info = backend.exportImageInfo()
        sourceWidth = Math.max(1, Number(info.sourceWidth || 1))
        sourceHeight = Math.max(1, Number(info.sourceHeight || 1))
        baseWidth = Math.max(1, Number(info.width || sourceWidth))
        baseHeight = Math.max(1, Number(info.height || sourceHeight))
        exportQuality = 90
        sourceHasTransparency = Boolean(info.hasTransparency)
        sourceHasAsciiLayer = Boolean(info.hasAsciiLayer)
        aspectLock.checked = true
        scaleCombo.currentIndex = 2
        formatCombo.currentIndex = 0
        resampleCombo.currentIndex = 0
        preserveTransparencyCheck.checked = sourceHasTransparency
        applyScale(1.0)
    }

    function openExportFileDialog() {
        exportFileDialog.selectedFile = backend.suggestedExportFile(selectedFormat)
        exportFileDialog.open()
    }

    function exportOptions() {
        return {
            "width": exportWidth,
            "height": exportHeight,
            "format": selectedFormat,
            "quality": exportQuality,
            "resampling": resampleCombo.currentText,
            "preserveTransparency": preserveTransparencyCheck.checked
                                     && sourceHasTransparency
                                     && transparencySupported
        }
    }

    onOpened: resetFromCurrentImage()

    background: Rectangle {
        color: theme.panelColor
        border.color: theme.borderColor
        border.width: 1
        radius: 10
    }

    Overlay.modal: Rectangle {
        color: Qt.rgba(0, 0, 0, 0.5)
    }

    header: Rectangle {
        implicitHeight: 46
        color: theme.panelRaisedColor

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: theme.borderColor
        }

        Text {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 16
            text: "Export Image"
            color: theme.textColor
            font.bold: true
            font.pixelSize: 15
        }
    }

    contentItem: ScrollView {
        id: exportScroll
        clip: true
        contentWidth: availableWidth
        contentHeight: exportBody.height

        ScrollBar.horizontal: ScrollBar {
            policy: ScrollBar.AlwaysOff
        }
        ScrollBar.vertical: ScrollBar {
            policy: exportScroll.contentHeight > exportScroll.availableHeight
                    ? ScrollBar.AsNeeded
                    : ScrollBar.AlwaysOff
        }

        RowLayout {
            id: exportBody
            width: exportScroll.availableWidth
            height: root.desiredBodyHeight
            spacing: 16

        Rectangle {
            Layout.preferredWidth: 330
            Layout.fillHeight: true
            radius: 8
            color: theme.canvasColor
            border.color: theme.borderColor
            clip: true

            Image {
                anchors.fill: parent
                anchors.margins: 14
                source: backend.hasSource ? "image://rastermint/preview?r=" + backend.previewRevision : ""
                cache: false
                asynchronous: false
                fillMode: Image.PreserveAspectFit
                smooth: false
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 34
                color: Qt.rgba(theme.panelColor.r, theme.panelColor.g, theme.panelColor.b, 0.92)

                Text {
                    anchors.centerIn: parent
                    text: root.exportWidth + " × " + root.exportHeight
                    color: theme.textColor
                    font.bold: true
                    font.pixelSize: 12
                }
            }
        }

        ColumnLayout {
            id: settingsColumn
            Layout.fillWidth: true
            Layout.minimumWidth: 280
            Layout.alignment: Qt.AlignTop
            spacing: 10

            MintLabel {
                text: "Image Size"
                font.bold: true
                font.pixelSize: 14
                visible: !root.textFormat
            }

            GridLayout {
                Layout.fillWidth: true
                visible: !root.textFormat
                columns: 2
                columnSpacing: 10
                rowSpacing: 7

                MintLabel {
                    text: "Source"
                    color: theme.mutedTextColor
                }
                MintLabel {
                    text: root.sourceWidth + " × " + root.sourceHeight + " px"
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight
                }

                MintLabel {
                    text: "Current output (1×)"
                    color: theme.mutedTextColor
                }
                MintLabel {
                    text: root.baseWidth + " × " + root.baseHeight + " px"
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight
                }

                MintLabel { text: "Scale" }
                MintComboBox {
                    id: scaleCombo
                    Layout.fillWidth: true
                    model: ["25%", "50%", "100%", "200%", "300%", "400%", "Custom"]
                    currentIndex: 2
                    onActivated: {
                        var scales = [0.25, 0.5, 1.0, 2.0, 3.0, 4.0]
                        if (currentIndex >= 0 && currentIndex < scales.length)
                            root.applyScale(scales[currentIndex])
                    }
                }

                MintLabel { text: "Width" }
                RowLayout {
                    Layout.fillWidth: true
                    MintTextField {
                        id: widthInput
                        Layout.fillWidth: true
                        horizontalAlignment: TextInput.AlignRight
                        inputMethodHints: Qt.ImhDigitsOnly
                        validator: IntValidator { bottom: 1; top: 32768 }
                        onEditingFinished: root.commitWidth()
                        onAccepted: root.commitWidth()
                    }
                    MintLabel {
                        text: "px"
                        color: theme.mutedTextColor
                    }
                }

                MintLabel { text: "Height" }
                RowLayout {
                    Layout.fillWidth: true
                    MintTextField {
                        id: heightInput
                        Layout.fillWidth: true
                        horizontalAlignment: TextInput.AlignRight
                        inputMethodHints: Qt.ImhDigitsOnly
                        validator: IntValidator { bottom: 1; top: 32768 }
                        onEditingFinished: root.commitHeight()
                        onAccepted: root.commitHeight()
                    }
                    MintLabel {
                        text: "px"
                        color: theme.mutedTextColor
                    }
                }
            }

            MintCheckBox {
                id: aspectLock
                text: "Lock aspect ratio"
                checked: true
                visible: !root.textFormat
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: theme.borderColor
                visible: !root.textFormat
            }

            MintLabel {
                text: "Export Settings"
                font.bold: true
                font.pixelSize: 14
            }

            RowLayout {
                Layout.fillWidth: true
                MintLabel {
                    text: "Format"
                    Layout.preferredWidth: 90
                }
                MintComboBox {
                    id: formatCombo
                    Layout.fillWidth: true
                    model: root.sourceHasAsciiLayer ? ["PNG", "JPEG", "WebP", "TIFF", "SVG", "TXT"] : ["PNG", "JPEG", "WebP", "TIFF", "SVG"]
                    currentIndex: 0
                    onActivated: {
                        if (root.textFormat || !root.transparencySupported)
                            preserveTransparencyCheck.checked = false
                        else if (root.sourceHasTransparency)
                            preserveTransparencyCheck.checked = true
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: !root.textFormat
                MintLabel {
                    text: "Resampling"
                    Layout.preferredWidth: 90
                }
                MintComboBox {
                    id: resampleCombo
                    Layout.fillWidth: true
                    model: ["Nearest (pixel-perfect)", "Bilinear", "Bicubic", "Lanczos"]
                    currentIndex: 0
                }
            }

            MintCheckBox {
                id: preserveTransparencyCheck
                text: "Preserve source transparency"
                checked: false
                visible: !root.textFormat
                enabled: root.sourceHasTransparency && root.transparencySupported
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: root.lossyFormat
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true
                    MintLabel {
                        text: "Quality"
                        Layout.fillWidth: true
                    }
                    MintLabel {
                        text: String(root.exportQuality)
                        color: theme.mutedTextColor
                    }
                }

                MintSlider {
                    Layout.fillWidth: true
                    from: 1
                    to: 100
                    stepSize: 1
                    value: root.exportQuality
                    onUserMoved: function(newValue) {
                        root.exportQuality = Math.round(newValue)
                    }
                }
            }

            MintLabel {
                Layout.fillWidth: true
                text: root.textFormat
                      ? "TXT exports the actual character grid from the last enabled ASCII / Glyph layer as UTF-8 text."
                      : (resampleCombo.currentIndex === 0
                         ? "Nearest keeps hard pixel edges when scaling. Use Lanczos for photographic output."
                         : "Scaling happens after RasterMint finishes processing, so your effect settings stay unchanged.")
                color: theme.mutedTextColor
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }

            Item { Layout.preferredHeight: 2 }

            RowLayout {
                Layout.fillWidth: true
                MintButton {
                    text: "Cancel"
                    onClicked: root.close()
                }
                Item { Layout.fillWidth: true }
                MintButton {
                    text: "Reset to 100%"
                    visible: !root.textFormat
                    onClicked: {
                        scaleCombo.currentIndex = 2
                        root.applyScale(1.0)
                    }
                }
                MintButton {
                    text: "Export…"
                    selected: true
                    onClicked: root.openExportFileDialog()
                }
            }
        }
        }
    }

    FileDialog {
        id: exportFileDialog
        title: "Export image"
        fileMode: FileDialog.SaveFile
        defaultSuffix: root.selectedFormat === "JPEG" ? "jpg"
                       : root.selectedFormat === "TIFF" ? "tif"
                       : root.selectedFormat === "TXT" ? "txt"
                       : root.selectedFormat.toLowerCase()
        nameFilters: root.selectedFormat === "PNG" ? ["PNG (*.png)"]
                   : root.selectedFormat === "JPEG" ? ["JPEG (*.jpg *.jpeg)"]
                   : root.selectedFormat === "WebP" ? ["WebP (*.webp)"]
                   : root.selectedFormat === "TIFF" ? ["TIFF (*.tif *.tiff)"]
                   : root.selectedFormat === "SVG" ? ["SVG (*.svg)"]
                   : ["Text (*.txt)"]

        onAccepted: {
            backend.exportImageWithOptions(root.urlNormalizer(selectedFile), root.exportOptions())
            root.close()
        }
    }
}
