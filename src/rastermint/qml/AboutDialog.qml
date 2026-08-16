import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Dialog {
    id: root
    title: "About RasterMint"
    modal: true
    width: 430
    height: 250
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.NoButton
    background: Rectangle { color: theme.panelColor; border.color: theme.borderColor; radius: 10 }
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
