import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    property int addIndex: 0

    // Layer/group drag state. Drops on the centre of a layer card group the
    // layers; edge drops keep reorder semantics and can pull a layer out one level.
    property int dragSourceIndex: -1
    property int dragTargetIndex: -1
    property string dragTargetGroupId: ""
    property string dragDropMode: "before"
    property real dragDeltaX: 0
    property real dragDeltaY: 0
    property string groupDragId: ""
    property int groupDragTargetIndex: -1
    property string groupDragTargetGroupId: ""
    property string groupDragDropMode: "before"
    property string editingGroupId: ""
    property string selectedGroupId: ""
    property var groupColorOptions: [
        {"name": qsTr("None"), "value": ""},
        {"name": qsTr("Red"), "value": "#ff5f56"},
        {"name": qsTr("Orange"), "value": "#ff9f43"},
        {"name": qsTr("Yellow"), "value": "#feca57"},
        {"name": qsTr("Green"), "value": "#2ed573"},
        {"name": qsTr("Cyan"), "value": "#48dbfb"},
        {"name": qsTr("Blue"), "value": "#54a0ff"},
        {"name": qsTr("Purple"), "value": "#a55eea"},
        {"name": qsTr("Pink"), "value": "#ff6bcb"}
    ]
    readonly property int layerRowHeight: 48
    readonly property int layerRowSpacing: 4
    readonly property int groupHeaderHeight: 34
    focus: true

    // Keep one stable parameter-editor model while a slider is held.
    // The backend emits layerSelectionChanged for every live parameter update;
    // replacing a Repeater model during the gesture destroys the Slider and
    // releases its mouse grab. We therefore resync only after the gesture ends.
    property bool parameterInteractionActive: false
    property var editorLayerParams: []
    property var selectedGroupData: root.groupData(root.selectedGroupId)
    property real dragIndicatorY: -1
    property real dragIndicatorX: 0
    property real dragIndicatorWidth: 0
    property real groupDragIndicatorY: -1
    property real groupDragIndicatorX: 0
    property real groupDragIndicatorWidth: 0

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

    function nearestVisibleLayerIndex(y) {
        var bestIndex = -1
        var bestDistance = Number.MAX_VALUE
        for (var i = 0; i < layerList.count; ++i) {
            var item = layerList.itemAtIndex(i)
            if (!item || item.height <= 0)
                continue
            var center = item.y + (item.layerContentShown
                                   ? item.layerCardY + root.layerRowHeight / 2
                                   : item.height / 2)
            var distance = Math.abs(center - y)
            if (distance < bestDistance) {
                bestDistance = distance
                bestIndex = i
            }
        }
        return bestIndex
    }

    function groupData(groupId) {
        var key = String(groupId || "")
        var groups = backend.layerGroups
        for (var i = 0; i < groups.length; ++i) {
            if (String(groups[i].id || "") === key)
                return groups[i]
        }
        return {"id": "", "name": "", "opacity": 1.0, "blend_mode": "Normal", "color_label": "", "note": ""}
    }

    function clearLayerDragIndicator() {
        dragIndicatorY = -1
        dragIndicatorX = 0
        dragIndicatorWidth = 0
        dragTargetGroupId = ""
    }

    function setLayerDragIndicator(x, y, width) {
        dragIndicatorX = x
        dragIndicatorY = y
        dragIndicatorWidth = width
    }

    function clearGroupDragIndicator() {
        groupDragIndicatorY = -1
        groupDragIndicatorX = 0
        groupDragIndicatorWidth = 0
    }

    function setGroupDragIndicator(x, y, width) {
        groupDragIndicatorX = x
        groupDragIndicatorY = y
        groupDragIndicatorWidth = width
    }

    function lastVisibleLayerIndexInGroup(groupId) {
        var key = String(groupId || "")
        var lastIndex = -1
        for (var i = 0; i < layerList.count; ++i) {
            var item = layerList.itemAtIndex(i)
            if (!item || item.height <= 0)
                continue
            if (backend.layerIsInGroup(i, key))
                lastIndex = i
        }
        return lastIndex
    }

    function beginLayerDrag(index) {
        selectedGroupId = ""
        dragSourceIndex = index
        dragTargetIndex = index
        dragTargetGroupId = ""
        dragDropMode = "before"
        dragDeltaX = 0
        dragDeltaY = 0
        clearLayerDragIndicator()
        backend.selectLayer(index)
    }

    function updateLayerDrag(deltaX, deltaY) {
        if (dragSourceIndex < 0 || layerList.count <= 0)
            return
        var sourceItem = layerList.itemAtIndex(dragSourceIndex)
        if (!sourceItem)
            return
        dragDeltaX = deltaX
        dragDeltaY = deltaY
        dragTargetGroupId = ""
        if (deltaX < -28 && backend.layerDirectGroupId(dragSourceIndex) !== "") {
            dragTargetIndex = dragSourceIndex
            dragDropMode = "ungroup"
            clearLayerDragIndicator()
            return
        }
        var centerY = sourceItem.y + sourceItem.layerCardY + root.layerRowHeight / 2 + deltaY
        var target = nearestVisibleLayerIndex(centerY)
        if (target < 0) {
            clearLayerDragIndicator()
            return
        }
        dragTargetIndex = target
        var targetItem = layerList.itemAtIndex(target)
        if (!targetItem) {
            clearLayerDragIndicator()
            return
        }
        var yInItem = centerY - targetItem.y
        if (targetItem.headerData.length > 0 && yInItem >= 0 && yInItem < targetItem.layerCardY) {
            var headerStride = root.groupHeaderHeight + 2
            var headerIndex = Math.max(0, Math.min(targetItem.headerData.length - 1, Math.floor(yInItem / headerStride)))
            var header = targetItem.headerData[headerIndex]
            dragDropMode = "into"
            dragTargetGroupId = String(header.id || "")
            var lastMemberIndex = lastVisibleLayerIndexInGroup(dragTargetGroupId)
            if (lastMemberIndex >= 0) {
                var lastMemberItem = layerList.itemAtIndex(lastMemberIndex)
                if (lastMemberItem && lastMemberItem.layerContentShown) {
                    setLayerDragIndicator(
                        lastMemberItem.layerIndent + 14,
                        lastMemberItem.y + lastMemberItem.layerCardY + root.layerRowHeight - 1,
                        Math.max(80, layerList.width - (lastMemberItem.layerIndent + 24)))
                    return
                }
            }
            setLayerDragIndicator(
                Math.max(14, Number(header.depth || 1) * 12 + 14),
                targetItem.y + headerIndex * headerStride + root.groupHeaderHeight - 1,
                Math.max(80, layerList.width - (Math.max(14, Number(header.depth || 1) * 12 + 24))))
            return
        }
        if (target === dragSourceIndex) {
            dragDropMode = "before"
            clearLayerDragIndicator()
            return
        }
        if (!targetItem.layerContentShown) {
            dragDropMode = "into"
            clearLayerDragIndicator()
            return
        }
        var localY = centerY - (targetItem.y + targetItem.layerCardY)
        var targetGroup = backend.layerDirectGroupId(target)
        if (localY >= root.layerRowHeight * 0.25 && localY <= root.layerRowHeight * 0.75) {
            dragDropMode = "into"
            dragTargetGroupId = String(targetGroup || "")
            setLayerDragIndicator(
                targetItem.layerIndent + 14,
                targetItem.y + targetItem.layerCardY + root.layerRowHeight - 1,
                Math.max(80, layerList.width - (targetItem.layerIndent + 24)))
        } else if (localY < root.layerRowHeight * 0.5) {
            dragDropMode = "before"
            setLayerDragIndicator(
                targetItem.layerIndent + 8,
                targetItem.y + targetItem.layerCardY - 1,
                Math.max(80, layerList.width - (targetItem.layerIndent + 18)))
        } else {
            dragDropMode = "after"
            setLayerDragIndicator(
                targetItem.layerIndent + 8,
                targetItem.y + targetItem.layerCardY + root.layerRowHeight - 1,
                Math.max(80, layerList.width - (targetItem.layerIndent + 18)))
        }
    }

    function finishLayerDrag() {
        var source = dragSourceIndex
        var target = dragTargetIndex
        var mode = dragDropMode
        var targetGroupId = dragTargetGroupId
        dragSourceIndex = -1
        dragTargetIndex = -1
        dragTargetGroupId = ""
        dragDropMode = "before"
        dragDeltaX = 0
        dragDeltaY = 0
        clearLayerDragIndicator()
        if (source >= 0 && target >= 0 && (source !== target || mode === "ungroup"))
            backend.dropLayer(source, target, mode, targetGroupId)
    }

    function beginGroupDrag(groupId) {
        groupDragId = String(groupId || "")
        groupDragTargetIndex = -1
        groupDragTargetGroupId = ""
        groupDragDropMode = "before"
        clearGroupDragIndicator()
    }

    function updateGroupDragAt(y) {
        if (groupDragId === "")
            return
        var target = nearestVisibleLayerIndex(y)
        groupDragTargetIndex = target
        groupDragTargetGroupId = ""
        groupDragDropMode = "before"
        if (target < 0) {
            clearGroupDragIndicator()
            return
        }
        var targetItem = layerList.itemAtIndex(target)
        if (!targetItem) {
            clearGroupDragIndicator()
            return
        }

        var yInItem = y - targetItem.y
        if (targetItem.headerData.length > 0 && yInItem >= 0 && yInItem < targetItem.layerCardY) {
            var headerStride = root.groupHeaderHeight + 2
            var headerIndex = Math.max(0, Math.min(targetItem.headerData.length - 1, Math.floor(yInItem / headerStride)))
            var header = targetItem.headerData[headerIndex]
            var headerId = String(header.id || "")
            if (headerId !== "" && headerId !== groupDragId) {
                groupDragDropMode = "into"
                groupDragTargetGroupId = headerId
                setGroupDragIndicator(
                    Math.max(14, Number(header.depth || 1) * 12 + 14),
                    targetItem.y + headerIndex * headerStride + root.groupHeaderHeight - 1,
                    Math.max(80, layerList.width - (Math.max(14, Number(header.depth || 1) * 12 + 24))))
                return
            }
        }

        if (!targetItem.layerContentShown) {
            clearGroupDragIndicator()
            return
        }
        var localY = y - (targetItem.y + targetItem.layerCardY)
        groupDragDropMode = localY < root.layerRowHeight * 0.5 ? "before" : "after"
        setGroupDragIndicator(
            targetItem.layerIndent + 8,
            targetItem.y + targetItem.layerCardY + (groupDragDropMode === "before" ? -1 : root.layerRowHeight - 1),
            Math.max(80, layerList.width - (targetItem.layerIndent + 18)))
    }

    function finishGroupDrag() {
        var groupId = groupDragId
        var target = groupDragTargetIndex
        var mode = groupDragDropMode
        var targetGroupId = groupDragTargetGroupId
        groupDragId = ""
        groupDragTargetIndex = -1
        groupDragTargetGroupId = ""
        groupDragDropMode = "before"
        clearGroupDragIndicator()
        if (groupId !== "" && target >= 0)
            backend.dropLayerGroup(groupId, target, mode, targetGroupId)
    }

    function beginGroupRename(groupId, name) {
        selectedGroupId = String(groupId || "")
        editingGroupId = String(groupId || "")
    }

    function finishGroupRename(groupId, name) {
        if (editingGroupId !== String(groupId || ""))
            return
        var clean = String(name || "").trim()
        editingGroupId = ""
        if (clean !== "")
            backend.renameLayerGroup(String(groupId), clean)
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

    function groupExists(groupId) {
        var key = String(groupId || "")
        return key !== "" && backend.layerGroupName(key) !== ""
    }

    function ensureSelectedGroupValid() {
        if (!groupExists(selectedGroupId))
            selectedGroupId = ""
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
            var modulation = algorithm === "Modulation"
            if (String(param.key).indexOf("color_mix_") === 0)
                return colourMix
            if (String(param.key).indexOf("modulation_") === 0) {
                if (!modulation)
                    return false
                var modulationMode = String(selectedParamValue("modulation_mode", "Smooth Diffuse"))
                if (param.key === "modulation_detail"
                        && (modulationMode === "Uniform Modulation X"
                            || modulationMode === "Uniform Modulation Y"
                            || modulationMode === "Ordered Modulation"))
                    return false
                return true
            }
            if (colourMix && (param.key === "strength" || param.key === "threshold" || param.key === "serpentine"))
                return false
            if (modulation && param.key === "threshold")
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
        function onLayerWorkflowChanged() {
            root.ensureSelectedGroupValid()
        }
        function onSettingsChanged() {
            root.ensureSelectedGroupValid()
        }
    }

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_F2 && root.groupExists(root.selectedGroupId)) {
            root.beginGroupRename(root.selectedGroupId, backend.layerGroupName(root.selectedGroupId))
            event.accepted = true
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
            Layout.preferredHeight: Math.min(contentHeight, 300)
            model: backend.layerModel
            spacing: root.layerRowSpacing
            clip: true
            currentIndex: backend.selectedLayerIndex
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Item {
                id: layerDelegate
                width: layerList.width

                property bool fixedStage: kind === "Hardware Limits" || kind === "Hardware Display"
                property bool isDragging: root.dragSourceIndex === index
                property bool multiSelected: backend.selectedLayerIndices.indexOf(index) >= 0
                property var headerData: groupHeaders || []
                property bool layerContentShown: Boolean(layerContentVisible)
                property bool authoredLayerEnabled: Boolean(layerEnabled)
                property bool layerSoloTarget: backend.layerSolo(index)
                property real headerAreaHeight: headerData.length > 0
                                                ? headerData.length * (root.groupHeaderHeight + 2)
                                                : 0
                property real layerCardY: headerAreaHeight
                property real layerIndent: Math.max(0, Number(groupDepth || 0)) * 12

                visible: height > 0
                height: headerAreaHeight + (layerContentShown ? root.layerRowHeight : 0)
                z: isDragging ? 30 : 0

                Column {
                    id: groupHeaderColumn
                    width: parent.width
                    spacing: 2

                    Repeater {
                        model: layerDelegate.headerData

                        delegate: Rectangle {
                            id: groupHeader
                            required property var modelData
                            property bool groupModelReady: groupHeader.modelData !== undefined && groupHeader.modelData !== null
                            property string groupIdText: String(groupModelReady && groupHeader.modelData.id ? groupHeader.modelData.id : "")
                            property bool groupEnabledState: Boolean(groupModelReady && groupHeader.modelData.enabled)
                            property bool groupSoloTarget: backend.layerGroupSolo(groupIdText)
                            property bool groupIsDragging: root.groupDragId === groupIdText
                            x: Math.max(0, (Number(modelData.depth || 1) - 1) * 12)
                            width: Math.max(80, groupHeaderColumn.width - x)
                            height: root.groupHeaderHeight
                            radius: 6
                            readonly property string groupColorCode: String(groupHeader.groupModelReady && groupHeader.modelData.color_label ? groupHeader.modelData.color_label : "")
                            readonly property color tintedBaseColor: groupColorCode !== ""
                                                                     ? Qt.tint(theme.panelColor, Qt.alpha(groupColorCode, groupHeaderHover.hovered ? 0.28 : 0.20))
                                                                     : (groupHeaderHover.hovered ? theme.panelHoverColor : theme.panelColor)
                            color: groupIsDragging
                                   ? theme.selectionColor
                                   : (root.selectedGroupId === groupHeader.groupIdText
                                      ? Qt.tint(tintedBaseColor, Qt.alpha(theme.accentColor, 0.20))
                                      : tintedBaseColor)
                            border.color: groupIsDragging || root.selectedGroupId === groupHeader.groupIdText
                                          ? theme.accentColor : theme.borderColor
                            border.width: groupIsDragging || root.selectedGroupId === groupHeader.groupIdText ? 2 : 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 6

                                MintButton {
                                    id: collapseGroupButton
                                    Layout.preferredWidth: 27
                                    Layout.preferredHeight: 25
                                    text: Boolean(groupHeader.modelData.collapsed) ? "▸" : "▾"
                                    onClicked: backend.setLayerGroupCollapsed(
                                                   groupHeader.groupIdText,
                                                   !Boolean(groupHeader.modelData.collapsed))
                                    MintToolTip {
                                        visible: collapseGroupButton.hovered
                                        text: qsTr("Collapse / expand layer group")
                                    }
                                }

                                Rectangle {
                                    Layout.preferredWidth: 28
                                    Layout.preferredHeight: 28
                                    radius: 8
                                    color: groupHeader.groupSoloTarget ? Qt.alpha(theme.accentColor, 0.18) : "transparent"
                                    border.color: groupHeader.groupSoloTarget ? theme.accentColor : "transparent"
                                    border.width: groupHeader.groupSoloTarget ? 2 : 0

                                    MintCheckBox {
                                        id: groupEnabledToggle
                                        anchors.centerIn: parent
                                        checked: Boolean(backend.soloActive
                                                         ? backend.layerGroupEffectiveEnabled(groupHeader.groupIdText)
                                                         : groupHeader.groupEnabledState)

                                        MouseArea {
                                            id: groupEnabledToggleMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            acceptedButtons: Qt.LeftButton
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: function(mouse) {
                                                root.selectedGroupId = groupHeader.groupIdText
                                                if (mouse.modifiers & Qt.AltModifier)
                                                    backend.toggleSoloLayerGroup(groupHeader.groupIdText)
                                                else
                                                    backend.setLayerGroupEnabled(
                                                        groupHeader.groupIdText,
                                                        !groupHeader.groupEnabledState)
                                            }
                                        }

                                        MintToolTip {
                                            visible: groupEnabledToggleMouse.containsMouse
                                            delay: 350
                                            text: qsTr("Alt+Click to solo this group")
                                        }
                                    }
                                }

                                Item {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true

                                    Text {
                                        anchors.fill: parent
                                        verticalAlignment: Text.AlignVCenter
                                        text: String(groupHeader.groupModelReady && groupHeader.modelData.name ? groupHeader.modelData.name : "")
                                        color: theme.textColor
                                        font.bold: true
                                        elide: Text.ElideRight
                                        visible: root.editingGroupId !== groupHeader.groupIdText
                                    }

                                    MintTextField {
                                        id: groupNameEditor
                                        anchors.fill: parent
                                        visible: root.editingGroupId === groupHeader.groupIdText
                                        onVisibleChanged: {
                                            if (visible) {
                                                text = String(groupHeader.groupModelReady && groupHeader.modelData.name ? groupHeader.modelData.name : "")
                                                forceActiveFocus()
                                                selectAll()
                                            }
                                        }
                                        Keys.onReturnPressed: root.finishGroupRename(groupHeader.groupIdText, text)
                                        Keys.onEnterPressed: root.finishGroupRename(groupHeader.groupIdText, text)
                                        Keys.onEscapePressed: root.editingGroupId = ""
                                        onEditingFinished: {
                                            if (root.editingGroupId === groupHeader.groupIdText)
                                                root.finishGroupRename(groupHeader.groupIdText, text)
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: root.editingGroupId !== groupHeader.groupIdText
                                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                                        onClicked: function(mouse) {
                                            root.selectedGroupId = groupHeader.groupIdText
                                            if (mouse.button === Qt.RightButton)
                                                backend.ungroupLayerGroup(groupHeader.groupIdText)
                                        }
                                        onDoubleClicked: {
                                            root.selectedGroupId = groupHeader.groupIdText
                                            root.beginGroupRename(groupHeader.groupIdText, groupHeader.groupModelReady ? groupHeader.modelData.name : "")
                                        }
                                    }
                                }
                            }

                            HoverHandler { id: groupHeaderHover }

                            Timer {
                                interval: 700
                                repeat: false
                                running: Boolean(groupHeader.modelData.collapsed)
                                         && (root.dragSourceIndex >= 0 || root.groupDragId !== "")
                                         && (!groupIsDragging)
                                         && ((root.dragTargetIndex === index && root.dragDropMode === "into")
                                             || root.groupDragTargetIndex === index)
                                onTriggered: backend.setLayerGroupCollapsed(groupHeader.groupIdText, false)
                            }

                            MintToolTip {
                                visible: groupHeaderHover.hovered
                                         && !groupEnabledToggleMouse.containsMouse
                                         && !collapseGroupButton.hovered
                                         && !groupIsDragging
                                delay: 450
                                timeout: 10000
                                text: {
                                    var parts = []
                                    parts.push(String(groupHeader.groupModelReady && groupHeader.modelData.name ? groupHeader.modelData.name : ""))
                                    var mix = []
                                    mix.push(Math.round(Number(groupHeader.modelData.opacity || 1) * 100) + "%")
                                    mix.push(qsTr(String(groupHeader.modelData.blend_mode || "Normal")))
                                    if (String(groupHeader.modelData.note || "") !== "")
                                        parts.push(String(groupHeader.modelData.note))
                                    parts.push(mix.join(" · "))
                                    return parts.join("\n")
                                }
                            }

                            DragHandler {
                                id: groupDrag
                                enabled: root.editingGroupId !== groupHeader.groupIdText
                                target: null
                                acceptedButtons: Qt.LeftButton
                                xAxis.enabled: false
                                yAxis.enabled: true
                                onActiveChanged: {
                                    if (active) {
                                        root.beginGroupDrag(groupHeader.groupIdText)
                                    } else if (root.groupDragId === groupHeader.groupIdText) {
                                        root.finishGroupDrag()
                                    }
                                }
                                onTranslationChanged: {
                                    if (!active)
                                        return
                                    var point = groupHeader.mapToItem(
                                                layerList,
                                                groupHeader.width / 2,
                                                groupHeader.height / 2 + translation.y)
                                    root.updateGroupDragAt(point.y)
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    id: layerCard
                    x: layerDelegate.layerIndent
                    y: layerDelegate.layerCardY
                    width: Math.max(90, layerDelegate.width - x)
                    height: layerDelegate.layerContentShown ? root.layerRowHeight : 0
                    visible: layerDelegate.layerContentShown
                    radius: 7
                    z: layerDelegate.isDragging ? 20 : 0
                    color: layerDelegate.multiSelected
                           ? theme.selectionColor
                           : (layerHover.hovered ? theme.panelHoverColor : theme.panelRaisedColor)
                    border.color: layerDelegate.isDragging ? theme.accentColor : theme.borderColor
                    border.width: layerDelegate.isDragging ? 2 : 1
                    opacity: layerDelegate.isDragging ? 0.88 : 1.0

                    transform: Translate {
                        x: layerDelegate.isDragging ? root.dragDeltaX : 0
                        y: layerDelegate.isDragging ? root.dragDeltaY : 0
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 7
                        spacing: 7

                        Rectangle {
                            Layout.preferredWidth: 28
                            Layout.preferredHeight: 28
                            radius: 8
                            color: layerDelegate.layerSoloTarget ? Qt.alpha(theme.accentColor, 0.18) : "transparent"
                            border.color: layerDelegate.layerSoloTarget ? theme.accentColor : "transparent"
                            border.width: layerDelegate.layerSoloTarget ? 2 : 0

                            MintCheckBox {
                                id: layerEnabledToggle
                                anchors.centerIn: parent
                                checked: Boolean(backend.soloActive ? backend.layerEffectiveEnabled(index) : layerDelegate.authoredLayerEnabled)

                                MouseArea {
                                    id: layerEnabledToggleMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    acceptedButtons: Qt.LeftButton
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: function(mouse) {
                                        root.selectedGroupId = ""
                                        backend.selectLayer(index)
                                        if (mouse.modifiers & Qt.AltModifier)
                                            backend.toggleSoloLayer(index)
                                        else
                                            backend.setLayerEnabled(index, !layerDelegate.authoredLayerEnabled)
                                    }
                                }

                                MintToolTip {
                                    visible: layerEnabledToggleMouse.containsMouse
                                    delay: 350
                                    text: qsTr("Alt+Click to solo this layer")
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1
                            Text {
                                Layout.fillWidth: true
                                text: qsTr(kind)
                                color: theme.textColor
                                font.bold: true
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                readonly property string maskType: String((layerMask && layerMask.type) || "None")
                                readonly property string compositingSummary: {
                                    var parts = []
                                    if (String(blendMode || "Normal") !== "Normal" || Number(layerOpacity) < 0.999) {
                                        parts.push(qsTr(String(blendMode || "Normal")))
                                        parts.push(Math.round(Number(layerOpacity) * 100) + "%")
                                    }
                                    if (maskType !== "None")
                                        parts.push(qsTr(maskType))
                                    return parts.join(" · ")
                                }
                                text: compositingSummary
                                      + (compositingSummary !== "" && String(summary) !== "" ? " · " : "")
                                      + qsTr(summary)
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
                        onTapped: {
                            root.selectedGroupId = ""
                            backend.selectLayer(index)
                        }
                    }
                    TapHandler {
                        acceptedModifiers: Qt.ControlModifier
                        onTapped: {
                            root.selectedGroupId = ""
                            backend.toggleLayerSelection(index)
                        }
                    }
                    TapHandler {
                        acceptedModifiers: Qt.ShiftModifier
                        onTapped: {
                            root.selectedGroupId = ""
                            backend.selectLayerRange(index)
                        }
                    }

                    DragHandler {
                        id: cardDrag
                        enabled: !layerDelegate.fixedStage
                        target: null
                        acceptedButtons: Qt.LeftButton
                        xAxis.enabled: true
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
                                root.updateLayerDrag(translation.x, translation.y)
                        }
                    }

                    MintToolTip {
                        visible: layerHover.hovered
                                 && !layerEnabledToggleMouse.containsMouse
                                 && !cardDrag.active
                                 && root.effectDescription(kind) !== ""
                        delay: 500
                        timeout: 10000
                        text: root.effectDescription(kind)
                    }
                }
            }

            Rectangle {
                parent: layerList.contentItem
                x: root.dragIndicatorX
                y: root.dragIndicatorY
                width: root.dragIndicatorWidth
                height: 3
                radius: 2
                color: theme.accentColor
                visible: root.dragSourceIndex >= 0 && root.dragIndicatorY >= 0 && root.dragDropMode !== "ungroup"
                z: 40
            }

            Rectangle {
                parent: layerList.contentItem
                x: root.groupDragIndicatorX
                y: root.groupDragIndicatorY
                width: root.groupDragIndicatorWidth
                height: 3
                radius: 2
                color: theme.accentColor
                visible: root.groupDragId !== "" && root.groupDragIndicatorY >= 0
                z: 40
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            MintButton {
                Layout.fillWidth: true
                text: root.groupExists(root.selectedGroupId) ? qsTr("Duplicate Group") : qsTr("Duplicate")
                enabled: root.groupExists(root.selectedGroupId)
                         || (backend.selectedLayerName !== "Hardware Limits" && backend.selectedLayerName !== "Hardware Display")
                onClicked: {
                    if (root.groupExists(root.selectedGroupId))
                        backend.duplicateLayerGroup(root.selectedGroupId)
                    else
                        backend.duplicateSelectedLayer()
                }
            }
            MintButton {
                Layout.fillWidth: true
                text: qsTr("Copy")
                enabled: !root.groupExists(root.selectedGroupId)
                onClicked: backend.copySelectedLayerSettings()
            }
            MintButton {
                Layout.fillWidth: true
                text: qsTr("Paste")
                enabled: !root.groupExists(root.selectedGroupId) && backend.layerClipboardAvailable
                onClicked: backend.pasteSelectedLayerSettings()
            }
            MintButton {
                Layout.fillWidth: true
                text: qsTr("Reset")
                enabled: !root.groupExists(root.selectedGroupId)
                onClicked: backend.resetSelectedLayer()
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            MintButton {
                Layout.fillWidth: true
                text: root.groupExists(root.selectedGroupId)
                      ? (backend.layerGroupSolo(root.selectedGroupId) ? qsTr("Unsolo Group") : qsTr("Solo Group"))
                      : (backend.selectedLayerSolo ? qsTr("Unsolo") : qsTr("Solo"))
                onClicked: {
                    if (root.groupExists(root.selectedGroupId))
                        backend.toggleSoloLayerGroup(root.selectedGroupId)
                    else
                        backend.toggleSoloSelectedLayer()
                }
            }
            MintButton { Layout.fillWidth: true; text: qsTr("Group"); onClicked: backend.groupSelectedLayers() }
            MintButton {
                Layout.fillWidth: true
                text: root.groupExists(root.selectedGroupId) ? qsTr("Ungroup Group") : qsTr("Ungroup")
                onClicked: {
                    if (root.groupExists(root.selectedGroupId))
                        backend.ungroupLayerGroup(root.selectedGroupId)
                    else
                        backend.ungroupSelectedLayers()
                }
            }
            MintButton {
                Layout.fillWidth: true
                enabled: !root.groupExists(root.selectedGroupId)
                text: backend.selectedLayerIndices.length > 1 ? qsTr("Remove %1").arg(backend.selectedLayerIndices.length) : qsTr("Remove")
                onClicked: backend.removeSelectedLayers()
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            visible: root.groupExists(root.selectedGroupId)

            MintLabel {
                text: qsTr("Selected group") + ": " + String(root.selectedGroupData.name || "")
                font.bold: true
            }
            MintLabel {
                Layout.fillWidth: true
                text: qsTr("%1 layer(s) inside this hierarchy").arg(backend.layerGroupCount(root.selectedGroupId))
                color: theme.mutedTextColor
                font.pixelSize: 10
            }
            RowLayout {
                Layout.fillWidth: true
                MintLabel { text: qsTr("Opacity"); color: theme.mutedTextColor; Layout.fillWidth: true }
                MintLabel { text: Math.round(Number(root.selectedGroupData.opacity || 1) * 100) + "%" }
            }
            MintSlider {
                Layout.fillWidth: true
                from: 0; to: 1; stepSize: 0.01
                value: Number(root.selectedGroupData.opacity || 1)
                onInteractionActiveChanged: {
                    if (interactionActive) backend.beginHistoryGroup(backend.layerGroupName(root.selectedGroupId) + " · Group Opacity")
                    else backend.endHistoryGroup()
                }
                onUserMoved: function(newValue) { backend.setLayerGroupOpacity(root.selectedGroupId, newValue) }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                MintLabel { text: qsTr("Blend mode"); color: theme.mutedTextColor }
                MintComboBox {
                    Layout.fillWidth: true
                    model: backend.layerBlendModes
                    currentIndex: Math.max(0, backend.layerBlendModes.indexOf(String(root.selectedGroupData.blend_mode || "Normal")))
                    onActivated: backend.setLayerGroupBlendMode(root.selectedGroupId, currentText)
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Rectangle {
                    Layout.preferredWidth: visible ? 12 : 0
                    Layout.preferredHeight: visible ? 12 : 0
                    radius: 6
                    visible: String(root.selectedGroupData.color_label || "") !== ""
                    color: String(root.selectedGroupData.color_label || "")
                    border.width: 0
                }
                MintComboBox {
                    id: groupColorCombo
                    Layout.fillWidth: true
                    model: root.groupColorOptions.map(function(item) { return item.name })
                    currentIndex: {
                        var current = String(root.selectedGroupData.color_label || "")
                        for (var i = 0; i < root.groupColorOptions.length; ++i) {
                            if (String(root.groupColorOptions[i].value) === String(current))
                                return i
                        }
                        return 0
                    }
                    onActivated: backend.setLayerGroupColor(root.selectedGroupId, root.groupColorOptions[currentIndex].value)
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                MintLabel { text: qsTr("Group note"); color: theme.mutedTextColor }
                MintTextField {
                    Layout.fillWidth: true
                    text: String(root.selectedGroupData.note || "")
                    placeholderText: qsTr("Example: CRT finishing pass")
                    onEditingFinished: backend.setLayerGroupNote(root.selectedGroupId, text)
                }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
        MintLabel { text: localization.translateRuntime(localization.effectiveLanguageId, String(backend.selectedLayerName)); font.bold: true }
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
                        currentIndex: Math.max(0, backend.layerBlendModes.indexOf(backend.selectedLayerBlendMode))
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
                        currentIndex: Math.max(0, backend.layerMaskTypes.indexOf(String(backend.selectedLayerMask.type || "None")))
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

    function effectDescription(kind) {
        var target = String(kind || "")
        var categories = backend.layerCategories || []
        for (var i = 0; i < categories.length; ++i) {
            var descriptions = categories[i].descriptions || {}
            var raw = String(descriptions[target] || "")
            if (raw !== "")
                return localization.translateRuntime(localization.effectiveLanguageId, raw)
        }
        return ""
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
                                    text: localization.translateRuntime(localization.effectiveLanguageId, String(categoryDelegate.modelData.name))
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
                                    id: effectDelegate
                                    required property var modelData
                                    readonly property string effectDescription: root.effectDescription(modelData)
                                    Layout.fillWidth: true
                                    implicitHeight: 32
                                    leftPadding: 28
                                    contentItem: Text {
                                        text: localization.translateRuntime(localization.effectiveLanguageId, String(effectDelegate.modelData))
                                        color: theme.textColor
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                    }
                                    background: Rectangle {
                                        radius: 5
                                        color: effectDelegate.hovered ? theme.selectionColor : "transparent"
                                    }
                                    MintToolTip {
                                        visible: effectDelegate.hovered && effectDelegate.effectDescription !== ""
                                        delay: 450
                                        timeout: 10000
                                        text: effectDelegate.effectDescription
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
            text: localization.translateRuntime(localization.effectiveLanguageId, String(param.label)) + (param.animated ? "  · " + qsTr("animated") : "")
            checked: Boolean(param.value)
            enabled: !param.animated
            onToggled: backend.setLayerParam(param.key, checked)
        }
    }

    Component {
        id: choiceEditor
        ColumnLayout {
            spacing: 4
            MintLabel { text: localization.translateRuntime(localization.effectiveLanguageId, String(param.label)); color: theme.mutedTextColor }
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
            MintLabel { text: localization.translateRuntime(localization.effectiveLanguageId, String(param.label)); color: theme.mutedTextColor }
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
            MintLabel { text: localization.translateRuntime(localization.effectiveLanguageId, String(param.label)); color: theme.mutedTextColor }
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
            MintLabel { text: localization.translateRuntime(localization.effectiveLanguageId, String(param.label)); color: theme.mutedTextColor }

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
                                            text: localization.translateRuntime(localization.effectiveLanguageId, String(glyphCategoryDelegate.modelData.name))
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
                                                    text: localization.translateRuntime(localization.effectiveLanguageId, String(glyphSetItem.modelData.name))
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
                text: localization.translateRuntime(localization.effectiveLanguageId, String(param.label)) + (param.animated ? "  · " + qsTr("animated") : "")
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
                    text: localization.translateRuntime(localization.effectiveLanguageId, String(param.label)) + (param.animated ? "  · " + qsTr("animated") : "")
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
