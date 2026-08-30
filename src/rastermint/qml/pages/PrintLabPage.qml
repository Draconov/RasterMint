import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Item {
    id: root
    property var state: backend.printLabState || ({})
    property bool setupExpanded: true
    property bool inksExpanded: true
    property bool registrationExpanded: false
    property bool imperfectionsExpanded: false
    property bool outputExpanded: true

    function setParam(key, value) { backend.setPrintLabParam(key, value) }
    function inkCount() {
        if (state.mode === "Monochrome") return 1
        if (state.mode === "CMYK") return 4
        if (state.mode === "RGB") return 3
        return Math.max(1, Math.min(8, Number(state.ink_count || 4)))
    }
    function inkName(index) {
        if (state.mode === "CMYK") return ["Cyan", "Magenta", "Yellow", "Black"][index]
        if (state.mode === "RGB") return ["Red", "Green", "Blue"][index]
        if (state.mode === "Monochrome") return "Black"
        return "Spot " + String(index + 1)
    }
    function previewChoices() {
        var list = ["Composite"]
        for (var i = 0; i < inkCount(); ++i) list.push(inkName(i))
        return list
    }

    component SectionHeader: Rectangle {
        id: sectionRoot
        property string titleText: ""
        property bool expanded: false
        signal toggled()
        Layout.fillWidth: true
        implicitHeight: 34
        radius: 5
        color: headerMouse.containsMouse ? theme.panelHoverColor : theme.panelRaisedColor
        border.color: theme.borderColor
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 9; anchors.rightMargin: 9
            Text { text: sectionRoot.expanded ? "▾" : "▸"; color: theme.accentColor; font.bold: true }
            MintLabel { text: sectionRoot.titleText; font.bold: true; Layout.fillWidth: true }
        }
        MouseArea { id: headerMouse; anchors.fill: parent; hoverEnabled: true; onClicked: sectionRoot.toggled() }
    }

    component LabeledSlider: ColumnLayout {
        id: labeledRoot
        property string labelText: ""
        property real fromValue: 0
        property real toValue: 1
        property real stepValue: 0.01
        property real currentValue: 0
        property int decimals: 2
        property string suffix: ""
        signal changed(real value)
        Layout.fillWidth: true
        spacing: 2
        RowLayout {
            Layout.fillWidth: true
            MintLabel { text: labeledRoot.labelText; color: theme.mutedTextColor; Layout.fillWidth: true }
            MintLabel { text: Number(slider.displayValue).toFixed(labeledRoot.decimals) + labeledRoot.suffix }
        }
        MintSlider {
            id: slider
            Layout.fillWidth: true
            from: labeledRoot.fromValue; to: labeledRoot.toValue; stepSize: labeledRoot.stepValue; value: labeledRoot.currentValue
            onInteractionActiveChanged: {
                if (interactionActive) backend.beginHistoryGroup("Print Lab · " + labeledRoot.labelText)
                else backend.endHistoryGroup()
            }
            onUserMoved: function(v) { labeledRoot.changed(v) }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true; spacing: 1
                MintLabel { text: qsTr("Print Lab"); font.bold: true; font.pixelSize: 16 }
                MintLabel {
                    Layout.fillWidth: true
                    text: qsTr("AM halftone, screen-print simulation and real separation artwork.")
                    color: theme.mutedTextColor; wrapMode: Text.WordWrap; font.pixelSize: 10
                }
            }
            MintButton {
                visible: !root.state.active
                text: qsTr("Add Print Lab")
                onClicked: backend.ensurePrintLab()
            }
            MintCheckBox {
                visible: root.state.active
                checked: Boolean(root.state.enabled)
                text: qsTr("Enabled")
                onToggled: backend.setPrintLabEnabled(checked)
            }
        }

        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: theme.borderColor }

        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; contentWidth: availableWidth
            ColumnLayout {
                width: parent.width
                spacing: 7
                enabled: root.state.active
                opacity: enabled ? 1.0 : 0.55

                SectionHeader { titleText: qsTr("Print Setup"); expanded: root.setupExpanded; onToggled: root.setupExpanded = !root.setupExpanded }
                ColumnLayout {
                    Layout.fillWidth: true; visible: root.setupExpanded; spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        MintLabel { text: qsTr("Mode"); Layout.preferredWidth: 110; color: theme.mutedTextColor }
                        MintComboBox {
                            Layout.fillWidth: true
                            model: ["Monochrome", "CMYK", "RGB", "Spot Colors"]
                            translateModel: true
                            currentIndex: Math.max(0, model.indexOf(String(root.state.mode || "CMYK")))
                            onActivated: root.setParam("mode", currentText)
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true; visible: root.state.mode === "Spot Colors"
                        MintLabel { text: qsTr("Spot inks"); Layout.preferredWidth: 110; color: theme.mutedTextColor }
                        MintSpinBox {
                            from: 1; to: 8; value: Number(root.state.ink_count || 4)
                            onValueModified: root.setParam("ink_count", value)
                        }
                    }
                    MintButton {
                        visible: root.state.mode === "Spot Colors"
                        text: qsTr("Use Active Palette as Spot Inks")
                        onClicked: backend.usePaletteForSpotInks()
                    }
                    LabeledSlider { labelText: qsTr("Cell size / frequency"); fromValue: 2; toValue: 128; stepValue: 1; decimals: 0; suffix: " px"; currentValue: Number(root.state.cell_size || 8); onChanged: function(v) { root.setParam("cell_size", Math.round(v)) } }
                    RowLayout {
                        Layout.fillWidth: true
                        MintLabel { text: qsTr("Dot shape"); Layout.preferredWidth: 110; color: theme.mutedTextColor }
                        MintComboBox {
                            Layout.fillWidth: true
                            model: ["Round", "Ellipse", "Square", "Diamond", "Line"]
                            translateModel: true
                            currentIndex: Math.max(0, model.indexOf(String(root.state.dot_shape || "Round")))
                            onActivated: root.setParam("dot_shape", currentText)
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        MintLabel { text: qsTr("Paper colour"); Layout.fillWidth: true; color: theme.mutedTextColor }
                        MintColorPicker {
                            Layout.preferredWidth: 150; alphaEnabled: false
                            colorValue: String(root.state.paper_color || "#F5F0E5")
                            onColorPicked: function(value) { root.setParam("paper_color", value) }
                        }
                    }
                    LabeledSlider { labelText: qsTr("Dot gain"); fromValue: -50; toValue: 100; stepValue: 1; decimals: 0; suffix: "%"; currentValue: Number(root.state.dot_gain || 0); onChanged: function(v) { root.setParam("dot_gain", v) } }
                    LabeledSlider { visible: root.state.mode === "CMYK"; labelText: qsTr("Black generation / mix"); fromValue: 0; toValue: 100; stepValue: 1; decimals: 0; suffix: "%"; currentValue: Number(root.state.black_mix === undefined ? 100 : root.state.black_mix); onChanged: function(v) { root.setParam("black_mix", v) } }
                    MintCheckBox { text: qsTr("Subtractive overprint / ink mixing"); checked: Boolean(root.state.overprint); onToggled: root.setParam("overprint", checked) }
                }

                SectionHeader { titleText: qsTr("Separations / Inks"); expanded: root.inksExpanded; onToggled: root.inksExpanded = !root.inksExpanded }
                ColumnLayout {
                    Layout.fillWidth: true; visible: root.inksExpanded; spacing: 8
                    Repeater {
                        model: root.state.active && root.inksExpanded ? root.inkCount() : 0
                        delegate: Rectangle {
                            required property int index
                            Layout.fillWidth: true
                            implicitHeight: inkColumn.implicitHeight + 14
                            radius: 6; color: theme.panelRaisedColor; border.color: theme.borderColor
                            ColumnLayout {
                                id: inkColumn; anchors { left: parent.left; right: parent.right; top: parent.top; margins: 7 }; spacing: 5
                                RowLayout {
                                    Layout.fillWidth: true
                                    MintLabel { text: localization.translateRuntime(localization.effectiveLanguageId, root.inkName(index)); font.bold: true; Layout.fillWidth: true }
                                    MintColorPicker {
                                        Layout.preferredWidth: 145; alphaEnabled: false
                                        colorValue: String(root.state["ink" + (index + 1) + "_color"] || "#000000")
                                        onColorPicked: function(value) { root.setParam("ink" + (index + 1) + "_color", value) }
                                    }
                                }
                                LabeledSlider { labelText: qsTr("Screen angle"); fromValue: -180; toValue: 180; stepValue: 1; decimals: 1; suffix: "°"; currentValue: Number(root.state["ink" + (index + 1) + "_angle"] || 0); onChanged: function(v) { root.setParam("ink" + (index + 1) + "_angle", v) } }
                                LabeledSlider { labelText: qsTr("Ink opacity"); fromValue: 0; toValue: 1; stepValue: 0.01; decimals: 2; currentValue: Number(root.state["ink" + (index + 1) + "_opacity"] === undefined ? 1 : root.state["ink" + (index + 1) + "_opacity"]); onChanged: function(v) { root.setParam("ink" + (index + 1) + "_opacity", v) } }
                            }
                        }
                    }
                }

                SectionHeader { titleText: qsTr("Registration"); expanded: root.registrationExpanded; onToggled: root.registrationExpanded = !root.registrationExpanded }
                ColumnLayout {
                    Layout.fillWidth: true; visible: root.registrationExpanded; spacing: 7
                    LabeledSlider { labelText: qsTr("Automatic registration error"); fromValue: 0; toValue: 64; stepValue: 0.25; decimals: 2; suffix: " px"; currentValue: Number(root.state.registration_error || 0); onChanged: function(v) { root.setParam("registration_error", v) } }
                    MintCheckBox { text: qsTr("Enable custom phase offsets"); checked: Boolean(root.state.phase_offsets); onToggled: root.setParam("phase_offsets", checked) }
                    Repeater {
                        model: root.state.active && root.registrationExpanded ? root.inkCount() : 0
                        delegate: ColumnLayout {
                            required property int index
                            Layout.fillWidth: true; spacing: 4
                            MintLabel { text: localization.translateRuntime(localization.effectiveLanguageId, root.inkName(index)); font.bold: true }
                            LabeledSlider { labelText: qsTr("X registration"); fromValue: -128; toValue: 128; stepValue: 0.25; decimals: 2; suffix: " px"; currentValue: Number(root.state["ink" + (index + 1) + "_offset_x"] || 0); onChanged: function(v) { root.setParam("ink" + (index + 1) + "_offset_x", v) } }
                            LabeledSlider { labelText: qsTr("Y registration"); fromValue: -128; toValue: 128; stepValue: 0.25; decimals: 2; suffix: " px"; currentValue: Number(root.state["ink" + (index + 1) + "_offset_y"] || 0); onChanged: function(v) { root.setParam("ink" + (index + 1) + "_offset_y", v) } }
                            LabeledSlider { visible: Boolean(root.state.phase_offsets); labelText: qsTr("Phase X"); fromValue: -1; toValue: 1; stepValue: 0.05; decimals: 2; currentValue: Number(root.state["ink" + (index + 1) + "_phase_x"] || 0); onChanged: function(v) { root.setParam("ink" + (index + 1) + "_phase_x", v) } }
                            LabeledSlider { visible: Boolean(root.state.phase_offsets); labelText: qsTr("Phase Y"); fromValue: -1; toValue: 1; stepValue: 0.05; decimals: 2; currentValue: Number(root.state["ink" + (index + 1) + "_phase_y"] || 0); onChanged: function(v) { root.setParam("ink" + (index + 1) + "_phase_y", v) } }
                        }
                    }
                }

                SectionHeader { titleText: qsTr("Print Imperfections"); expanded: root.imperfectionsExpanded; onToggled: root.imperfectionsExpanded = !root.imperfectionsExpanded }
                ColumnLayout {
                    Layout.fillWidth: true; visible: root.imperfectionsExpanded; spacing: 6
                    LabeledSlider { labelText: qsTr("Screen roughness"); fromValue: 0; toValue: 1; stepValue: 0.01; currentValue: Number(root.state.roughness || 0); onChanged: function(v) { root.setParam("roughness", v) } }
                    LabeledSlider { labelText: qsTr("Missing / weak ink"); fromValue: 0; toValue: 1; stepValue: 0.01; currentValue: Number(root.state.missing_ink || 0); onChanged: function(v) { root.setParam("missing_ink", v) } }
                    LabeledSlider { labelText: qsTr("Irregular ink spread"); fromValue: 0; toValue: 1; stepValue: 0.01; currentValue: Number(root.state.ink_spread || 0); onChanged: function(v) { root.setParam("ink_spread", v) } }
                    LabeledSlider { labelText: qsTr("Paper grain interaction"); fromValue: 0; toValue: 1; stepValue: 0.01; currentValue: Number(root.state.paper_grain || 0); onChanged: function(v) { root.setParam("paper_grain", v) } }
                    LabeledSlider { labelText: qsTr("Squeegee / coverage artifacts"); fromValue: 0; toValue: 1; stepValue: 0.01; currentValue: Number(root.state.squeegee || 0); onChanged: function(v) { root.setParam("squeegee", v) } }
                }

                SectionHeader { titleText: qsTr("Output"); expanded: root.outputExpanded; onToggled: root.outputExpanded = !root.outputExpanded }
                ColumnLayout {
                    Layout.fillWidth: true; visible: root.outputExpanded; spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        MintLabel { text: qsTr("Preview"); Layout.preferredWidth: 110; color: theme.mutedTextColor }
                        MintComboBox {
                            Layout.fillWidth: true
                            model: root.previewChoices()
                            translateModel: true
                            currentIndex: Math.max(0, model.indexOf(String(root.state.preview || "Composite")))
                            onActivated: root.setParam("preview", currentText)
                        }
                    }
                    MintLabel {
                        Layout.fillWidth: true
                        text: qsTr("Separation export writes actual vector SVG screen geometry, optional raster proofs, and a composite PNG.")
                        color: theme.mutedTextColor; wrapMode: Text.WordWrap; font.pixelSize: 10
                    }
                    MintButton { text: qsTr("Export Separations…"); enabled: backend.hasSource; onClicked: separationFolder.open() }
                }
                Item { Layout.preferredHeight: 8 }
            }
        }
    }

    FolderDialog {
        id: separationFolder
        title: qsTr("Choose separation export folder")
        onAccepted: backend.exportPrintSeparations(selectedFolder.toString())
    }
}
