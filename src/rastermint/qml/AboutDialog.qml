import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Dialog {
    id: root
    title: "About RasterMint"
    modal: true
    popupType: Popup.Item
    width: 430
    height: 265
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

    // The default Qt Quick Controls dialog header uses style colors. Keeping a
    // RasterMint-owned header prevents a light/default strip from leaking into
    // dark themes and keeps the whole dialog live-bound to the active theme.
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

    contentItem: ColumnLayout {
        spacing: 10
        Item { Layout.fillHeight: true }
        MintLabel { Layout.alignment: Qt.AlignHCenter; text: "RasterMint " + backend.version; font.bold: true; font.pixelSize: 20 }
        MintLabel { Layout.alignment: Qt.AlignHCenter; text: "Developed by Draconov · 2026"; color: theme.mutedTextColor }
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: '<a href="https://github.com/Draconov/RasterMint">github.com/Draconov/RasterMint</a>'
            color: theme.accentColor
            linkColor: theme.accentColor
            textFormat: Text.RichText
            onLinkActivated: function(link) { Qt.openUrlExternally(link) }
            HoverHandler { cursorShape: Qt.PointingHandCursor }
        }
        Item { Layout.fillHeight: true }
        MintButton { Layout.alignment: Qt.AlignHCenter; text: "Close"; onClicked: root.close() }
    }
}
