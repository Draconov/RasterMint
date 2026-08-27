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
        if (Boolean(param.hidden))
            return false
        if (backend.selectedLayerName === "ASCII / Glyph") {
            var asciiMapping = String(selectedParamValue("mapping", "Density"))
            var structureMatch = asciiMapping === "Structure Match"
            if (param.key === "custom_chars")
                return String(selectedParamValue("character_set", "Classic ASCII")) === "Custom"
            if (param.key === "foreground")
                return String(selectedParamValue("color_mode", "Source")) === "Single Colour"
            if (param.key === "background")
                return String(selectedParamValue("background_mode", "Solid Colour")) === "Solid Colour"
            if (param.key === "structure"
                    || param.key === "density_influence"
                    || param.key === "local_detail"
                    || param.key === "auto_cell_aspect"
                    || param.key === "supersampling")
                return structureMatch
            if (param.key === "color_sampling")
                return structureMatch && String(selectedParamValue("color_mode", "Source")) !== "Single Colour"
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
        if (backend.selectedLayerName === "Hardware Limits" && param.key === "palette_source")
            return String(selectedParamValue("profile_palette_json", "[]")) !== "[]"
        if (backend.selectedLayerName === "Hardware Limits" && param.key === "use_profile_groups")
            return String(selectedParamValue("profile_group_indices_json", "[]")) !== "[]"
        return true
    }

    function glyphPreview(name) {
        var injected = String(selectedParamValue("inject_chars", ""))
        var base = ""
        if (String(name) === "Custom") {
            base = String(selectedParamValue("custom_chars", " .:-=+*#%@"))
        } else {
            var categories = root.glyphSetCategories || []
            for (var i = 0; i < categories.length; ++i) {
                var sets = categories[i].sets || []
                for (var j = 0; j < sets.length; ++j) {
                    if (String(sets[j].name) === String(name)) {
                        base = String(sets[j].preview || "")
                        break
                    }
                }
                if (base !== "")
                    break
            }
        }
        return injected !== "" ? (base + "  +  " + injected) : base
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
            MintLabel { text: qsTr("Layers"); font.bold: true; font.pixelSize: 15; Layout.fillWidth: true }
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

                property bool fixedStage: kind === "Hardware Limits" || kind === "Hardware Display"
                property bool isDragging: root.dragSourceIndex === index
                property bool multiSelected: backend.selectedLayerIndices.indexOf(index) >= 0
                property bool firstInGroup: String(groupId || "") !== "" && backend.isFirstLayerInGroup(index)
                property string groupName: String(groupId || "") !== "" ? backend.layerGroupName(groupId) : ""
                visible: String(groupId || "") === "" || !backend.layerGroupCollapsed(groupId) || firstInGroup
                height: visible ? root.layerRowHeight : 0
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
                color: multiSelected
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

                    MintButton {
                        visible: layerDelegate.firstInGroup
                        Layout.preferredWidth: 28
                        text: backend.layerGroupCollapsed(groupId) ? "▸" : "▾"
                        onClicked: backend.setLayerGroupCollapsed(groupId, !backend.layerGroupCollapsed(groupId))
                        ToolTip.visible: hovered
                        ToolTip.text: qsTr("Collapse / expand layer group")
                    }

                    MintCheckBox {
                        checked: layerEnabled
                        onToggled: backend.setLayerEnabled(index, checked)
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text {
                            Layout.fillWidth: true
                            text: layerDelegate.firstInGroup && layerDelegate.groupName !== ""
                                  ? (layerDelegate.groupName + " · " + qsTr(kind))
                                  : qsTr(kind)
                            color: theme.textColor
                            font.bold: true
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: (String(blendMode || "Normal") !== "Normal" || Number(layerOpacity) < 0.999
                                  ? (qsTr(String(blendMode || "Normal")) + " · " + Math.round(Number(layerOpacity) * 100) + "%" + (String(summary) !== "" ? " · " : ""))
                                  : "") + qsTr(summary)
                            color: theme.mutedTextColor
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                    }

                    MintButton { text: "↑"; enabled: !layerDelegate.fixedStage && index > 0; onClicked: backend.moveLayer(index, index - 1) }
                    MintButton { text: "↓"; enabled: !layerDelegate.fixedStage && index < layerList.count - 1; onClicked: backend.moveLayer(index, index + 1) }
                }

                HoverHandler {
                    id: layerHover
                    cursorShape: cardDrag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                }

                TapHandler {
                    acceptedModifiers: Qt.NoModifier
                    onTapped: backend.selectLayer(index)
                }
                TapHandler {
                    acceptedModifiers: Qt.ControlModifier
                    onTapped: backend.toggleLayerSelection(index)
                }

                // Dragging works from the whole layer card. Child buttons still
                // receive ordinary clicks; moving beyond the drag threshold turns
                // the same press into a card reorder gesture.
                DragHandler {
                    id: cardDrag
                    enabled: !layerDelegate.fixedStage
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
                ToolTip.text: layerDelegate.fixedStage
                    ? qsTr("Hardware pipeline stage · fixed after normal layers")
                    : qsTr("Drag anywhere on the layer card to reorder")
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            MintButton {
                Layout.fillWidth: true
                text: qsTr("Duplicate")
                enabled: backend.selectedLayerName !== "Hardware Limits" && backend.selectedLayerName !== "Hardware Display"
                onClicked: backend.duplicateSelectedLayer()
            }
            MintButton { Layout.fillWidth: true; text: qsTr("Copy"); onClicked: backend.copySelectedLayerSettings() }
            MintButton { Layout.fillWidth: true; text: qsTr("Paste"); enabled: backend.layerClipboardAvailable; onClicked: backend.pasteSelectedLayerSettings() }
            MintButton { Layout.fillWidth: true; text: qsTr("Reset"); onClicked: backend.resetSelectedLayer() }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            MintButton { Layout.fillWidth: true; text: backend.selectedLayerSolo ? qsTr("Unsolo") : qsTr("Solo"); onClicked: backend.toggleSoloSelectedLayer() }
            MintButton { Layout.fillWidth: true; text: qsTr("Group"); onClicked: groupDialog.open() }
            MintButton { Layout.fillWidth: true; text: qsTr("Ungroup"); onClicked: backend.ungroupSelectedLayers() }
            MintButton {
                Layout.fillWidth: true
                text: backend.selectedLayerIndices.length > 1 ? qsTr("Remove %1").arg(backend.selectedLayerIndices.length) : qsTr("Remove")
                onClicked: backend.removeSelectedLayers()
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
        MintLabel { text: qsTr(backend.selectedLayerName); font.bold: true }
        MintLabel {
            Layout.fillWidth: true
            visible: backend.selectedLayerName === "Hardware Limits" || backend.selectedLayerName === "Hardware Display"
            text: backend.selectedLayerName === "Hardware Limits"
                  ? (String(selectedParamValue("profile_palette_json", "[]")) !== "[]"
                     ? qsTr("Fixed hardware stage after normal Layers. Choose Active Palette to make palette edits affect the strict hardware remap, or Profile Palette to restore the hardware profile's original colours.")
                     : qsTr("Fixed hardware stage after normal Layers. This profile has no fixed hardware palette; its channel/tile/colour-depth limits still apply. Use the Dither layer if you want to map the image to the active palette."))
                  : qsTr("Fixed display stage. Runs after pixel-aspect correction in Display view and in exports only when display-view export is enabled.")
            color: theme.mutedTextColor
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }

        ScrollView {
            id: paramScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            ScrollBar.vertical.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: paramScroll.availableWidth
                spacing: 8

                MintLabel { text: qsTr("Layer compositing"); font.bold: true }
                RowLayout {
                    Layout.fillWidth: true
                    MintLabel { text: qsTr("Opacity"); color: theme.mutedTextColor; Layout.fillWidth: true }
                    MintLabel { text: Math.round(backend.selectedLayerOpacity * 100) + "%" }
                }
                MintSlider {
                    Layout.fillWidth: true
                    from: 0; to: 1; stepSize: 0.01
                    value: backend.selectedLayerOpacity
                    onInteractionActiveChanged: {
                        if (interactionActive) backend.beginHistoryGroup(backend.selectedLayerName + " · Opacity")
                        else backend.endHistoryGroup()
                    }
                    onUserMoved: function(newValue) { backend.setLayerOpacity(newValue) }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    MintLabel { text: qsTr("Blend mode"); color: theme.mutedTextColor }
                    MintComboBox {
                        Layout.fillWidth: true
                        model: backend.layerBlendModes
                        translateModel: true
                        Component.onCompleted: currentIndex = Math.max(0, backend.layerBlendModes.indexOf(backend.selectedLayerBlendMode))
                        onActivated: backend.setLayerBlendMode(currentText)
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    MintLabel { text: qsTr("Mask"); color: theme.mutedTextColor }
                    MintComboBox {
                        Layout.fillWidth: true
                        model: backend.layerMaskTypes
                        translateModel: true
                        Component.onCompleted: currentIndex = Math.max(0, backend.layerMaskTypes.indexOf(String(backend.selectedLayerMask.type || "None")))
                        onActivated: backend.setLayerMaskType(currentText)
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: String(backend.selectedLayerMask.type || "None") !== "None"
                    spacing: 4
                    RowLayout {
                        Layout.fillWidth: true
                        MintLabel { text: qsTr("Mask strength"); color: theme.mutedTextColor; Layout.fillWidth: true }
                        MintLabel { text: Math.round(Number(backend.selectedLayerMask.strength || 0) * 100) + "%" }
                    }
                    MintSlider {
                        Layout.fillWidth: true; from: 0; to: 1; stepSize: 0.01
                        value: Number(backend.selectedLayerMask.strength !== undefined ? backend.selectedLayerMask.strength : 1)
                        onUserMoved: function(newValue) { backend.setLayerMaskStrength(newValue) }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        MintLabel { text: qsTr("Mask feather"); color: theme.mutedTextColor; Layout.fillWidth: true }
                        MintLabel { text: Math.round(Number(backend.selectedLayerMask.feather || 0) * 100) + "%" }
                    }
                    MintSlider {
                        Layout.fillWidth: true; from: 0; to: 1; stepSize: 0.01
                        value: Number(backend.selectedLayerMask.feather || 0)
                        onUserMoved: function(newValue) { backend.setLayerMaskFeather(newValue) }
                    }
                    MintCheckBox {
                        text: qsTr("Invert mask")
                        checked: Boolean(backend.selectedLayerMask.invert)
                        onToggled: backend.setLayerMaskInvert(checked)
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
                MintLabel { text: qsTr("Effect parameters"); font.bold: true }

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
                                                 : param.type === "duration"
                                                   ? durationEditor
                                                   : numberEditor
                    }
                }
            }
        }
    }

    Dialog {
        id: groupDialog
        title: qsTr("Create Layer Group")
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: Overlay.overlay
        onOpened: { groupNameField.text = qsTr("Layer Group"); groupNameField.forceActiveFocus() }
        onAccepted: backend.groupSelectedLayers(groupNameField.text)
        contentItem: ColumnLayout {
            spacing: 8
            MintLabel { text: qsTr("Group name"); color: theme.mutedTextColor }
            MintTextField { id: groupNameField; Layout.preferredWidth: 260 }
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
                                    text: qsTr(categoryDelegate.modelData.name)
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
                                        text: qsTr(parent.modelData)
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
            text: qsTr(param.label) + (param.animated ? "  · " + qsTr("animated") : "")
            checked: Boolean(param.value)
            enabled: !param.animated
            onToggled: backend.setLayerParam(param.key, checked)
        }
    }

    Component {
        id: choiceEditor
        ColumnLayout {
            spacing: 4
            MintLabel { text: qsTr(param.label); color: theme.mutedTextColor }
            MintComboBox {
                Layout.fillWidth: true
                model: param.options
                translateModel: true
                enabled: !param.animated
                Component.onCompleted: currentIndex = Math.max(0, param.options.indexOf(String(param.value)))
                onActivated: backend.setLayerParam(param.key, currentText)
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "Display Persistence" && param.key === "display_type"
                text: String(param.value) === "CRT"
                      ? qsTr("CRT keeps bright phosphor trails, with green lingering slightly longer than red and blue.")
                      : (String(param.value) === "LCD"
                         ? qsTr("LCD models pixel-response lag, with darker transitions typically trailing longer.")
                         : (String(param.value) === "OLED"
                            ? qsTr("OLED models longer temporary retention concentrated in bright image regions.")
                            : qsTr("Generic blends a neutral exponential history of previous frame colours.")))
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "ASCII / Glyph" && param.key === "color_mode"
                text: String(param.value) === "Palette"
                      ? qsTr("Glyphs use the nearest colour from the active palette, based on the selected colour-sampling method.")
                      : (String(param.value) === "Single Colour"
                         ? qsTr("Every glyph uses the selected Foreground colour.")
                         : (String(selectedParamValue("mapping", "Density")) === "Structure Match"
                            && String(selectedParamValue("color_sampling", "Glyph Weighted")) === "Glyph Weighted"
                            ? qsTr("Glyph colour is sampled mainly from source pixels covered by the selected glyph.")
                            : qsTr("Each glyph uses the average source colour of its image cell.")))
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "ASCII / Glyph" && param.key === "mapping"
                text: String(param.value) === "Structure Match"
                      ? qsTr("High-detail mode compares each source cell against the actual shape of every available glyph.")
                      : qsTr("Classic fast mode chooses glyphs only by cell brightness/density.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "ASCII / Glyph" && param.key === "color_sampling"
                text: String(param.value) === "Glyph Weighted"
                      ? qsTr("Samples colour mainly from source pixels covered by the selected glyph.")
                      : qsTr("Uses the average colour of the whole source cell.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "ASCII / Glyph" && param.key === "supersampling"
                text: qsTr("Higher supersampling renders glyphs above final resolution, then downsamples them for cleaner tiny shapes.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "ASCII / Glyph"
                         && param.key === "background_mode"
                         && String(param.value) === "Transparent"
                text: qsTr("Transparent ASCII background keeps alpha in transparency-capable exports.")
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
            MintLabel { text: qsTr(param.label); color: theme.mutedTextColor }
            MintTextField {
                Layout.fillWidth: true
                text: String(param.value)
                enabled: !param.animated
                onEditingFinished: backend.setLayerParam(param.key, text)
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "ASCII / Glyph" && param.key === "inject_chars"
                text: qsTr("Adds unique characters to the selected built-in set without replacing it.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
        }
    }

    Component {
        id: colorEditor
        ColumnLayout {
            spacing: 4
            MintLabel { text: qsTr(param.label); color: theme.mutedTextColor }
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
            MintLabel { text: qsTr(param.label); color: theme.mutedTextColor }

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
                                            text: qsTr(glyphCategoryDelegate.modelData.name)
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
                                                    text: qsTr(glyphSetItem.modelData.name)
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
        id: durationEditor
        ColumnLayout {
            spacing: 4

            MintLabel {
                text: qsTr(param.label) + (param.animated ? "  · " + qsTr("animated") : "")
                color: theme.mutedTextColor
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 7

                MintSlider {
                    id: durationSlider
                    Layout.fillWidth: true
                    enabled: !param.animated
                    from: Number(param.min)
                    to: Number(param.slider_max !== undefined ? param.slider_max : param.max)
                    stepSize: Number(param.step || 0.05)
                    value: Math.min(Number(param.value), to)

                    onInteractionActiveChanged: {
                        if (interactionActive) {
                            root.beginParameterInteraction()
                            backend.beginHistoryGroup(backend.selectedLayerName + " · " + param.label)
                        } else {
                            backend.endHistoryGroup()
                            root.endParameterInteraction()
                        }
                    }
                    onUserMoved: function(newValue) {
                        backend.setLayerParam(param.key, newValue)
                    }
                }

                MintTextField {
                    id: durationField
                    Layout.preferredWidth: 82
                    enabled: !param.animated
                    horizontalAlignment: TextInput.AlignRight
                    text: Number(param.value).toFixed(param.decimals !== undefined ? param.decimals : 2)
                    validator: DoubleValidator {
                        bottom: Number(param.min)
                        top: Number(param.max)
                        decimals: param.decimals !== undefined ? Number(param.decimals) : 2
                        notation: DoubleValidator.StandardNotation
                    }
                    onEditingFinished: {
                        var parsed = Number(String(text).replace(",", "."))
                        if (isFinite(parsed)) {
                            parsed = Math.max(Number(param.min), Math.min(Number(param.max), parsed))
                            backend.setLayerParam(param.key, parsed)
                        } else {
                            text = Number(param.value).toFixed(param.decimals !== undefined ? param.decimals : 2)
                        }
                    }
                }
                MintLabel { text: qsTr("s"); color: theme.mutedTextColor }
            }

            MintLabel {
                Layout.fillWidth: true
                text: qsTr("The slider covers 0–60 seconds. Type a value up to 300 seconds for longer retention.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "Display Persistence"
                text: qsTr("Temporal history accumulates during forward playback, rendered animation/video previews, and sequential exports. After seeking or changing persistence settings, re-render the preview to rebuild history.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
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
                    text: qsTr(param.label) + (param.animated ? "  · " + qsTr("animated") : "")
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

            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "Display Persistence" && param.key === "decay"
                text: qsTr("Decay speed 1.00 uses the selected persistence time directly. Lower values leave a longer tail; higher values fade faster.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "ASCII / Glyph" && param.key === "font_scale"
                text: qsTr("Glyph size relative to the cell. 1.00× is roughly one cell high; the cell grid and spacing do not change.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "ASCII / Glyph" && param.key === "structure"
                text: qsTr("How strongly High Detail cares about the spatial shape inside each cell.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "ASCII / Glyph" && param.key === "density_influence"
                text: qsTr("Keeps the chosen glyph's overall ink/brightness density close to the source cell.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            MintLabel {
                Layout.fillWidth: true
                visible: backend.selectedLayerName === "ASCII / Glyph" && param.key === "local_detail"
                text: qsTr("Boosts contrast inside each cell before shape matching so edges survive in shadows and highlights.")
                color: theme.mutedTextColor
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
        }
    }
}
