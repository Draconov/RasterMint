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
        MintLabel { text: "Target Raster"; font.bold: true; font.pixelSize: 15 }
        MintCheckBox { text: "Use exact target size"; checked: backend.settingsMap.target_enabled; onToggled: backend.setSetting("target_enabled", checked) }

        MintLabel { text: "Preset"; color: theme.mutedTextColor }
        MintComboBox {
            id: rasterPreset
            Layout.fillWidth: true
            model: ["Custom", "Game Boy · 160 × 144", "GBA · 240 × 160", "SNES · 256 × 224", "NES · 256 × 240", "ZX Spectrum · 256 × 192", "320 × 200", "320 × 240", "640 × 480"]
            onActivated: if (currentIndex > 0) backend.setRasterSize(root.rasterSizes[currentIndex][0], root.rasterSizes[currentIndex][1])
        }

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                MintLabel { text: "Width"; color: theme.mutedTextColor }
                SpinBox { Layout.fillWidth: true; from: 1; to: 16384; value: Math.max(1, backend.settingsMap.target_width || 1); editable: true; onValueModified: backend.setSetting("target_width", value) }
            }
            ColumnLayout {
                Layout.fillWidth: true
                MintLabel { text: "Height"; color: theme.mutedTextColor }
                SpinBox { Layout.fillWidth: true; from: 1; to: 16384; value: Math.max(1, backend.settingsMap.target_height || 1); editable: true; onValueModified: backend.setSetting("target_height", value) }
            }
        }
        MintCheckBox { text: "Keep aspect ratio"; checked: backend.settingsMap.keep_aspect; onToggled: backend.setSetting("keep_aspect", checked) }

        MintLabel { text: "Source fit"; color: theme.mutedTextColor }
        MintComboBox {
            id: fitCombo
            Layout.fillWidth: true
            model: ["Fit · show all", "Fill · crop edges", "Stretch"]
            Component.onCompleted: currentIndex = Math.max(0, ["fit","fill","stretch"].indexOf(String(backend.settingsMap.fit_mode)))
            onActivated: backend.setSetting("fit_mode", ["fit","fill","stretch"][currentIndex])
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: theme.borderColor }
        MintLabel { text: "Framebuffer Pixel Aspect"; font.bold: true }
        MintComboBox {
            id: parPreset
            Layout.fillWidth: true
            model: ["Square · 1:1", "CGA 320×200 display-fit · 5:6", "SNES display-fit · 7:6", "Mega Drive 320-wide · 14:15", "C64 multicolor display-fit · 5:3", "Custom"]
            onActivated: if (currentIndex < root.pixelAspects.length) backend.setPixelAspect(root.pixelAspects[currentIndex][0], root.pixelAspects[currentIndex][1])
        }
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                MintLabel { text: "Width"; color: theme.mutedTextColor }
                MintTextField { Layout.fillWidth: true; text: Number(backend.settingsMap.pixel_aspect_x).toFixed(3); onEditingFinished: backend.setSetting("pixel_aspect_x", Number(text)) }
            }
            ColumnLayout {
                Layout.fillWidth: true
                MintLabel { text: "Height"; color: theme.mutedTextColor }
                MintTextField { Layout.fillWidth: true; text: Number(backend.settingsMap.pixel_aspect_y).toFixed(3); onEditingFinished: backend.setSetting("pixel_aspect_y", Number(text)) }
            }
        }

        MintLabel { text: "View"; color: theme.mutedTextColor }
        MintComboBox {
            id: displayCombo
            Layout.fillWidth: true
            model: ["Raw framebuffer", "Corrected pixels", "Display simulation"]
            Component.onCompleted: currentIndex = Math.max(0, ["raw","corrected","display"].indexOf(String(backend.settingsMap.display_mode)))
            onActivated: backend.setSetting("display_mode", ["raw","corrected","display"][currentIndex])
        }
        MintCheckBox { text: "Apply display view to export"; checked: backend.settingsMap.display_export; onToggled: backend.setSetting("display_export", checked) }
    }
}
