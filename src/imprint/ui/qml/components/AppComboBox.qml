import QtQuick
import QtQuick.Controls

ComboBox {
    id: control

    implicitHeight: 42
    font.family: Theme.fontFamily
    font.pixelSize: 14

    background: Rectangle {
        radius: Theme.radius
        color: Theme.surfaceAlt
        border.width: 1
        border.color: control.activeFocus ? Theme.accent : Theme.border
    }

    contentItem: Text {
        leftPadding: 12
        rightPadding: 32
        text: control.displayText
        color: Theme.text
        font: control.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Text {
        x: control.width - width - 12
        y: (control.height - height) / 2
        text: "\u25BE"
        color: Theme.textMuted
        font.pixelSize: 12
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        implicitHeight: Math.min(320, contentItem.implicitHeight + 8)
        padding: 4
        background: Rectangle {
            color: Theme.surfaceAlt
            radius: Theme.radius
            border.width: 1
            border.color: Theme.border
        }
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            delegate: ItemDelegate {
                width: control.width - 8
                text: modelData
                font: control.font
                background: Rectangle {
                    radius: 6
                    color: control.highlightedIndex === index ? Theme.surfaceHover : "transparent"
                }
                contentItem: Text {
                    text: parent.text
                    color: Theme.text
                    font: control.font
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
            }
        }
    }
}
