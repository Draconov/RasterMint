import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root
    contentWidth: availableWidth
    property int selectedTrack: -1
    property var playbackModeValues: ["Quick", "Rendered"]
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
            MintComboBox { id: motionPreset; Layout.fillWidth: true; model: backend.animationPresetNames }
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
                        Text { Layout.fillWidth: true; text: qsTr(modelData.label); color: theme.textColor; font.bold: true; elide: Text.ElideRight }
                        Text { Layout.fillWidth: true; text: Number(modelData.start).toFixed(2) + " → " + Number(modelData.end).toFixed(2) + " s  ·  " + modelData.easing; color: theme.mutedTextColor; font.pixelSize: 10; elide: Text.ElideRight }
                    }
                }
                HoverHandler { id: trackHover }
                TapHandler { onTapped: root.loadTrack(modelData) }
            }
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
