import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Dialog {
    id: root
    title: "Settings"
    modal: true
    popupType: Popup.Item
    width: 420
    height: 310
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.NoButton
    padding: 16

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
            font.pixelSize: 15
        }
    }

    contentItem: ColumnLayout {
        spacing: 12

        MintLabel {
            text: "Appearance"
            font.bold: true
        }
        MintComboBox {
            id: themeChooser
            Layout.fillWidth: true
            model: theme.themeNames
            Component.onCompleted: syncThemeIndex()

            function syncThemeIndex() {
                currentIndex = Math.max(0, theme.themeIds.indexOf(theme.themeId))
            }

            onActivated: {
                theme.setTheme(theme.themeIds[currentIndex])
                backend.reportAction("Theme: " + currentText)
            }
            Connections {
                target: theme
                function onThemeChanged() { themeChooser.syncThemeIndex() }
            }
        }

        MintLabel {
            text: "History"
            font.bold: true
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            MintLabel {
                text: "Undo history"
                Layout.fillWidth: true
            }
            MintSpinBox {
                id: historyLimit
                from: 10
                to: 200
                stepSize: 10
                value: backend.historyLimit
                onValueModified: backend.historyLimit = value
            }
            MintLabel {
                text: "actions"
                color: theme.mutedTextColor
            }
        }
        MintLabel {
            Layout.fillWidth: true
            text: "Keep 10–200 undo steps. Higher values retain more editing history."
            color: theme.mutedTextColor
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }

        Item { Layout.fillHeight: true }
        RowLayout {
            Layout.fillWidth: true
            MintButton { text: "Close"; onClicked: root.close() }
            Item { Layout.fillWidth: true }
            MintButton {
                text: "Reset Settings"
                onClicked: {
                    theme.resetTheme()
                    backend.resetSettings()
                    themeChooser.syncThemeIndex()
                }
            }
        }
    }
}
