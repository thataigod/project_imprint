import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    property string label: ""
    property string help: ""
    property bool value: false

    signal toggled(bool value)

    spacing: 4
    Layout.fillWidth: true

    RowLayout {
        Layout.fillWidth: true
        spacing: 8

        Text {
            text: root.label
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: 12
            Layout.fillWidth: true
        }

        Switch {
            id: control
            checked: root.value
            text: ""
            onToggled: root.toggled(checked)

            indicator: Rectangle {
                implicitWidth: 44
                implicitHeight: 24
                radius: 12
                color: control.checked ? Theme.accent : Theme.surfacePressed
                border.width: 1
                border.color: control.checked ? Theme.accent : Theme.border

                Rectangle {
                    x: control.checked ? parent.width - width - 3 : 3
                    y: 3
                    width: 18
                    height: 18
                    radius: 9
                    color: "#FFFFFF"
                    Behavior on x {
                        NumberAnimation { duration: 120 }
                    }
                }
            }

            contentItem: Item {}
        }
    }

    Text {
        text: root.help
        visible: text.length > 0
        color: Theme.textFaint
        font.family: Theme.fontFamily
        font.pixelSize: 11
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
}
