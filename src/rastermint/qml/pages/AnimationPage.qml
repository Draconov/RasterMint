import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root
    contentWidth: availableWidth
    property int selectedTrack: -1
    property int selectedKey: -1
    property var playbackModeValues: ["Quick", "Rendered"]

    function selectedTrackData() {
        var tracks = backend.animationTracks || []
        return selectedTrack >= 0 && selectedTrack < tracks.length ? tracks[selectedTrack] : null
    }

    function selectedKeyData() {
        var track = selectedTrackData()
        var keys = track ? (track.keyframes || []) : []
        return selectedKey >= 0 && selectedKey < keys.length ? keys[selectedKey] : null
    }

    function loadKey(index) {
        selectedKey = index
        var key = selectedKeyData()
        if (!key) return
        keyTimeField.text = Number(key.time).toFixed(3)
        keyValueField.text = Number(key.value).toString()
        keyEasingCombo.currentIndex = Math.max(0, backend.easingNames.indexOf(String(key.easing || "Linear")))
        var bezier = key.bezier || [0.25, 0.1, 0.25, 1.0]
        bezierX1.text = Number(bezier[0]).toFixed(2)
        bezierY1.text = Number(bezier[1]).toFixed(2)
        bezierX2.text = Number(bezier[2]).toFixed(2)
        bezierY2.text = Number(bezier[3]).toFixed(2)
    }
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff

    function resetEditorFromTarget() {
        if (targetCombo.currentIndex < 0 || targetCombo.currentIndex >= backend.animationTargets.length) return
        var target = backend.animationTargets[targetCombo.currentIndex]
        fromField.text = Number(target.default).toFixed(target.decimals)
        toField.text = Number(target.default).toFixed(target.decimals)
        startField.text = "0.00"
        endField.text = Number(backend.timelineDuration).toFixed(2)
    }

    function loadTrack(row) {
        selectedTrack = row.index
        selectedKey = -1
        var targetIndex = backend.animationTargetIds.indexOf(row.target)
        targetCombo.currentIndex = Math.max(0, targetIndex)
        fromField.text = Number(row.from).toString()
        toField.text = Number(row.to).toString()
        startField.text = Number(row.start).toFixed(2)
        endField.text = Number(row.end).toFixed(2)
        easingCombo.currentIndex = Math.max(0, backend.easingNames.indexOf(row.easing))
    }

    ColumnLayout {
        width: root.availableWidth
        spacing: 9

        MintLabel { text: qsTr("Animation"); font.bold: true; font.pixelSize: 15 }
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                MintLabel { text: qsTr("Duration (s)"); color: theme.mutedTextColor }
                MintTextField {
                    Layout.fillWidth: true
                    text: Number(backend.settingsMap.animation_duration).toFixed(2)
                    validator: DoubleValidator { bottom: 0.1; top: 600 }
                    onEditingFinished: backend.setSetting("animation_duration", Number(text))
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                MintLabel { text: "FPS"; color: theme.mutedTextColor }
                MintSpinBox { Layout.fillWidth: true; from: 1; to: 120; value: backend.settingsMap.animation_fps; onValueModified: backend.setSetting("animation_fps", value) }
            }
        }
        MintCheckBox { text: qsTr("Loop"); checked: backend.settingsMap.animation_loop; onToggled: backend.setSetting("animation_loop", checked) }

        MintLabel { text: qsTr("Motion preset"); color: theme.mutedTextColor }
        RowLayout {
            Layout.fillWidth: true
            MintComboBox { id: motionPreset; Layout.fillWidth: true; model: backend.animationPresetNames; translateModel: true }
            MintButton { text: qsTr("Apply"); enabled: motionPreset.currentIndex >= 0; onClicked: backend.applyAnimationPreset(backend.animationPresetIds[motionPreset.currentIndex]) }
        }
        RowLayout {
            Layout.fillWidth: true
            MintButton { Layout.fillWidth: true; text: qsTr("Dither In"); onClicked: backend.applyAnimationPreset("dither-in") }
            MintButton { Layout.fillWidth: true; text: qsTr("Dither Out"); onClicked: backend.applyAnimationPreset("dither-out") }
            MintButton { Layout.fillWidth: true; text: qsTr("In / Out"); onClicked: backend.applyAnimationPreset("dither-in-out") }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
        RowLayout {
            Layout.fillWidth: true
            MintButton { text: "|‹"; onClicked: backend.seekStart() }
            MintButton { text: "‹"; onClicked: backend.stepFrame(-1) }
            MintButton { text: backend.playing ? qsTr("Pause") : qsTr("Play"); onClicked: backend.togglePlay() }
            MintButton { text: "›"; onClicked: backend.stepFrame(1) }
            MintButton { text: "›|"; onClicked: backend.seekEnd() }
            Item { Layout.fillWidth: true }
            MintComboBox {
                id: playback
                Layout.preferredWidth: 118
                model: [qsTr("Quick"), qsTr("Rendered")]
                Component.onCompleted: currentIndex = backend.playbackMode === "Rendered" ? 1 : 0
                onActivated: backend.setPlaybackMode(root.playbackModeValues[currentIndex])
            }
        }
        MintSlider { Layout.fillWidth: true; from: 0; to: backend.timelineDuration; value: backend.currentTime; onUserMoved: function(newValue) { backend.setCurrentTime(newValue) } }
        RowLayout {
            Layout.fillWidth: true
            MintLabel { Layout.fillWidth: true; text: backend.currentTime.toFixed(2) + " / " + backend.timelineDuration.toFixed(2) + " s"; color: theme.mutedTextColor }
            MintButton { text: backend.renderedPreviewReady ? qsTr("Re-render preview") : qsTr("Render preview"); onClicked: backend.renderPreviewCache() }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
        MintLabel { text: qsTr("Tracks"); font.bold: true }
        ListView {
            id: trackList
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, 170)
            clip: true
            spacing: 3
            model: backend.animationTracks
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOff }
            delegate: Rectangle {
                width: trackList.width; height: 44; radius: 6
                color: index === root.selectedTrack ? theme.selectionColor : (trackHover.hovered ? theme.panelHoverColor : theme.panelRaisedColor)
                border.color: theme.borderColor
                RowLayout {
                    anchors.fill: parent; anchors.margins: 5
                    MintCheckBox { checked: modelData.enabled; onToggled: backend.setAnimationTrackEnabled(index, checked) }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 0
                        Text { Layout.fillWidth: true; text: localization.translateRuntime(localization.effectiveLanguageId, String(modelData.label)); color: theme.textColor; font.bold: true; elide: Text.ElideRight }
                        Text { Layout.fillWidth: true; text: Number(modelData.start).toFixed(2) + " → " + Number(modelData.end).toFixed(2) + " s  ·  " + modelData.easing; color: theme.mutedTextColor; font.pixelSize: 10; elide: Text.ElideRight }
                    }
                }
                HoverHandler { id: trackHover }
                TapHandler { onTapped: root.loadTrack(modelData) }
            }
        }

        MintLabel { text: qsTr("Keyframes"); font.bold: true; visible: root.selectedTrack >= 0 }
        Rectangle {
            id: keyTimeline
            Layout.fillWidth: true
            Layout.preferredHeight: 58
            visible: root.selectedTrack >= 0
            radius: 6
            color: theme.panelRaisedColor
            border.color: theme.borderColor
            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 12; anchors.rightMargin: 12; height: 2; color: theme.borderColor }
            Repeater {
                model: {
                    var track = root.selectedTrackData()
                    return track ? (track.keyframes || []) : []
                }
                delegate: Rectangle {
                    id: keyDot
                    required property var modelData
                    required property int index
                    width: 14; height: 14; radius: 3
                    rotation: 45
                    y: (keyTimeline.height - height) / 2
                    x: 7 + (keyTimeline.width - 28) * Math.max(0, Math.min(1, Number(modelData.time) / Math.max(0.001, backend.timelineDuration)))
                    color: index === root.selectedKey ? theme.accentColor : theme.textColor
                    border.color: theme.panelColor
                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -7
                        cursorShape: Qt.SizeHorCursor
                        drag.target: keyDot
                        drag.axis: Drag.XAxis
                        drag.minimumX: 7
                        drag.maximumX: Math.max(7, keyTimeline.width - 21)
                        onPressed: root.loadKey(index)
                        onReleased: {
                            var time = Math.max(0, Math.min(backend.timelineDuration,
                                ((keyDot.x - 7) / Math.max(1, keyTimeline.width - 28)) * backend.timelineDuration))
                            var key = root.selectedKeyData()
                            if (key)
                                backend.updateAnimationKeyframe(root.selectedTrack, index, time, Number(key.value), String(key.easing), key.bezier || [0.25,0.1,0.25,1.0])
                        }
                    }
                    ToolTip.visible: keyMouseHover.hovered
                    ToolTip.text: Number(modelData.time).toFixed(2) + " s · " + Number(modelData.value).toFixed(2)
                    HoverHandler { id: keyMouseHover }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: root.selectedTrack >= 0
            MintButton {
                text: qsTr("Add key")
                onClicked: {
                    var track = root.selectedTrackData()
                    if (!track) return
                    var value = Number(track.from || 0)
                    var keys = track.keyframes || []
                    if (keys.length) {
                        var closest = keys[0]
                        for (var i = 1; i < keys.length; ++i)
                            if (Math.abs(Number(keys[i].time) - backend.currentTime) < Math.abs(Number(closest.time) - backend.currentTime)) closest = keys[i]
                        value = Number(closest.value)
                    }
                    backend.addAnimationKeyframe(root.selectedTrack, backend.currentTime, value, "Linear")
                }
            }
            MintButton { text: qsTr("Copy key"); enabled: root.selectedKey >= 0; onClicked: backend.copyAnimationKeyframe(root.selectedTrack, root.selectedKey) }
            MintButton { text: qsTr("Paste key"); enabled: backend.keyframeClipboardAvailable; onClicked: backend.pasteAnimationKeyframe(root.selectedTrack, backend.currentTime) }
            MintButton { text: qsTr("Remove key"); enabled: root.selectedKey >= 0 && ((root.selectedTrackData() || {}).keyframes || []).length > 2; onClicked: { backend.removeAnimationKeyframe(root.selectedTrack, root.selectedKey); root.selectedKey = -1 } }
        }
        GridLayout {
            Layout.fillWidth: true
            visible: root.selectedTrack >= 0 && root.selectedKey >= 0
            columns: 2
            columnSpacing: 6; rowSpacing: 5
            MintLabel { text: qsTr("Key time"); color: theme.mutedTextColor }
            MintTextField {
                id: keyTimeField
                Layout.fillWidth: true
                validator: DoubleValidator { bottom: 0 }
                text: "0"
            }
            MintLabel { text: qsTr("Key value"); color: theme.mutedTextColor }
            MintTextField {
                id: keyValueField
                Layout.fillWidth: true
                validator: DoubleValidator {}
                text: "0"
            }
            MintLabel { text: qsTr("Key easing"); color: theme.mutedTextColor }
            MintComboBox { id: keyEasingCombo; Layout.fillWidth: true; model: backend.easingNames }
            MintLabel { text: qsTr("Bezier x1 / y1"); visible: keyEasingCombo.currentText === "Bezier"; color: theme.mutedTextColor }
            RowLayout {
                visible: keyEasingCombo.currentText === "Bezier"; Layout.fillWidth: true
                MintTextField { id: bezierX1; Layout.fillWidth: true; text: "0.25"; validator: DoubleValidator {} }
                MintTextField { id: bezierY1; Layout.fillWidth: true; text: "0.10"; validator: DoubleValidator {} }
            }
            MintLabel { text: qsTr("Bezier x2 / y2"); visible: keyEasingCombo.currentText === "Bezier"; color: theme.mutedTextColor }
            RowLayout {
                visible: keyEasingCombo.currentText === "Bezier"; Layout.fillWidth: true
                MintTextField { id: bezierX2; Layout.fillWidth: true; text: "0.25"; validator: DoubleValidator {} }
                MintTextField { id: bezierY2; Layout.fillWidth: true; text: "1.00"; validator: DoubleValidator {} }
            }
        }
        MintButton {
            visible: root.selectedTrack >= 0 && root.selectedKey >= 0
            text: qsTr("Update key")
            onClicked: backend.updateAnimationKeyframe(root.selectedTrack, root.selectedKey,
                Number(keyTimeField.text), Number(keyValueField.text), keyEasingCombo.currentText,
                [Number(bezierX1.text), Number(bezierY1.text), Number(bezierX2.text), Number(bezierY2.text)])
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor; visible: root.selectedTrack >= 0 }
        MintLabel { text: qsTr("Modulator"); font.bold: true; visible: root.selectedTrack >= 0 }
        GridLayout {
            Layout.fillWidth: true; visible: root.selectedTrack >= 0
            columns: 2; columnSpacing: 6; rowSpacing: 5
            MintLabel { text: qsTr("Type"); color: theme.mutedTextColor }
            MintComboBox {
                id: modType
                Layout.fillWidth: true
                model: backend.modulatorNames
                Component.onCompleted: currentIndex = 0
            }
            MintLabel { text: qsTr("Amount"); color: theme.mutedTextColor }
            MintTextField { id: modAmount; Layout.fillWidth: true; text: "0"; validator: DoubleValidator {} }
            MintLabel { text: qsTr("Frequency"); color: theme.mutedTextColor }
            MintTextField { id: modFrequency; Layout.fillWidth: true; text: "1"; validator: DoubleValidator { bottom: 0 } }
            MintLabel { text: qsTr("Phase"); color: theme.mutedTextColor }
            MintTextField { id: modPhase; Layout.fillWidth: true; text: "0"; validator: DoubleValidator {} }
            MintLabel { text: "BPM"; color: theme.mutedTextColor }
            MintTextField { id: modBpm; Layout.fillWidth: true; text: "120"; validator: DoubleValidator { bottom: 1 } }
            MintLabel { text: qsTr("Seed"); color: theme.mutedTextColor }
            MintSpinBox { id: modSeed; Layout.fillWidth: true; from: 0; to: 999999; value: 1 }
        }
        RowLayout {
            Layout.fillWidth: true; visible: root.selectedTrack >= 0
            MintButton { text: qsTr("Apply modulator"); onClicked: backend.setAnimationModulator(root.selectedTrack, modType.currentText, Number(modAmount.text), Number(modFrequency.text), Number(modPhase.text), Number(modBpm.text), modSeed.value) }
            MintButton { text: backend.audioEnvelopeReady ? qsTr("Re-analyse audio") : qsTr("Analyse audio"); onClicked: backend.analyzeAudioModulation() }
            MintLabel { Layout.fillWidth: true; text: backend.audioEnvelopeReady ? qsTr("%1 audio samples").arg(backend.audioEnvelopeSamples) : ""; color: theme.mutedTextColor }
        }
        RowLayout {
            Layout.fillWidth: true; visible: root.selectedTrack >= 0
            MintTextField { id: clipName; Layout.fillWidth: true; placeholderText: qsTr("Animation clip name") }
            MintButton { text: qsTr("Save clip"); onClicked: backend.saveAnimationClip(root.selectedTrack, clipName.text) }
        }
        RowLayout {
            Layout.fillWidth: true
            MintComboBox { id: clipCombo; Layout.fillWidth: true; model: (backend.animationClipLibrary || []).map(function(item) { return item.name }) }
            MintButton { text: qsTr("Apply clip"); enabled: clipCombo.currentIndex >= 0 && targetCombo.currentIndex >= 0; onClicked: backend.applyAnimationClip(clipCombo.currentText, backend.animationTargetIds[targetCombo.currentIndex]) }
        }

        MintLabel { text: qsTr("Animate"); color: theme.mutedTextColor }
        MintComboBox {
            id: targetCombo
            Layout.fillWidth: true
            model: backend.animationTargetNames
            onActivated: root.resetEditorFromTarget()
            Component.onCompleted: if (count > 0) root.resetEditorFromTarget()
        }
        RowLayout {
            Layout.fillWidth: true

            ColumnLayout {
                Layout.fillWidth: true
                MintLabel {
                    text: qsTr("From")
                    color: theme.mutedTextColor
                }
                MintTextField {
                    id: fromField
                    Layout.fillWidth: true
                    text: "0"
                    validator: DoubleValidator {}
                }
            }

            MintLabel { text: "→" }

            ColumnLayout {
                Layout.fillWidth: true
                MintLabel {
                    text: qsTr("To")
                    color: theme.mutedTextColor
                }
                MintTextField {
                    id: toField
                    Layout.fillWidth: true
                    text: "1"
                    validator: DoubleValidator {}
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            ColumnLayout {
                Layout.fillWidth: true
                MintLabel {
                    text: qsTr("Start (s)")
                    color: theme.mutedTextColor
                }
                MintTextField {
                    id: startField
                    Layout.fillWidth: true
                    text: "0.00"
                    validator: DoubleValidator { bottom: 0 }
                }
            }

            MintLabel { text: "→" }

            ColumnLayout {
                Layout.fillWidth: true
                MintLabel {
                    text: qsTr("End (s)")
                    color: theme.mutedTextColor
                }
                MintTextField {
                    id: endField
                    Layout.fillWidth: true
                    text: Number(backend.timelineDuration).toFixed(2)
                    validator: DoubleValidator { bottom: 0 }
                }
            }
        }
        MintLabel { text: qsTr("Easing"); color: theme.mutedTextColor }
        MintComboBox { id: easingCombo; Layout.fillWidth: true; model: backend.easingNames }

        RowLayout {
            Layout.fillWidth: true
            MintButton {
                Layout.fillWidth: true; text: qsTr("Add"); enabled: targetCombo.currentIndex >= 0
                onClicked: backend.addAnimationTrack(backend.animationTargetIds[targetCombo.currentIndex], Number(fromField.text), Number(toField.text), Number(startField.text), Number(endField.text), easingCombo.currentText)
            }
            MintButton {
                Layout.fillWidth: true; text: qsTr("Update"); enabled: root.selectedTrack >= 0
                onClicked: backend.updateAnimationTrack(root.selectedTrack, backend.animationTargetIds[targetCombo.currentIndex], Number(fromField.text), Number(toField.text), Number(startField.text), Number(endField.text), easingCombo.currentText)
            }
            MintButton { text: qsTr("Duplicate"); enabled: root.selectedTrack >= 0; onClicked: backend.duplicateAnimationTrack(root.selectedTrack) }
            MintButton { text: qsTr("Remove"); enabled: root.selectedTrack >= 0; onClicked: { backend.removeAnimationTrack(root.selectedTrack); root.selectedTrack = -1 } }
        }
        MintLabel { Layout.fillWidth: true; text: qsTr("Animated parameters are locked in the layer editor while their track is enabled."); color: theme.mutedTextColor; wrapMode: Text.WordWrap }
    }
}
