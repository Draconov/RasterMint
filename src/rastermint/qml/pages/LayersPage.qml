import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    property int addIndex: 0
    ColumnLayout {
        anchors.fill: parent
        spacing: 8
        RowLayout {
            Layout.fillWidth: true
            MintLabel { text: "Layers"; font.bold: true; font.pixelSize: 15; Layout.fillWidth: true }
            MintButton {
                id: addLayerButton
                objectName: "addLayerButton"
                text: "+"
                onClicked: {
                    var point = addLayerButton.mapToItem(Overlay.overlay, 0, addLayerButton.height + 4)
                    addPopup.x = Math.max(4, Math.min(point.x - addPopup.width + addLayerButton.width, Overlay.overlay.width - addPopup.width - 4))
                    addPopup.y = Math.max(4, Math.min(point.y, Overlay.overlay.height - addPopup.height - 4))
                    addPopup.open()
                }
            }
        }
        ListView {
            id: layerList
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, 260)
            model: backend.layerModel
            spacing: 4
            clip: true
            currentIndex: backend.selectedLayerIndex
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOff }
            delegate: Rectangle {
                width: layerList.width
                height: 48
                radius: 7
                color: index === backend.selectedLayerIndex ? theme.selectionColor : (layerHover.hovered ? theme.panelHoverColor : theme.panelRaisedColor)
                border.color: theme.borderColor
                RowLayout {
                    anchors.fill: parent; anchors.margins: 7; spacing: 7
                    MintCheckBox { checked: layerEnabled; onToggled: backend.setLayerEnabled(index, checked) }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 1
                        Text { Layout.fillWidth: true; text: kind; color: theme.textColor; font.bold: true; elide: Text.ElideRight }
                        Text { Layout.fillWidth: true; text: summary; color: theme.mutedTextColor; font.pixelSize: 10; elide: Text.ElideRight }
                    }
                    MintButton { text: "↑"; enabled: index > 0; onClicked: backend.moveLayer(index, index - 1) }
                    MintButton { text: "↓"; enabled: index < layerList.count - 1; onClicked: backend.moveLayer(index, index + 1) }
                }
                HoverHandler { id: layerHover }
                TapHandler { onTapped: backend.selectLayer(index) }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            MintButton { Layout.fillWidth: true; text: "Duplicate"; onClicked: backend.duplicateLayer(backend.selectedLayerIndex) }
            MintButton { Layout.fillWidth: true; text: "Remove"; onClicked: backend.removeLayer(backend.selectedLayerIndex) }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
        MintLabel { text: backend.selectedLayerName; font.bold: true }
        ScrollView {
            id: paramScroll
            Layout.fillWidth: true; Layout.fillHeight: true
            contentWidth: availableWidth
            ScrollBar.vertical.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                width: paramScroll.availableWidth
                spacing: 8
                Repeater {
                    model: backend.selectedLayerParams
                    delegate: Loader {
                        Layout.fillWidth: true
                        property var param: modelData
                        sourceComponent: param.type === "bool" ? boolEditor : param.type === "choice" ? choiceEditor : param.type === "text" || param.type === "file" || param.type === "color" ? textEditor : numberEditor
                    }
                }
            }
        }
    }

    property var expandedEffectCategories: ({})

    function effectCategoryExpanded(name) {
        return Boolean(expandedEffectCategories[name])
    }

    function toggleEffectCategory(name) {
        var next = {}
        for (var key in expandedEffectCategories)
            next[key] = expandedEffectCategories[key]
        next[name] = !Boolean(next[name])
        expandedEffectCategories = next
    }

    Popup {
        id: addPopup
        popupType: Popup.Item
        parent: Overlay.overlay
        width: 300
        height: Math.max(120, Math.min(500, categoryColumn.implicitHeight + 10, Overlay.overlay.height - y - 4))
        padding: 5
        background: Rectangle { color: theme.panelRaisedColor; border.color: theme.borderColor; radius: 8 }

        contentItem: ScrollView {
            id: categoryScroll
            clip: true
            contentWidth: availableWidth
            ScrollBar.vertical.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                id: categoryColumn
                width: categoryScroll.availableWidth
                spacing: 3

                Repeater {
                    model: backend.layerCategories
                    delegate: ColumnLayout {
                        id: categoryDelegate
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 2

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 36
                            radius: 5
                            color: categoryMouse.containsMouse ? theme.selectionColor : theme.panelRaisedColor

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 7
                                Text {
                                    text: root.effectCategoryExpanded(categoryDelegate.modelData.name) ? "▾" : "▸"
                                    color: theme.accentColor
                                    font.pixelSize: 13
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: categoryDelegate.modelData.name
                                    color: theme.textColor
                                    font.bold: true
                                    verticalAlignment: Text.AlignVCenter
                                }
                                Text {
                                    text: String(categoryDelegate.modelData.effects.length)
                                    color: theme.mutedTextColor
                                    font.pixelSize: 10
                                }
                            }
                            MouseArea {
                                id: categoryMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: root.toggleEffectCategory(categoryDelegate.modelData.name)
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1
                            visible: root.effectCategoryExpanded(categoryDelegate.modelData.name)
                            Repeater {
                                model: categoryDelegate.modelData.effects
                                delegate: ItemDelegate {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: 32
                                    leftPadding: 28
                                    contentItem: Text {
                                        text: parent.modelData
                                        color: theme.textColor
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                    }
                                    background: Rectangle {
                                        radius: 5
                                        color: parent.hovered ? theme.selectionColor : "transparent"
                                    }
                                    onClicked: {
                                        backend.addLayer(modelData)
                                        addPopup.close()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: boolEditor
        MintCheckBox {
            text: param.label + (param.animated ? "  · animated" : "")
            checked: Boolean(param.value)
            enabled: !param.animated
            onToggled: backend.setLayerParam(param.key, checked)
        }
    }
    Component {
        id: choiceEditor
        ColumnLayout {
            spacing: 4
            MintLabel { text: param.label; color: theme.mutedTextColor }
            MintComboBox {
                Layout.fillWidth: true; model: param.options; enabled: !param.animated
                Component.onCompleted: currentIndex = Math.max(0, param.options.indexOf(String(param.value)))
                onActivated: backend.setLayerParam(param.key, currentText)
            }
        }
    }
    Component {
        id: textEditor
        ColumnLayout {
            spacing: 4
            MintLabel { text: param.label; color: theme.mutedTextColor }
            MintTextField { Layout.fillWidth: true; text: String(param.value); enabled: !param.animated; onEditingFinished: backend.setLayerParam(param.key, text) }
        }
    }
    Component {
        id: numberEditor
        ColumnLayout {
            spacing: 4
            RowLayout {
                Layout.fillWidth: true
                MintLabel { text: param.label + (param.animated ? "  · animated" : ""); color: theme.mutedTextColor; Layout.fillWidth: true }
                MintLabel { text: Number(param.value).toFixed(param.decimals !== undefined ? param.decimals : 0) + (param.suffix || "") }
            }
            MintSlider {
                Layout.fillWidth: true
                enabled: !param.animated
                from: Number(param.min)
                to: Number(param.max)
                stepSize: Number(param.step || 1)
                value: Number(param.value)
                onPressedChanged: {
                    if (pressed)
                        backend.beginHistoryGroup(backend.selectedLayerName + " · " + param.label)
                    else
                        backend.endHistoryGroup()
                }
                onMoved: backend.setLayerParam(param.key, value)
            }
        }
    }
}
