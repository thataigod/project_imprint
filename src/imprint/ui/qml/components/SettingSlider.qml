import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    property string label: ""
    property string help: ""
    property real from: 0
    property real to: 1
    property real stepSize: 0.01
    property real value: 0

    signal valueEdited(real value)

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

        Text {
            text: root.value.toFixed(2)
            color: Theme.accent
            font.family: Theme.monoFamily
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }
    }

    Slider {
        id: slider
        Layout.fillWidth: true
        from: root.from
        to: root.to
        stepSize: root.stepSize
        value: root.value
        onMoved: root.valueEdited(value)

        background: Rectangle {
            x: slider.leftPadding
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            implicitWidth: 200
            implicitHeight: 6
            width: slider.availableWidth
            height: implicitHeight
            radius: 3
            color: Theme.surfacePressed

            Rectangle {
                width: slider.visualPosition * parent.width
                height: parent.height
                radius: 3
                color: Theme.accent
            }
        }

        handle: Rectangle {
            x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            implicitWidth: 18
            implicitHeight: 18
            radius: 9
            color: Theme.accent
            border.width: 3
            border.color: Theme.accentSoft
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
