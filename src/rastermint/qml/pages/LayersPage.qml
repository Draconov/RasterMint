import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    property int addIndex: 0

    // Layer-card drag state. The model itself is committed only on release;
    // delegates are translated live so the user sees the final order while dragging.
    property int dragSourceIndex: -1
    property int dragTargetIndex: -1
    property real dragDeltaY: 0
    readonly property int layerRowHeight: 48
    readonly property int layerRowSpacing: 4

    // Keep one stable parameter-editor model while a slider is held.
    // The backend emits layerSelectionChanged for every live parameter update;
    // replacing a Repeater model during the gesture destroys the Slider and
    // releases its mouse grab. We therefore resync only after the gesture ends.
    property bool parameterInteractionActive: false
    property var editorLayerParams: []

    function beginLayerDrag(index) {
        dragSourceIndex = index
        dragTargetIndex = index
        dragDeltaY = 0
        backend.selectLayer(index)
    }

    function updateLayerDrag(deltaY) {
        if (dragSourceIndex < 0 || layerList.count <= 0)
            return

        var stride = layerRowHeight + layerRowSpacing
        var minimum = -dragSourceIndex * stride
        var maximum = (layerList.count - 1 - dragSourceIndex) * stride
        dragDeltaY = Math.max(minimum, Math.min(maximum, deltaY))
        dragTargetIndex = Math.max(
            0,
            Math.min(layerList.count - 1, dragSourceIndex + Math.round(dragDeltaY / stride))
        )
    }

    function finishLayerDrag() {
        var source = dragSourceIndex
        var target = dragTargetIndex
        dragSourceIndex = -1
        dragTargetIndex = -1
        dragDeltaY = 0
        if (source >= 0 && target >= 0 && source !== target)
            backend.moveLayer(source, target)
    }

    function syncEditorLayerParams() {
        if (!parameterInteractionActive)
            editorLayerParams = backend.selectedLayerParams
    }

    function beginParameterInteraction() {
        // Do not touch editorLayerParams here: changing the Repeater model at
        // press time would immediately destroy the slider that owns the grab.
        parameterInteractionActive = true
    }

    function endParameterInteraction() {
        parameterInteractionActive = false
        // Let the release event finish first, then pull the final canonical
        // value back from the backend once.
        Qt.callLater(syncEditorLayerParams)
    }

    Component.onCompleted: syncEditorLayerParams()

    Connections {
        target: backend
        function onLayerSelectionChanged() {
            root.syncEditorLayerParams()
        }
    }

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
            spacing: root.layerRowSpacing
            clip: true
            currentIndex: backend.selectedLayerIndex
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOff }

            delegate: Rectangle {
                id: layerDelegate
                width: layerList.width
                height: root.layerRowHeight
                radius: 7

                property bool isDragging: root.dragSourceIndex === index
                property real liveReorderOffset: {
                    if (root.dragSourceIndex < 0 || root.dragTargetIndex === root.dragSourceIndex)
                        return 0

                    var stride = root.layerRowHeight + root.layerRowSpacing
                    if (root.dragSourceIndex < root.dragTargetIndex
                            && index > root.dragSourceIndex
                            && index <= root.dragTargetIndex)
                        return -stride
                    if (root.dragSourceIndex > root.dragTargetIndex
                            && index >= root.dragTargetIndex
                            && index < root.dragSourceIndex)
                        return stride
                    return 0
                }

                z: isDragging ? 20 : 0
                color: index === backend.selectedLayerIndex
                       ? theme.selectionColor
                       : (layerHover.hovered ? theme.panelHoverColor : theme.panelRaisedColor)
                border.color: isDragging ? theme.accentColor : theme.borderColor
                border.width: isDragging ? 2 : 1
                opacity: isDragging ? 0.88 : 1.0

                transform: Translate {
                    y: layerDelegate.isDragging ? root.dragDeltaY : layerDelegate.liveReorderOffset
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 7

                    MintCheckBox {
                        checked: layerEnabled
                        onToggled: backend.setLayerEnabled(index, checked)
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text {
                            Layout.fillWidth: true
                            text: kind
                            color: theme.textColor
                            font.bold: true
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: summary
                            color: theme.mutedTextColor
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                    }

                    Text {
                        text: "≡"
                        color: layerDelegate.isDragging ? theme.textColor : theme.mutedTextColor
                        font.pixelSize: 16
                        font.bold: true
                        Layout.leftMargin: 8
                        Layout.rightMargin: 5
                    }

                    MintButton { text: "↑"; enabled: index > 0; onClicked: backend.moveLayer(index, index - 1) }
                    MintButton { text: "↓"; enabled: index < layerList.count - 1; onClicked: backend.moveLayer(index, index + 1) }
                }

                HoverHandler {
                    id: layerHover
                    cursorShape: cardDrag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                }

                TapHandler {
                    onTapped: backend.selectLayer(index)
                }

                // Dragging works from the whole layer card. Child buttons still
                // receive ordinary clicks; moving beyond the drag threshold turns
                // the same press into a card reorder gesture.
                DragHandler {
                    id: cardDrag
                    target: null
                    acceptedButtons: Qt.LeftButton
                    xAxis.enabled: false
                    yAxis.enabled: true

                    onActiveChanged: {
                        if (active) {
                            root.beginLayerDrag(index)
                        } else if (root.dragSourceIndex === index) {
                            root.finishLayerDrag()
                        }
                    }

                    onTranslationChanged: {
                        if (active)
                            root.updateLayerDrag(translation.y)
                    }
                }

                ToolTip.visible: layerHover.hovered && !cardDrag.active
                ToolTip.delay: 500
                ToolTip.text: "Drag anywhere on the layer card to reorder"
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
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            ScrollBar.vertical.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: paramScroll.availableWidth
                spacing: 8

                Repeater {
                    model: root.editorLayerParams
                    delegate: Loader {
                        Layout.fillWidth: true
                        property var param: modelData
                        sourceComponent: param.type === "bool"
                                         ? boolEditor
                                         : param.type === "choice"
                                           ? choiceEditor
                                           : param.type === "text" || param.type === "file" || param.type === "color"
                                             ? textEditor
                                             : numberEditor
                    }
                }
            }
        }
    }

    Popup {
        id: addPopup
        popupType: Popup.Item
        parent: Overlay.overlay
        width: 250
        height: Math.min(440, addList.contentHeight + 10)
        padding: 5
        background: Rectangle { color: theme.panelRaisedColor; border.color: theme.borderColor; radius: 8 }
        contentItem: ListView {
            id: addList
            model: backend.layerKinds
            clip: true
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOff }
            delegate: ItemDelegate {
                width: addList.width
                height: 32
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
                Layout.fillWidth: true
                model: param.options
                enabled: !param.animated
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
            MintTextField {
                Layout.fillWidth: true
                text: String(param.value)
                enabled: !param.animated
                onEditingFinished: backend.setLayerParam(param.key, text)
            }
        }
    }

    Component {
        id: numberEditor
        ColumnLayout {
            spacing: 4

            RowLayout {
                Layout.fillWidth: true
                MintLabel {
                    text: param.label + (param.animated ? "  · animated" : "")
                    color: theme.mutedTextColor
                    Layout.fillWidth: true
                }
                MintLabel {
                    text: Number(paramSlider.displayValue).toFixed(param.decimals !== undefined ? param.decimals : 0) + (param.suffix || "")
                }
            }

            MintSlider {
                id: paramSlider
                Layout.fillWidth: true
                enabled: !param.animated
                from: Number(param.min)
                to: Number(param.max)
                stepSize: Number(param.step || 1)
                value: Number(param.value)

                onInteractionActiveChanged: {
                    if (interactionActive) {
                        root.beginParameterInteraction()
                        backend.beginHistoryGroup(backend.selectedLayerName + " · " + param.label)
                    } else {
                        backend.endHistoryGroup()
                        root.endParameterInteraction()
                    }
                }

                // Every pointer movement is applied immediately, so the preview
                // updates continuously while the knob is held and dragged.
                onUserMoved: function(newValue) {
                    backend.setLayerParam(param.key, newValue)
                }
            }
        }
    }
}
