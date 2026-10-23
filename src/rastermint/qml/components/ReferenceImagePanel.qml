import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    objectName: "referenceImagePanel"
    property var chooseReference: function() {}
    property real zoom: 1.0
    readonly property real fitScale: imagePreview.implicitWidth > 0 && imagePreview.implicitHeight > 0
                                      ? Math.min(referenceFlick.width / imagePreview.implicitWidth,
                                                 referenceFlick.height / imagePreview.implicitHeight)
                                      : 1.0

    color: theme.panelColor
    border.color: theme.borderColor
    border.width: 1
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            Text {
                Layout.fillWidth: true
                text: qsTr("Reference Image")
                color: theme.textColor
                font.bold: true
                font.pixelSize: 13
                elide: Text.ElideRight
            }
            MintButton {
                text: qsTr("Open…")
                onClicked: root.chooseReference()
            }
            MintButton {
                text: "×"
                MintToolTip {
                    visible: parent.hovered
                    text: qsTr("Hide reference")
                }
                onClicked: backend.setReferenceVisible(false)
            }
        }
        Text {
            Layout.fillWidth: true
            visible: backend.referenceImagePath.length > 0
            text: backend.referenceImagePath.split(/[\\/]/).pop()
            color: theme.mutedTextColor
            font.pixelSize: 10
            elide: Text.ElideMiddle
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 5
            color: theme.canvasColor
            border.color: theme.borderColor
            clip: true

            Text {
                anchors.centerIn: parent
                visible: backend.referenceImagePath.length === 0
                text: qsTr("Open an image to use as reference")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                width: parent.width - 20
            }

            Flickable {
                id: referenceFlick
                anchors.fill: parent
                anchors.margins: 4
                visible: backend.referenceImagePath.length > 0
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: Math.max(width, imagePreview.implicitWidth * root.fitScale * root.zoom)
                contentHeight: Math.max(height, imagePreview.implicitHeight * root.fitScale * root.zoom)

                Image {
                    id: imagePreview
                    source: backend.referenceImagePath.length > 0
                            ? "image://rastermint/reference?revision=" + backend.referenceRevision
                            : ""
                    cache: false
                    asynchronous: true
                    smooth: false
                    fillMode: Image.PreserveAspectFit
                    width: referenceFlick.contentWidth
                    height: referenceFlick.contentHeight
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            MintButton {
                text: "−"
                onClicked: root.zoom = Math.max(0.25, root.zoom / 1.25)
            }
            Text {
                Layout.fillWidth: true
                text: Math.round(root.zoom * 100) + "%"
                color: theme.mutedTextColor
                horizontalAlignment: Text.AlignHCenter
            }
            MintButton {
                text: "+"
                onClicked: root.zoom = Math.min(6.0, root.zoom * 1.25)
            }
            MintButton {
                text: qsTr("Clear")
                enabled: backend.referenceImagePath.length > 0
                onClicked: backend.clearReferenceImage()
            }
        }
    }
}
