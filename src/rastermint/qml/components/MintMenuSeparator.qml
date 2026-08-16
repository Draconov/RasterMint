import QtQuick
import QtQuick.Controls

MenuSeparator {
    id: control
    topPadding: 4
    bottomPadding: 4
    leftPadding: 8
    rightPadding: 8

    contentItem: Rectangle {
        implicitHeight: 1
        color: theme.borderColor
    }
}
