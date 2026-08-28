import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    property bool translateModel: false
    property string separatorToken: "__mint_unused_separator__"
    implicitHeight: 34
    leftPadding: 10
    rightPadding: 28
    font.pixelSize: 13
    contentItem: Text {
        leftPadding: 2
        text: control.translateModel ? localization.translateRuntime(localization.effectiveLanguageId, String(control.displayText)) : control.displayText
        color: theme.textColor
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Text {
        x: control.width - width - 10
        anchors.verticalCenter: parent.verticalCenter
        text: "▾"
        color: theme.mutedTextColor
    }
    background: Rectangle {
        radius: 6
        color: control.hovered ? theme.panelHoverColor : theme.panelRaisedColor
        border.color: control.activeFocus ? theme.accentColor : theme.borderColor
        border.width: control.activeFocus ? 2 : 1
        Behavior on color { ColorAnimation { duration: 90 } }
    }
    popup: Popup {
        popupType: Popup.Item
        y: control.height + 2
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 320)
        padding: 4
        background: Rectangle {
            radius: 7
            color: theme.panelRaisedColor
            border.color: theme.borderColor
        }
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator { }
        }
    }
    delegate: ItemDelegate {
        id: delegateItem
        readonly property bool isSeparator: modelData === control.separatorToken
        width: control.width - 8
        height: isSeparator ? 9 : 32
        enabled: !isSeparator
        hoverEnabled: !isSeparator
        highlighted: !isSeparator && control.highlightedIndex === index
        contentItem: Text {
            visible: !delegateItem.isSeparator
            text: control.translateModel ? localization.translateRuntime(localization.effectiveLanguageId, String(modelData)) : modelData
            color: theme.textColor
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        background: Item {
            Rectangle {
                visible: !delegateItem.isSeparator
                anchors.fill: parent
                radius: 5
                color: delegateItem.highlighted || delegateItem.hovered ? theme.selectionColor : "transparent"
            }
            Rectangle {
                visible: delegateItem.isSeparator
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                height: 1
                color: theme.borderColor
            }
        }
    }
}
