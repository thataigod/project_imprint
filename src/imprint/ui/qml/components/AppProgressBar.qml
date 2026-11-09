import QtQuick
import QtQuick.Controls

ProgressBar {
    id: control
    implicitHeight: 8

    background: Rectangle {
        implicitHeight: 8
        radius: 4
        color: Theme.surfaceAlt
        border.width: 1
        border.color: Theme.border
    }

    contentItem: Item {
        Rectangle {
            width: control.position * parent.width
            height: parent.height
            radius: 4
            color: Theme.accent
            Behavior on width {
                NumberAnimation { duration: 120 }
            }
        }
    }
}
