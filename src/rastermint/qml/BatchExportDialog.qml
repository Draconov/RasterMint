import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "components"

Dialog {
    id: root
    title: qsTr("Batch Export Images")
    modal: true
    popupType: Popup.Item
    standardButtons: Dialog.NoButton
    padding: 18

    property var selectedFiles: []
    property string outputFolder: ""
    property var urlNormalizer: function(value) { return value ? value.toString() : "" }
    property var urlsNormalizer: function(values) {
        var result = []
        for (var i = 0; i < values.length; ++i)
            result.push(root.urlNormalizer(values[i]))
        return result
    }
    readonly property real overlayWidth: Overlay.overlay ? Overlay.overlay.width : 760
    readonly property real overlayHeight: Overlay.overlay ? Overlay.overlay.height : 820
    readonly property real desiredDialogHeight: 46 + (padding * 2) + batchBody.implicitHeight
    readonly property bool canStart: selectedFiles.length > 0 && outputFolder.length > 0
    readonly property var resamplingValues: ["Nearest (pixel-perfect)", "Bilinear", "Bicubic", "Lanczos"]
    readonly property bool transparencySupported: formatCombo.currentText === "PNG"
                                               || formatCombo.currentText === "WEBP"
                                               || formatCombo.currentText === "TIFF"
    width: Math.max(520, Math.min(680, overlayWidth - 24))
    height: Math.max(420, Math.min(Math.max(480, desiredDialogHeight), overlayHeight - 24))
    anchors.centerIn: Overlay.overlay

    background: Rectangle {
        color: theme.panelColor
        border.color: theme.borderColor
        border.width: 1
        radius: 10
    }

    Overlay.modal: Rectangle {
        color: Qt.rgba(0, 0, 0, 0.45)
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
            text: root.title
            color: theme.textColor
            font.bold: true
            font.pixelSize: 13
        }
    }

    function startExport() {
        if (!canStart)
            return
        var overwriteMode = "auto-rename"
        if (overwriteCombo.currentIndex === 1)
            overwriteMode = "replace"
        else if (overwriteCombo.currentIndex === 2)
            overwriteMode = "skip"
        backend.batchExportWithOptions(
            selectedFiles,
            outputFolder,
            {
                format: formatCombo.currentText,
                scalePercent: scaleSpin.value,
                overwrite: overwriteMode,
                resampling: root.resamplingValues[resampleCombo.currentIndex],
                preserveTransparency: preserveTransparencyCheck.checked
                                      && root.transparencySupported
            }
        )
        close()
    }

    contentItem: ScrollView {
        id: batchScroll
        clip: true
        contentWidth: availableWidth
        contentHeight: batchBody.implicitHeight

        ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AlwaysOff }
        ScrollBar.vertical: ScrollBar {
            policy: batchScroll.contentHeight > batchScroll.availableHeight
                    ? ScrollBar.AsNeeded
                    : ScrollBar.AlwaysOff
        }

        ColumnLayout {
            id: batchBody
            width: batchScroll.availableWidth
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                color: theme.panelRaisedColor
                border.color: theme.borderColor
                radius: 8
                implicitHeight: sourceBlock.implicitHeight + 16

                ColumnLayout {
                    id: sourceBlock
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    MintLabel {
                        text: qsTr("Sources and destination")
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        MintButton {
                            text: qsTr("Choose Images")
                            onClicked: filesDialog.open()
                        }
                        MintLabel {
                            Layout.fillWidth: true
                            text: selectedFiles.length === 1
                                  ? qsTr("1 image selected")
                                  : (selectedFiles.length > 1
                                     ? qsTr("%1 images selected").arg(selectedFiles.length)
                                     : qsTr("No images selected"))
                            wrapMode: Text.Wrap
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        MintButton {
                            text: qsTr("Choose Output Folder")
                            onClicked: folderDialog.open()
                        }
                        MintLabel {
                            Layout.fillWidth: true
                            text: outputFolder.length > 0
                                  ? outputFolder
                                  : qsTr("No output folder selected")
                            wrapMode: Text.WrapAnywhere
                            color: outputFolder.length > 0 ? theme.textColor : theme.mutedTextColor
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                color: theme.panelRaisedColor
                border.color: theme.borderColor
                radius: 8
                implicitHeight: optionsBlock.implicitHeight + 16

                ColumnLayout {
                    id: optionsBlock
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 10

                    MintLabel {
                        text: qsTr("Batch export options")
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        MintLabel { text: qsTr("Format"); Layout.preferredWidth: 140 }
                        MintComboBox {
                            id: formatCombo
                            Layout.fillWidth: true
                            model: ["PNG", "JPEG", "WEBP", "TIFF", "BMP"]
                            currentIndex: 0
                            onActivated: {
                                preserveTransparencyCheck.checked = root.transparencySupported
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        MintLabel { text: qsTr("Scale (%)"); Layout.preferredWidth: 140 }
                        MintSpinBox {
                            id: scaleSpin
                            from: 10
                            to: 800
                            stepSize: 10
                            editable: true
                            value: 100
                            Layout.fillWidth: true
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        MintLabel { text: qsTr("Resampling"); Layout.preferredWidth: 140 }
                        MintComboBox {
                            id: resampleCombo
                            Layout.fillWidth: true
                            model: [qsTr("Nearest (pixel-perfect)"), qsTr("Bilinear"), qsTr("Bicubic"), qsTr("Lanczos")]
                            currentIndex: 0
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        MintLabel { text: qsTr("Transparency"); Layout.preferredWidth: 140 }
                        MintCheckBox {
                            id: preserveTransparencyCheck
                            text: qsTr("Preserve source transparency")
                            checked: true
                            enabled: root.transparencySupported
                            Layout.fillWidth: true
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        MintLabel { text: qsTr("Overwrite"); Layout.preferredWidth: 140 }
                        MintComboBox {
                            id: overwriteCombo
                            Layout.fillWidth: true
                            model: [qsTr("Auto rename"), qsTr("Replace existing"), qsTr("Skip existing")]
                            currentIndex: 0
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                MintButton {
                    text: qsTr("Cancel")
                    onClicked: root.close()
                }
                MintButton {
                    text: qsTr("Start Batch Export")
                    enabled: root.canStart
                    onClicked: root.startExport()
                }
            }
        }
    }

    FileDialog {
        id: filesDialog
        title: qsTr("Select images for batch processing")
        fileMode: FileDialog.OpenFiles
        nameFilters: [qsTr("Images") + " (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)"]
        onAccepted: root.selectedFiles = root.urlsNormalizer(selectedFiles)
    }

    FolderDialog {
        id: folderDialog
        title: qsTr("Choose batch output folder")
        onAccepted: root.outputFolder = root.urlNormalizer(selectedFolder)
    }
}
