import QtQuick
import QtQuick.Layouts

Card {
    id: root
    property string fileName: ""
    property string sourceUrl: ""
    property real score: -1
    property real detScore: -1
    property string status: "skip"
    property string subfolder: ""
    property bool cached: false
    property string errorText: ""

    signal clicked()

    implicitHeight: 200

    TapHandler {
        onTapped: root.clicked()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 118
            clip: true

            Image {
                id: preview
                anchors.fill: parent
                source: root.sourceUrl
                asynchronous: true
                cache: false
                fillMode: Image.PreserveAspectFit
            }

            Rectangle {
                anchors.fill: parent
                visible: preview.status !== Image.Ready
                color: Theme.surfaceAlt

                Text {
                    anchors.centerIn: parent
                    text: "No preview"
                    color: Theme.textFaint
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                }
            }

            Rectangle {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 8
                implicitWidth: badgeText.implicitWidth + 14
                implicitHeight: 22
                radius: 6
                color: root.status === "match" ? Theme.successSoft : root.status === "error" ? Theme.dangerSoft : Theme.surfaceAlt
                border.width: 1
                border.color: root.status === "match" ? Theme.success : root.status === "error" ? Theme.danger : Theme.border

                Text {
                    id: badgeText
                    anchors.centerIn: parent
                    text: root.status === "match" ? root.score.toFixed(3) : root.status.toUpperCase()
                    color: root.status === "match" ? Theme.success : root.status === "error" ? Theme.danger : Theme.textMuted
                    font.family: Theme.monoFamily
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: 10
            spacing: 3

            Text {
                text: root.fileName
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 12
                font.weight: Font.DemiBold
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }

            Text {
                text: root.status === "error"
                      ? (root.errorText.length > 0 ? root.errorText : "Could not process image")
                      : root.subfolder.length > 0
                        ? root.subfolder + (root.cached ? "  |  cached" : "")
                        : "Skipped"
                color: root.status === "error" ? Theme.danger : Theme.textFaint
                font.family: Theme.fontFamily
                font.pixelSize: 10
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }
    }
}
