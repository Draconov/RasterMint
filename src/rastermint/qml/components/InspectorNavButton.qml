import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects

Button {
    id: control

    property bool selected: false
    property url iconSource: ""
    property bool paletteSwatches: false
    property color iconColor: theme.textColor

    implicitWidth: 44
    implicitHeight: 36
    flat: true

    ToolTip.visible: control.hovered
    ToolTip.text: control.text
    ToolTip.delay: 350
    ToolTip.timeout: 3000

    contentItem: Item {
        Image {
            id: iconMask
            anchors.centerIn: parent
            width: 32
            height: 32
            source: control.iconSource
            visible: !control.paletteSwatches
            opacity: 0.0
            fillMode: Image.PreserveAspectFit
            smooth: false
            mipmap: false
            sourceSize.width: width
            sourceSize.height: height
        }

        ColorOverlay {
            anchors.fill: iconMask
            source: iconMask
            color: control.iconColor
            visible: !control.paletteSwatches
            cached: true
        }

        Grid {
            anchors.centerIn: parent
            visible: control.paletteSwatches
            columns: 2
            spacing: 2

            Repeater {
                model: [
                    theme.panelRaisedColor,
                    theme.selectionColor,
                    theme.accentColor,
                    theme.textColor
                ]

                Rectangle {
                    width: 14
                    height: 14
                    radius: 1
                    color: modelData
                }
            }
        }
    }

    background: Rectangle {
        radius: 6
        color: control.selected ? theme.selectionColor : (control.hovered ? theme.panelHoverColor : "transparent")

        Rectangle {
            visible: control.selected
            width: 3
            radius: 2
            color: theme.accentColor
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom; margins: 5 }
        }

        Behavior on color { ColorAnimation { duration: 90 } }
    }
}
