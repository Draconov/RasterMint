import QtQuick
import QtQuick.Controls

Button {
    id: control

    property bool selected: false
    property url iconSource: ""
    property bool paletteSwatches: false
    property color iconColor: control.selected ? theme.accentColor : theme.textColor

    implicitWidth: 44
    implicitHeight: 36
    flat: true

    MintToolTip {
        visible: control.hovered
        text: control.text
        delay: 350
        timeout: 3000
    }

    contentItem: Item {
        Canvas {
            id: iconCanvas
            anchors.centerIn: parent
            width: 32
            height: 32
            visible: !control.paletteSwatches

            property url imageSource: control.iconSource
            property color tintColor: control.iconColor

            function loadCurrentImage() {
                if (imageSource && imageSource.toString().length > 0 && !isImageLoaded(imageSource) && !isImageLoading(imageSource))
                    loadImage(imageSource)
            }

            Component.onCompleted: loadCurrentImage()
            onImageSourceChanged: {
                loadCurrentImage()
                requestPaint()
            }
            onTintColorChanged: requestPaint()
            onImageLoaded: requestPaint()

            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)

                if (!imageSource || imageSource.toString().length === 0 || !isImageLoaded(imageSource))
                    return

                // Keep the uploaded PNG as the alpha/shape mask, then replace
                // its RGB with the current theme's icon/text colour.
                ctx.globalCompositeOperation = "source-over"
                ctx.drawImage(imageSource, 0, 0, width, height)
                ctx.globalCompositeOperation = "source-in"
                ctx.fillStyle = tintColor
                ctx.fillRect(0, 0, width, height)
                ctx.globalCompositeOperation = "source-over"
            }
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


        Behavior on color { ColorAnimation { duration: 90 } }
    }
}
