import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Dialog {
    id: root
    title: qsTr("Settings")
    modal: true
    popupType: Popup.Item
    // Localized labels can be substantially longer than English. Use the
    // available application width instead of forcing the old 460 px dialog,
    // while still keeping the settings window compact on large screens.
    width: Math.min(620, Math.max(420, Overlay.overlay ? Overlay.overlay.width - 32 : 560))
    height: Math.min(680, Overlay.overlay ? Overlay.overlay.height - 32 : 680)
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.NoButton
    padding: 16

    function resetWindowSettings() {
        theme.resetTheme()
        localization.resetLanguage()
        backend.historyLimit = 50
        backend.setLayerCacheEnabled(true)
        backend.setLayerCacheMegabytes(192)
        backend.setTiledProcessingEnabled(true)
        backend.setProcessingTileSize(1024)
        themeChooser.syncThemeIndex()
        languageChooser.rebuildLanguageMenu()
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

    contentItem: ScrollView {
        id: settingsScroll
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AsNeeded
        contentWidth: availableWidth

        ColumnLayout {
            width: settingsScroll.availableWidth
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

            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: theme.borderColor }
            MintLabel { text: qsTr("Performance"); font.bold: true }

            RowLayout {
                Layout.fillWidth: true
                MintCheckBox {
                    checked: backend.layerCacheEnabled
                    onToggled: backend.setLayerCacheEnabled(checked)
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1
                    MintLabel { text: qsTr("Per-layer preview cache") }
                    MintLabel {
                        Layout.fillWidth: true
                        text: qsTr("Reuses unchanged layers when editing a later layer.")
                        color: theme.mutedTextColor
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                enabled: backend.layerCacheEnabled
                MintLabel { text: qsTr("Cache memory budget"); Layout.fillWidth: true }
                MintTextField {
                    id: cacheBudgetInput
                    Layout.preferredWidth: 72
                    horizontalAlignment: TextInput.AlignHCenter
                    validator: IntValidator { bottom: 64; top: 2048 }
                    text: String(backend.layerCacheMegabytes)
                    onEditingFinished: {
                        var value = Math.max(64, Math.min(2048, parseInt(text, 10) || backend.layerCacheMegabytes))
                        backend.setLayerCacheMegabytes(value)
                        text = String(backend.layerCacheMegabytes)
                    }
                }
                MintLabel { text: qsTr("MB"); color: theme.mutedTextColor }
            }
            MintSlider {
                Layout.fillWidth: true
                enabled: backend.layerCacheEnabled
                from: 64; to: 2048; stepSize: 32
                value: backend.layerCacheMegabytes
                onUserMoved: function(newValue) { backend.setLayerCacheMegabytes(Math.round(newValue / 32) * 32) }
            }

            RowLayout {
                Layout.fillWidth: true
                MintCheckBox {
                    checked: backend.tiledProcessingEnabled
                    onToggled: backend.setTiledProcessingEnabled(checked)
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1
                    MintLabel { text: qsTr("Memory-safe large-image tiling") }
                    MintLabel {
                        Layout.fillWidth: true
                        text: qsTr("Automatically tiles very large images when the current stack can be processed identically tile-by-tile.")
                        color: theme.mutedTextColor
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                }
                MintComboBox {
                    Layout.preferredWidth: 96
                    enabled: backend.tiledProcessingEnabled
                    model: ["256", "512", "1024", "2048", "4096"]
                    Component.onCompleted: currentIndex = Math.max(0, model.indexOf(String(backend.processingTileSize)))
                    onActivated: backend.setProcessingTileSize(parseInt(currentText, 10))
                }
            }

            RowLayout {
                Layout.fillWidth: true
                MintButton { text: qsTr("Clear Layer Cache"); enabled: backend.layerCacheEnabled; onClicked: backend.clearLayerCache() }
                MintButton { text: qsTr("Benchmark Current Stack"); enabled: backend.hasSource; onClicked: backend.benchmarkCurrentStack() }
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.benchmarkSummary.length > 0
                text: backend.benchmarkSummary
                color: theme.mutedTextColor
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            Connections {
                target: backend
                function onPerformanceSettingsChanged() {
                    if (!cacheBudgetInput.activeFocus)
                        cacheBudgetInput.text = String(backend.layerCacheMegabytes)
                }
            }
        }
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
