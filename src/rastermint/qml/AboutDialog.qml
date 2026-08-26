import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Dialog {
    id: root
    title: qsTr("About RasterMint")
    modal: true
    popupType: Popup.Item

    readonly property real overlayWidth: Overlay.overlay ? Overlay.overlay.width : 520
    readonly property real overlayHeight: Overlay.overlay ? Overlay.overlay.height : 420
    readonly property real desiredDialogHeight: 46 + (padding * 2) + aboutBody.implicitHeight

    width: Math.max(320, Math.min(430, overlayWidth - 24))
    height: Math.max(220, Math.min(Math.max(265, desiredDialogHeight), overlayHeight - 24))
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.NoButton
    padding: 18

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

    contentItem: ScrollView {
        id: aboutScroll
        clip: true
        contentWidth: availableWidth
        contentHeight: aboutBody.implicitHeight

        ScrollBar.horizontal: ScrollBar {
            policy: ScrollBar.AlwaysOff
        }
        ScrollBar.vertical: ScrollBar {
            policy: aboutScroll.contentHeight > aboutScroll.availableHeight
                    ? ScrollBar.AsNeeded
                    : ScrollBar.AlwaysOff
        }

        ColumnLayout {
            id: aboutBody
            width: aboutScroll.availableWidth
            spacing: 10

            Item { Layout.preferredHeight: 8 }

            MintLabel {
                Layout.alignment: Qt.AlignHCenter
                text: qsTr("RasterMint ") + backend.version
                font.bold: true
                font.pixelSize: 20
            }

            MintLabel {
                Layout.alignment: Qt.AlignHCenter
                text: qsTr("Developed by Draconov · 2026")
                color: theme.mutedTextColor
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: '<a href="https://github.com/Draconov/RasterMint">github.com/Draconov/RasterMint</a>'
                color: theme.accentColor
                linkColor: theme.accentColor
                textFormat: Text.RichText
                onLinkActivated: function(link) { Qt.openUrlExternally(link) }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
            }

            Item { Layout.preferredHeight: 8 }

            MintButton {
                Layout.alignment: Qt.AlignHCenter
                text: qsTr("Close")
                onClicked: root.close()
            }
        }
    }
}
