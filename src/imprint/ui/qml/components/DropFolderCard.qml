import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Card {
    id: card
    property string title: ""
    property string path: ""
    property string hint: ""
    property string kind: ""

    signal browseRequested()
    signal folderDropped(string kind, url url)

    implicitHeight: 102

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: card.title
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 13
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }

            AppButton {
                text: "Browse"
                variant: "secondary"
                implicitHeight: 32
                implicitWidth: 82
                font.pixelSize: 12
                onClicked: card.browseRequested()
            }
        }

        Text {
            text: card.path.length > 0 ? card.path : card.hint
            color: card.path.length > 0 ? Theme.textMuted : Theme.textFaint
            font.family: Theme.fontFamily
            font.pixelSize: 11
            elide: Text.ElideMiddle
            Layout.fillWidth: true
        }
    }

    DropArea {
        anchors.fill: parent
        onEntered: card.border.color = Theme.accent
        onExited: card.border.color = Theme.border
        onDropped: function (drop) {
            if (drop.urls.length > 0) {
                card.folderDropped(card.kind, drop.urls[0]);
                drop.acceptProposedAction();
            }
        }
    }
}
