import QtQuick
import QtQuick.Controls

Menu {
    id: control

    // Do not let Qt promote RasterMint's themed menus to native menus/windows.
    // More importantly, always give the popup a concrete width: a customized
    // Menu whose delegate/background have no implicit width can open at width 0
    // and look as if the menu bar did nothing.
    popupType: Popup.Item
    property real menuWidth: 280
    width: menuWidth
    padding: 4

    delegate: MintMenuItem {
        width: control.availableWidth
    }

    background: Rectangle {
        implicitWidth: control.menuWidth
        implicitHeight: 32
        radius: 7
        color: theme.panelRaisedColor
        border.color: theme.borderColor
        border.width: 1
    }
}
