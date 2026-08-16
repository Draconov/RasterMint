import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Dialog {
    id: root
    title: "RasterMint Settings"
    modal: true
    width: 420
    height: 260
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.NoButton
    background: Rectangle { color: theme.panelColor; border.color: theme.borderColor; radius: 10 }
    header: Rectangle {
        implicitHeight: 48; color: theme.panelRaisedColor
        Text { anchors { left: parent.left; verticalCenter: parent.verticalCenter; leftMargin: 16 }; text: root.title; color: theme.textColor; font.bold: true; font.pixelSize: 16 }
    }
    contentItem: ColumnLayout {
        spacing: 12
        MintLabel { text: "Appearance"; font.bold: true }
        MintLabel { text: "Theme"; color: theme.mutedTextColor }
        MintComboBox {
            id: themeChooser
            Layout.fillWidth: true
            model: theme.themeNames
            Component.onCompleted: currentIndex = Math.max(0, theme.themeIds.indexOf(theme.themeId))
            onActivated: theme.setTheme(theme.themeIds[currentIndex])
        }
        MintLabel { Layout.fillWidth: true; text: "Themes apply immediately. RasterMint Dark is the default."; color: theme.mutedTextColor; wrapMode: Text.WordWrap }
        Item { Layout.fillHeight: true }
        RowLayout {
            Layout.fillWidth: true
            MintButton { text: "Close"; onClicked: root.close() }
            Item { Layout.fillWidth: true }
            MintButton { text: "Reset Settings"; onClicked: { theme.resetTheme(); backend.resetSettings(); themeChooser.currentIndex = Math.max(0, theme.themeIds.indexOf(theme.themeId)) } }
        }
    }
}
