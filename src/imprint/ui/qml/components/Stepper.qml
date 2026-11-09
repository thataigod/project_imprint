import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    property string label: ""
    property string help: ""
    property int from: 1
    property int to: 64
    property int value: 1

    signal valueEdited(int value)

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

        Rectangle {
            implicitWidth: 56
            implicitHeight: 38
            radius: Theme.radius - 1
            color: Theme.surfaceAlt
            border.width: 1
            border.color: Theme.border

            Text {
                anchors.centerIn: parent
                text: root.value
                color: Theme.text
                font.family: Theme.monoFamily
                font.pixelSize: 13
                font.weight: Font.DemiBold
            }
        }

        AppButton {
            text: "-"
            variant: "secondary"
            implicitWidth: 38
            implicitHeight: 38
            font.pixelSize: 16
            enabled: root.value > root.from
            onClicked: root.valueEdited(Math.max(root.from, root.value - 1))
        }

        AppButton {
            text: "+"
            variant: "secondary"
            implicitWidth: 38
            implicitHeight: 38
            font.pixelSize: 16
            enabled: root.value < root.to
            onClicked: root.valueEdited(Math.min(root.to, root.value + 1))
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
