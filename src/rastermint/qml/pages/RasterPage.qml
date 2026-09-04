import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root
    contentWidth: availableWidth
    property var rasterSizes: [[0,0], [160,144], [240,160], [256,224], [256,240], [256,192], [320,200], [320,240], [640,480]]
    property var pixelAspects: [[1,1], [5,6], [7,6], [14,15], [5,3]]
    clip: true
    ScrollBar.vertical.policy: ScrollBar.AlwaysOff

    ColumnLayout {
        width: root.availableWidth
        spacing: 9
        MintLabel { text: qsTr("Target Raster"); font.bold: true; font.pixelSize: 15 }
        MintCheckBox { text: qsTr("Use exact target size"); checked: backend.settingsMap.target_enabled; onToggled: backend.setSetting("target_enabled", checked) }
        MintLabel {
            Layout.fillWidth: true
            text: backend.settingsMap.target_enabled
                  ? qsTr("Processing uses exactly Width × Height pixels before dithering and effects.")
                  : qsTr("Off: RasterMint keeps the transformed source raster size. Width and Height are ignored.")
            color: theme.mutedTextColor
            wrapMode: Text.WordWrap
            font.pixelSize: 10
        }

        MintLabel { text: qsTr("Preset"); color: theme.mutedTextColor }
        MintComboBox {
            id: rasterPreset
            Layout.fillWidth: true
            model: [qsTr("Custom"), "Game Boy · 160 × 144", "GBA · 240 × 160", "SNES · 256 × 224", "NES · 256 × 240", "ZX Spectrum · 256 × 192", "320 × 200", "320 × 240", "640 × 480"]
            onActivated: if (currentIndex > 0) backend.setRasterSize(root.rasterSizes[currentIndex][0], root.rasterSizes[currentIndex][1])
            enabled: true
        }

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                MintLabel { text: qsTr("Width"); color: theme.mutedTextColor }
                MintSpinBox { Layout.fillWidth: true; from: 1; to: 16384; value: backend.settingsMap.target_enabled ? Math.max(1, backend.settingsMap.target_width || 1) : backend.sourceWidth; editable: true; enabled: backend.settingsMap.target_enabled; onValueModified: backend.setTargetRasterWidth(value) }
            }
            ColumnLayout {
                Layout.fillWidth: true
                MintLabel { text: qsTr("Height"); color: theme.mutedTextColor }
                MintSpinBox { Layout.fillWidth: true; from: 1; to: 16384; value: backend.settingsMap.target_enabled ? Math.max(1, backend.settingsMap.target_height || 1) : backend.sourceHeight; editable: true; enabled: backend.settingsMap.target_enabled; onValueModified: backend.setTargetRasterHeight(value) }
            }
        }
        MintCheckBox { text: qsTr("Keep aspect ratio"); checked: backend.settingsMap.keep_aspect; enabled: backend.settingsMap.target_enabled; onToggled: backend.setSetting("keep_aspect", checked) }
        MintLabel {
            Layout.fillWidth: true
            visible: backend.settingsMap.target_enabled && backend.settingsMap.keep_aspect
            text: qsTr("Width and Height are linked to the cropped/rotated source aspect ratio. Editing either dimension updates the other.")
            color: theme.mutedTextColor
            wrapMode: Text.WordWrap
            font.pixelSize: 10
        }

        MintLabel { text: qsTr("Source fit"); color: theme.mutedTextColor }
        MintComboBox {
            id: fitCombo
            Layout.fillWidth: true
            model: [qsTr("Fit · show all"), qsTr("Fill · crop edges"), qsTr("Stretch")]
            Component.onCompleted: currentIndex = Math.max(0, ["fit","fill","stretch"].indexOf(String(backend.settingsMap.fit_mode)))
            onActivated: backend.setSetting("fit_mode", ["fit","fill","stretch"][currentIndex])
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
        MintLabel { text: qsTr("Framebuffer Pixel Aspect"); font.bold: true }
        MintComboBox {
            id: parPreset
            Layout.fillWidth: true
            model: [qsTr("Square · 1:1"), qsTr("CGA 320×200 display-fit · 5:6"), qsTr("SNES display-fit · 7:6"), qsTr("Mega Drive 320-wide · 14:15"), qsTr("C64 multicolor display-fit · 5:3"), qsTr("Custom")]
            onActivated: if (currentIndex < root.pixelAspects.length) backend.setPixelAspect(root.pixelAspects[currentIndex][0], root.pixelAspects[currentIndex][1])
        }
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                MintLabel { text: qsTr("Width"); color: theme.mutedTextColor }
                MintTextField { Layout.fillWidth: true; text: Number(backend.settingsMap.pixel_aspect_x).toFixed(3); onEditingFinished: backend.setSetting("pixel_aspect_x", Number(text)) }
            }
            ColumnLayout {
                Layout.fillWidth: true
                MintLabel { text: qsTr("Height"); color: theme.mutedTextColor }
                MintTextField { Layout.fillWidth: true; text: Number(backend.settingsMap.pixel_aspect_y).toFixed(3); onEditingFinished: backend.setSetting("pixel_aspect_y", Number(text)) }
            }
        }

        MintLabel { text: qsTr("View"); color: theme.mutedTextColor }
        MintComboBox {
            id: displayCombo
            Layout.fillWidth: true
            model: [qsTr("Raw framebuffer"), qsTr("Corrected pixels"), qsTr("Display simulation")]
            Component.onCompleted: currentIndex = Math.max(0, ["raw","corrected","display"].indexOf(String(backend.settingsMap.display_mode)))
            onActivated: backend.setSetting("display_mode", ["raw","corrected","display"][currentIndex])
        }
    }
}
