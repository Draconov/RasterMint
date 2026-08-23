import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Item {
    id: root

    property string colorValue: "#FFFFFF"
    property string dialogTitle: "Choose colour"
    signal colorPicked(string value)

    implicitHeight: 34
    implicitWidth: 150

    function normalized(value) {
        var candidate = String(value || "#FFFFFF")
        return candidate.length > 0 ? candidate : "#FFFFFF"
    }

    Button {
        id: button
        anchors.fill: parent
        enabled: root.enabled
        hoverEnabled: true
        leftPadding: 8
        rightPadding: 8

        contentItem: RowLayout {
            spacing: 8
            Rectangle {
                Layout.preferredWidth: 24
                Layout.preferredHeight: 20
                radius: 4
                color: root.normalized(root.colorValue)
                border.color: theme.borderColor
                border.width: 1
            }
            Text {
                Layout.fillWidth: true
                text: root.normalized(root.colorValue).toUpperCase()
                color: root.enabled ? theme.textColor : theme.mutedTextColor
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                font.pixelSize: 12
            }
            Text {
                text: "▾"
                color: theme.mutedTextColor
                verticalAlignment: Text.AlignVCenter
            }
        }

        background: Rectangle {
            radius: 6
            color: button.down ? theme.selectionColor : (button.hovered ? theme.panelHoverColor : theme.panelRaisedColor)
            border.color: button.activeFocus ? theme.accentColor : theme.borderColor
            border.width: button.activeFocus ? 2 : 1
        }

        onClicked: {
            picker.selectedColor = root.normalized(root.colorValue)
            picker.open()
        }
    }

    ColorDialog {
        id: picker
        title: root.dialogTitle
        onAccepted: {
            root.colorValue = selectedColor.toString()
            root.colorPicked(root.colorValue)
        }
    }
}
