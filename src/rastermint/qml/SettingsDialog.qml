import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Dialog {
    id: root
    title: qsTr("Settings")
    modal: true
    popupType: Popup.Item
    width: 420
    height: 470
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.NoButton
    padding: 16

    function resetWindowSettings() {
        theme.resetTheme()
        localization.resetLanguage()
        backend.historyLimit = 50
        themeChooser.syncThemeIndex()
        languageChooser.syncLanguageIndex()
    }

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
            text: qsTr("Appearance")
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
                backend.reportAction(qsTr("Theme: %1").arg(currentText))
            }
            Connections {
                target: theme
                function onThemeChanged() { themeChooser.syncThemeIndex() }
            }
        }

        MintLabel {
            text: qsTr("Language")
            font.bold: true
        }
        MintComboBox {
            id: languageChooser
            Layout.fillWidth: true
            separatorToken: "__language_separator__"
            property var menuLanguageIds: []
            Component.onCompleted: rebuildLanguageMenu()

            function rebuildLanguageMenu() {
                var ids = localization.languageIds
                var names = localization.languageNames
                var activeIndex = ids.indexOf(localization.languageId)
                if (activeIndex < 0)
                    activeIndex = 0

                var nextIds = [ids[activeIndex], ""]
                var nextNames = [names[activeIndex], separatorToken]
                for (var i = 0; i < ids.length; ++i) {
                    if (i === activeIndex)
                        continue
                    nextIds.push(ids[i])
                    nextNames.push(names[i])
                }

                menuLanguageIds = nextIds
                model = nextNames
                currentIndex = 0
            }
            onActivated: {
                var selectedId = menuLanguageIds[currentIndex]
                if (!selectedId) {
                    currentIndex = 0
                    return
                }
                var selectedName = currentText
                localization.setLanguage(selectedId)
                backend.reportAction(qsTr("Language: %1").arg(selectedName))
            }
            Connections {
                target: localization
                function onLanguageChanged() { languageChooser.rebuildLanguageMenu() }
            }
        }

        MintLabel {
            text: qsTr("History")
            font.bold: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            MintLabel {
                text: qsTr("Undo history")
                Layout.fillWidth: true
            }
            MintTextField {
                id: historyLimitInput
                Layout.preferredWidth: 62
                horizontalAlignment: TextInput.AlignHCenter
                inputMethodHints: Qt.ImhDigitsOnly
                validator: IntValidator { bottom: 10; top: 200 }
                text: String(backend.historyLimit)
                function commitValue() {
                    var parsed = parseInt(text, 10)
                    if (isNaN(parsed))
                        parsed = backend.historyLimit
                    parsed = Math.max(10, Math.min(200, parsed))
                    backend.historyLimit = parsed
                    text = String(backend.historyLimit)
                }
                onEditingFinished: commitValue()
            }
            MintLabel {
                text: qsTr("actions")
                color: theme.mutedTextColor
            }
        }
        MintSlider {
            id: historyLimitSlider
            Layout.fillWidth: true
            from: 10
            to: 200
            stepSize: 1
            snapMode: Slider.SnapAlways
            value: backend.historyLimit
            onUserMoved: function(newValue) { backend.historyLimit = Math.round(newValue) }
        }
        RowLayout {
            Layout.fillWidth: true
            MintLabel {
                text: "10"
                color: theme.mutedTextColor
                font.pixelSize: 10
            }
            Item { Layout.fillWidth: true }
            MintLabel {
                text: "200"
                color: theme.mutedTextColor
                font.pixelSize: 10
            }
        }
        MintLabel {
            Layout.fillWidth: true
            text: qsTr("Keep 10–200 undo steps. Higher values retain more editing history and use more memory.")
            color: theme.mutedTextColor
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
        Connections {
            target: backend
            function onHistoryLimitChanged() {
                if (!historyLimitInput.activeFocus)
                    historyLimitInput.text = String(backend.historyLimit)
            }
        }

        Item { Layout.fillHeight: true }
    }

    footer: Item {
        implicitHeight: 58

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.bottomMargin: 10
            spacing: 6

            MintButton { text: qsTr("Close"); onClicked: root.close() }
            Item { Layout.fillWidth: true }
            MintButton {
                text: qsTr("Reset Settings")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Reset only the options shown in this Settings window")
                onClicked: root.resetWindowSettings()
            }
            MintButton {
                text: qsTr("Full Reset")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Reset RasterMint processing and app settings to defaults")
                onClicked: {
                    root.resetWindowSettings()
                    backend.resetSettings()
                }
            }
        }
    }
}
