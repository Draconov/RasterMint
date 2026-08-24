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

    // Glyph picker metadata mirrors the core's 48 built-in sets plus Custom.
    // The actual characters and density analysis stay in Python; QML only needs
    // names and short previews for browsing.
    property var glyphSetCategories: [
        {"name": "ASCII & Punctuation", "sets": [
            {"name": "Classic ASCII", "preview": " .:-=+*#%@"}, {"name": "Dense ASCII", "preview": " .'`^\",:;Il!i~+_-?..."},
            {"name": "Minimal ASCII", "preview": " .-+*#@"}, {"name": "Punctuation", "preview": " .'`,:;!iI|/\\()[]{}<>?"},
            {"name": "Typewriter", "preview": " .,:;i1tfLCG08@"}, {"name": "Technical", "preview": " ._-~=+<>[]{}()|/\\*#%@"}
        ]},
        {"name": "Numbers", "sets": [
            {"name": "Binary", "preview": "01"}, {"name": "Decimal", "preview": " 0123456789"}, {"name": "Hex", "preview": " 0123456789ABCDEF"},
            {"name": "Roman", "preview": " .IVXLCDM"}, {"name": "Digital", "preview": " .1470253689"}
        ]},
        {"name": "Blocks", "sets": [
            {"name": "Blocks", "preview": " ░▒▓█"}, {"name": "Shade Blocks", "preview": " ░▒▓█"}, {"name": "Half Blocks", "preview": " ▂▄▆█"},
            {"name": "Vertical Blocks", "preview": " ▁▂▃▄▅▆▇█"}, {"name": "Quadrants", "preview": " ▖▗▘▝▚▞▙▛▜▟█"}
        ]},
        {"name": "Braille", "sets": [
            {"name": "Braille Low", "preview": " ⠂⠃⠇⠏⠟⠿⣿"}, {"name": "Braille Dense", "preview": " ⠁⠉⠋⠛⠟⠿⣿"},
            {"name": "Braille Dots", "preview": " ⠂⠆⠇⠧⠷⠿⣿"}, {"name": "Braille Cells", "preview": " ⠀⠐⠒⠖⠶⠾⣿"}
        ]},
        {"name": "Geometric", "sets": [
            {"name": "Squares", "preview": " ·▫▪□▣■"}, {"name": "Circles", "preview": " ·∘○◌◍●"}, {"name": "Diamonds", "preview": " ·◇◈◆"},
            {"name": "Triangles", "preview": " ·△▽◁▷▲▼◀▶"}, {"name": "Mixed Geometry", "preview": " ·○□◇△◌◍▣◆●■"}
        ]},
        {"name": "Symbols", "sets": [
            {"name": "Arrows", "preview": " ·←↑→↓↔↕⇐⇑⇒⇓"}, {"name": "Math", "preview": " .−+=×÷≈≠≤≥∞∑∫√"}, {"name": "Stars", "preview": " ·⋆✦✧★✹✺✸"},
            {"name": "Currency", "preview": " .¢$€£¥₩₽₹"}, {"name": "Cards", "preview": " ·♤♡♢♧♠♥♦♣"}
        ]},
        {"name": "Line Art", "sets": [
            {"name": "Box Light", "preview": " ·─│┌┐└┘├┤┬┴┼"}, {"name": "Box Heavy", "preview": " ·━┃┏┓┗┛┣┫┳┻╋"},
            {"name": "Corners", "preview": " ·╭╮╰╯┌┐└┘"}, {"name": "Diagonals", "preview": " ./\\╱╲╳×#"}
        ]},
        {"name": "Letters", "sets": [
            {"name": "Latin Lower", "preview": " .abcdefghijklmnopqrstuvwxyz"}, {"name": "Latin Upper", "preview": " .ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
            {"name": "Mixed Letters", "preview": " .ilIjtfrxvucszXYUJCLQOZ..."}, {"name": "Greek", "preview": " .ιτγλνχκπρσφωΨΩ"},
            {"name": "Cyrillic", "preview": " .іґлптчжкмшщюяФЖШЩЮ"}
        ]},
        {"name": "Retro", "sets": [
            {"name": "Terminal", "preview": " .,:;+*xX#%@"}, {"name": "DOS", "preview": " .░▒▓█"},
            {"name": "Teletext", "preview": " .▖▗▘▝▚▞▙▛▜▟█"}, {"name": "LCD", "preview": " ._-:=+*#█"}
        ]},
        {"name": "Decorative", "sets": [
            {"name": "Dots", "preview": " .·•∙●"}, {"name": "Crosses", "preview": " .+×✕✖✚✜"}, {"name": "Sparkles", "preview": " .·✧✦⋆★✹"},
            {"name": "Flowers", "preview": " .·❀✿❁✾✽"}, {"name": "Music", "preview": " .·♪♫♩♬♭♯"}
        ]},
        {"name": "Custom", "sets": [{"name": "Custom", "preview": "Your characters"}]}
    ]

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

    function selectedParamValue(key, fallback) {
        for (var i = 0; i < editorLayerParams.length; ++i) {
            if (editorLayerParams[i].key === key)
                return editorLayerParams[i].value
        }
        return fallback
    }

    function paramVisible(param) {
        if (backend.selectedLayerName === "ASCII / Glyph") {
            if (param.key === "custom_chars")
                return String(selectedParamValue("character_set", "Classic ASCII")) === "Custom"
            if (param.key === "foreground")
                return String(selectedParamValue("color_mode", "Source")) === "Single Colour"
            if (param.key === "background")
                return String(selectedParamValue("background_mode", "Solid Colour")) === "Solid Colour"
        }
        if (backend.selectedLayerName === "Text Mask" && param.key === "background")
            return String(selectedParamValue("background_mode", "Solid Colour")) === "Solid Colour"
        if (backend.selectedLayerName === "Dither") {
            var algorithm = String(selectedParamValue("algorithm", "Floyd-Steinberg"))
            var colourMix = algorithm === "1:1 Colour Mix"
            if (String(param.key).indexOf("color_mix_") === 0)
                return colourMix
            if (colourMix && (param.key === "strength" || param.key === "threshold" || param.key === "serpentine"))
                return false
        }
        if (backend.selectedLayerName === "Dither Glow" && param.key === "glow_color")
            return String(selectedParamValue("glow_color_mode", "Source")) === "Custom Tint"
        return true
    }

    function glyphPreview(name) {
        if (String(name) === "Custom")
            return String(selectedParamValue("custom_chars", " .:-=+*#%@"))
        var categories = root.glyphSetCategories || []
        for (var i = 0; i < categories.length; ++i) {
            var sets = categories[i].sets || []
            for (var j = 0; j < sets.length; ++j) {
                if (String(sets[j].name) === String(name))
                    return String(sets[j].preview || "")
            }
        }
        return ""
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
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

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
                        visible: root.paramVisible(param)
                        sourceComponent: param.type === "bool"
                                         ? boolEditor
                                         : param.type === "glyph_set"
                                           ? glyphSetEditor
                                           : param.type === "choice"
                                             ? choiceEditor
                                             : param.type === "color"
                                               ? colorEditor
                                               : param.type === "text" || param.type === "file"
                                                 ? textEditor
                                                 : numberEditor
                    }
                }
            }
        }
    }

    property var expandedGlyphCategories: ({})

    function glyphCategoryExpanded(name) {
        return Boolean(expandedGlyphCategories[name])
    }

    function toggleGlyphCategory(name) {
        var next = {}
        for (var key in expandedGlyphCategories)
            next[key] = expandedGlyphCategories[key]
        next[name] = !Boolean(next[name])
        expandedGlyphCategories = next
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
                Layout.fillWidth: true
                model: param.options
                enabled: !param.animated
                Component.onCompleted: currentIndex = Math.max(0, param.options.indexOf(String(param.value)))
                onActivated: backend.setLayerParam(param.key, currentText)
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "ASCII / Glyph"
                         && param.key === "background_mode"
                         && String(param.value) === "Transparent"
                text: "Transparent ASCII background keeps alpha in transparency-capable exports."
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
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
        id: colorEditor
        ColumnLayout {
            spacing: 4
            MintLabel { text: param.label; color: theme.mutedTextColor }
            MintColorPicker {
                Layout.fillWidth: true
                colorValue: String(param.value)
                dialogTitle: "Choose " + String(param.label).toLowerCase()
                enabled: !param.animated
                onColorPicked: function(value) {
                    backend.setLayerParam(param.key, value)
                }
            }
        }
    }

    Component {
        id: glyphSetEditor
        ColumnLayout {
            id: glyphEditor
            spacing: 4
            MintLabel { text: param.label; color: theme.mutedTextColor }

            MintButton {
                id: glyphButton
                Layout.fillWidth: true
                text: String(param.value || "Classic ASCII")
                enabled: !param.animated
                onClicked: {
                    var point = glyphButton.mapToItem(Overlay.overlay, 0, glyphButton.height + 4)
                    glyphPopup.x = Math.max(4, Math.min(point.x, Overlay.overlay.width - glyphPopup.width - 4))
                    glyphPopup.y = Math.max(4, Math.min(point.y, Overlay.overlay.height - glyphPopup.height - 4))
                    glyphPopup.open()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                radius: 5
                color: theme.canvasColor
                border.color: theme.borderColor
                clip: true
                Text {
                    anchors.fill: parent
                    anchors.margins: 7
                    text: root.glyphPreview(String(param.value || "Classic ASCII"))
                    color: theme.textColor
                    font.family: "monospace"
                    font.pixelSize: 14
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
            }

            Popup {
                id: glyphPopup
                popupType: Popup.Item
                parent: Overlay.overlay
                width: 360
                height: Math.max(160, Math.min(500, glyphCategoryColumn.implicitHeight + 10, Overlay.overlay.height - y - 4))
                padding: 5
                background: Rectangle { color: theme.panelRaisedColor; border.color: theme.borderColor; radius: 8 }

                contentItem: ScrollView {
                    id: glyphScroll
                    clip: true
                    contentWidth: availableWidth
                    ScrollBar.vertical.policy: ScrollBar.AlwaysOff

                    ColumnLayout {
                        id: glyphCategoryColumn
                        width: glyphScroll.availableWidth
                        spacing: 3

                        Repeater {
                            model: root.glyphSetCategories
                            delegate: ColumnLayout {
                                id: glyphCategoryDelegate
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: 2

                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 34
                                    radius: 5
                                    color: glyphCategoryMouse.containsMouse ? theme.selectionColor : theme.panelRaisedColor
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 8
                                        anchors.rightMargin: 8
                                        spacing: 7
                                        Text {
                                            text: root.glyphCategoryExpanded(glyphCategoryDelegate.modelData.name) ? "▾" : "▸"
                                            color: theme.accentColor
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: glyphCategoryDelegate.modelData.name
                                            color: theme.textColor
                                            font.bold: true
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            text: String((glyphCategoryDelegate.modelData.sets || []).length)
                                            color: theme.mutedTextColor
                                            font.pixelSize: 10
                                        }
                                    }
                                    MouseArea {
                                        id: glyphCategoryMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: root.toggleGlyphCategory(glyphCategoryDelegate.modelData.name)
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: root.glyphCategoryExpanded(glyphCategoryDelegate.modelData.name)
                                    spacing: 1
                                    Repeater {
                                        model: glyphCategoryDelegate.modelData.sets || []
                                        delegate: ItemDelegate {
                                            id: glyphSetItem
                                            required property var modelData
                                            Layout.fillWidth: true
                                            implicitHeight: 36
                                            leftPadding: 22
                                            rightPadding: 8
                                            contentItem: RowLayout {
                                                spacing: 8
                                                Text {
                                                    Layout.preferredWidth: 112
                                                    text: glyphSetItem.modelData.name
                                                    color: theme.textColor
                                                    elide: Text.ElideRight
                                                }
                                                Text {
                                                    Layout.fillWidth: true
                                                    text: glyphSetItem.modelData.preview
                                                    color: theme.mutedTextColor
                                                    font.family: "monospace"
                                                    font.pixelSize: 11
                                                    horizontalAlignment: Text.AlignRight
                                                    elide: Text.ElideRight
                                                }
                                            }
                                            background: Rectangle {
                                                radius: 5
                                                color: parent.hovered ? theme.selectionColor : "transparent"
                                            }
                                            onClicked: {
                                                backend.setLayerParam(param.key, String(modelData.name))
                                                glyphPopup.close()
                                            }
                                        }
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
