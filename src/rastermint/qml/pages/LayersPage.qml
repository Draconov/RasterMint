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
            MintButton { text: "+"; onClicked: addPopup.open() }
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
            Layout.fillWidth: true; Layout.fillHeight: true
            ScrollBar.vertical.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                width: parent.width
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

    Popup {
        id: addPopup
        width: 250; height: Math.min(440, addList.contentHeight + 10); padding: 5
        background: Rectangle { color: theme.panelRaisedColor; border.color: theme.borderColor; radius: 8 }
        contentItem: ListView {
            id: addList; model: backend.layerKinds; clip: true
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOff }
            delegate: ItemDelegate {
                width: addList.width; height: 32
                contentItem: Text { text: modelData; color: theme.textColor; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { radius: 5; color: parent.hovered ? theme.selectionColor : "transparent" }
                onClicked: { backend.addLayer(modelData); addPopup.close() }
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
            Slider {
                Layout.fillWidth: true
                enabled: !param.animated
                from: Number(param.min); to: Number(param.max); stepSize: Number(param.step || 1); value: Number(param.value)
                onMoved: backend.setLayerParam(param.key, value)
                background: Rectangle { x: parent.leftPadding; y: parent.topPadding + parent.availableHeight / 2 - 2; width: parent.availableWidth; height: 4; radius: 2; color: theme.borderColor
                    Rectangle { width: parent.parent.visualPosition * parent.width; height: parent.height; radius: 2; color: theme.accentColor }
                }
                handle: Rectangle { x: parent.leftPadding + parent.visualPosition * (parent.availableWidth - width); y: parent.topPadding + parent.availableHeight / 2 - height / 2; width: 15; height: 15; radius: 8; color: parent.pressed ? theme.accentHoverColor : theme.accentColor }
            }
        }
    }
}
