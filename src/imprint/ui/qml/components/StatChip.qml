import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string label: ""
    property int value: 0
    property color accentColor: Theme.accent

    implicitWidth: 108
    implicitHeight: 58
    radius: 10
    color: Theme.surfaceAlt
    border.width: 1
    border.color: Theme.border

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 2

        Text {
            text: root.value
            color: root.accentColor
            font.family: Theme.fontFamily
            font.pixelSize: 18
            font.weight: Font.Bold
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            text: root.label
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: 10
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
