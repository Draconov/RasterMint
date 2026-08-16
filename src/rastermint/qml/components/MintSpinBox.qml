import QtQuick
import QtQuick.Controls

SpinBox {
    id: control

    implicitHeight: 34
    implicitWidth: 96
    editable: true
    leftPadding: 8
    rightPadding: 52
    font.pixelSize: 13

    contentItem: TextInput {
        z: 2
        text: control.textFromValue(control.value, control.locale)
        font: control.font
        color: control.enabled ? theme.textColor : theme.mutedTextColor
        selectionColor: theme.selectionColor
        selectedTextColor: theme.textColor
        horizontalAlignment: Qt.AlignLeft
        verticalAlignment: Qt.AlignVCenter
        readOnly: !control.editable
        validator: control.validator
        inputMethodHints: Qt.ImhFormattedNumbersOnly
    }

    up.indicator: Rectangle {
        x: parent.width - width
        width: 26
        height: parent.height / 2
        color: control.up.pressed ? theme.selectionColor
             : control.up.hovered ? theme.panelHoverColor
             : "transparent"

        Text {
            anchors.centerIn: parent
            text: "▴"
            color: control.enabled ? theme.textColor : theme.mutedTextColor
            font.pixelSize: 10
        }
    }

    down.indicator: Rectangle {
        x: parent.width - width
        y: parent.height / 2
        width: 26
        height: parent.height / 2
        color: control.down.pressed ? theme.selectionColor
             : control.down.hovered ? theme.panelHoverColor
             : "transparent"

        Text {
            anchors.centerIn: parent
            text: "▾"
            color: control.enabled ? theme.textColor : theme.mutedTextColor
            font.pixelSize: 10
        }
    }

    background: Rectangle {
        implicitWidth: 96
        implicitHeight: 34
        radius: 6
        color: theme.panelRaisedColor
        border.color: control.visualFocus ? theme.accentColor : theme.borderColor
        border.width: control.visualFocus ? 2 : 1

        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 26
            color: "transparent"
            border.color: theme.borderColor
            border.width: 1
            radius: 6
        }
    }
}
