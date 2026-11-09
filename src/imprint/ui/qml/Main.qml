import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: window
    visible: true
    title: "Imprint Face Sorter v" + bridge.version
    width: bridge.windowWidth
    height: bridge.windowHeight
    x: bridge.windowX
    y: bridge.windowY
    minimumWidth: 1080
    minimumHeight: 720
    color: Theme.background
    font.family: Theme.fontFamily

    property bool logExpanded: true
    property bool viewerOpen: false
    property int viewerIndex: -1
    property var viewerData: ({})

    function openViewer(index) {
        viewerIndex = index;
        viewerData = bridge.resultAt(index);
        viewerOpen = true;
        viewerScope.forceActiveFocus();
    }

    function closeViewer() {
        viewerOpen = false;
    }

    function stepViewer(delta) {
        var count = bridge.visibleResultCount;
        if (!viewerOpen || count <= 0) {
            return;
        }
        var next = Math.max(0, Math.min(count - 1, viewerIndex + delta));
        if (next !== viewerIndex) {
            viewerIndex = next;
            viewerData = bridge.resultAt(next);
        }
    }

    function setResultFilter(value) {
        viewerOpen = false;
        bridge.resultFilter = value;
    }

    Shortcut {
        sequence: "Ctrl+R"
        onActivated: bridge.startAnalysis()
    }
    Shortcut {
        sequence: "Ctrl+P"
        onActivated: bridge.togglePause()
    }
    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (window.viewerOpen) {
                window.closeViewer();
            } else {
                bridge.cancelAnalysis();
            }
        }
    }
    Shortcut {
        sequence: "Ctrl+L"
        onActivated: bridge.clearLog()
    }

    onClosing: {
        bridge.saveWindowGeometry(window.width, window.height, window.x, window.y);
        bridge.shutdown();
    }

    FolderDialog {
        id: folderDialog
        property string targetKind: "reference"
        title: "Select folder"
        onAccepted: bridge.setFolderFromUrl(targetKind, selectedFolder)
    }

    MessageDialog {
        id: errorDialog
        title: "Error"
        text: ""
        onAccepted: close()
    }

    Connections {
        target: bridge
        function onErrorOccurred(title, message) {
            errorDialog.title = title;
            errorDialog.text = message;
            errorDialog.open();
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 76
            color: Theme.surface

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.border
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 22
                anchors.rightMargin: 22
                spacing: 14

                Rectangle {
                    width: 42
                    height: 42
                    radius: 12
                    color: Theme.accentSoft
                    border.width: 1
                    border.color: Theme.accent

                    Text {
                        anchors.centerIn: parent
                        text: "I"
                        color: Theme.accent
                        font.family: Theme.fontFamily
                        font.pixelSize: 20
                        font.weight: Font.Bold
                    }
                }

                ColumnLayout {
                    spacing: 1

                    Text {
                        text: "Imprint"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: 20
                        font.weight: Font.Bold
                    }

                    Text {
                        text: "Face similarity sorter"
                        color: Theme.textFaint
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                    }
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    implicitWidth: statusRow.implicitWidth + 24
                    implicitHeight: 32
                    radius: 16
                    color: Theme.surfaceAlt
                    border.width: 1
                    border.color: Theme.border

                    RowLayout {
                        id: statusRow
                        anchors.centerIn: parent
                        spacing: 8

                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: bridge.running
                                   ? (bridge.paused ? Theme.warning : Theme.accent)
                                   : Theme.success
                        }

                        Text {
                            text: bridge.running
                                  ? (bridge.paused ? "Paused" : "Running")
                                  : "Ready"
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                        }
                    }
                }

                AppButton {
                    text: Theme.dark ? "Light mode" : "Dark mode"
                    variant: "secondary"
                    implicitHeight: 34
                    implicitWidth: 104
                    font.pixelSize: 12
                    onClicked: Theme.dark = !Theme.dark
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.preferredWidth: 396
                Layout.fillHeight: true
                color: Theme.surface

                Rectangle {
                    anchors.right: parent.right
                    width: 1
                    height: parent.height
                    color: Theme.border
                }

                ScrollView {
                    id: sidebarScroll
                    anchors.fill: parent
                    anchors.margins: 16
                    anchors.bottomMargin: 166
                    clip: true
                    contentWidth: availableWidth
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    ColumnLayout {
                        width: sidebarScroll.availableWidth
                        spacing: 12

                        Text {
                            text: "1  FOLDERS"
                            color: Theme.textFaint
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            font.letterSpacing: 1.2
                        }

                        DropFolderCard {
                            Layout.fillWidth: true
                            title: "Reference faces"
                            path: bridge.referenceFolder
                            hint: "Drop the person's photos here or browse"
                            kind: "reference"
                            onBrowseRequested: {
                                folderDialog.targetKind = "reference";
                                folderDialog.open();
                            }
                            onFolderDropped: function (kind, url) {
                                bridge.setFolderFromUrl(kind, url);
                            }
                        }

                        DropFolderCard {
                            Layout.fillWidth: true
                            title: "Source images"
                            path: bridge.sourceFolder
                            hint: "Drop the folder to sort here or browse"
                            kind: "source"
                            onBrowseRequested: {
                                folderDialog.targetKind = "source";
                                folderDialog.open();
                            }
                            onFolderDropped: function (kind, url) {
                                bridge.setFolderFromUrl(kind, url);
                            }
                        }

                        DropFolderCard {
                            Layout.fillWidth: true
                            title: "Destination"
                            path: bridge.destinationFolder
                            hint: "Drop a folder for matched images here"
                            kind: "destination"
                            onBrowseRequested: {
                                folderDialog.targetKind = "destination";
                                folderDialog.open();
                            }
                            onFolderDropped: function (kind, url) {
                                bridge.setFolderFromUrl(kind, url);
                            }
                        }

                        Text {
                            Layout.topMargin: 4
                            text: "2  SETTINGS"
                            color: Theme.textFaint
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            font.letterSpacing: 1.2
                        }

                        Card {
                            Layout.fillWidth: true
                            implicitHeight: settingsColumn.implicitHeight + 28

                            ColumnLayout {
                                id: settingsColumn
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 12

                                Text {
                                    text: "Recognition model"
                                    color: Theme.text
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 12
                                }

                                AppComboBox {
                                    id: modelCombo
                                    Layout.fillWidth: true
                                    model: bridge.modelDisplayNames
                                    currentIndex: bridge.modelIndex
                                    onActivated: bridge.selectModel(index)
                                }

                                Text {
                                    text: "Antelope v2 prioritises accuracy; Buffalo S is the fastest."
                                    color: Theme.textFaint
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }

                                SettingSlider {
                                    label: "Distance threshold"
                                    help: "Lower values are stricter. Also controls reference consistency."
                                    from: 0.10
                                    to: 1.0
                                    stepSize: 0.01
                                    value: bridge.distanceThreshold
                                    onValueEdited: bridge.distanceThreshold = value
                                }

                                SettingSlider {
                                    label: "Face confidence"
                                    help: "Reject blurry or partial faces below this detection score."
                                    from: 0.10
                                    to: 1.0
                                    stepSize: 0.01
                                    value: bridge.confidenceThreshold
                                    onValueEdited: bridge.confidenceThreshold = value
                                }

                                Stepper {
                                    label: "Batch size"
                                    help: "Images per progress update group."
                                    from: 1
                                    to: 64
                                    value: bridge.batchSize
                                    onValueEdited: bridge.batchSize = value
                                }

                                Stepper {
                                    label: "Score subfolders"
                                    help: "Number of score-range destination folders."
                                    from: 1
                                    to: 50
                                    value: bridge.numberOfSubfolders
                                    onValueEdited: bridge.numberOfSubfolders = value
                                }

                                SettingSwitch {
                                    label: "Embedding cache"
                                    help: "Reuse embeddings for unchanged images to speed up reruns."
                                    value: bridge.cacheEnabled
                                    onToggled: bridge.cacheEnabled = value
                                }

                                AppButton {
                                    Layout.fillWidth: true
                                    text: "Reset recommended"
                                    variant: "ghost"
                                    implicitHeight: 30
                                    font.pixelSize: 11
                                    onClicked: bridge.resetRecommended()
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: tipColumn.implicitHeight + 24
                            radius: Theme.radius
                            color: Theme.accentSoft
                            border.width: 1
                            border.color: Theme.accent

                            ColumnLayout {
                                id: tipColumn
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 4

                                Text {
                                    text: "SHORTCUTS"
                                    color: Theme.accent
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 9
                                    font.weight: Font.Bold
                                    font.letterSpacing: 1
                                }

                                Text {
                                    text: "Ctrl+R run   Ctrl+P pause   Esc cancel   Ctrl+L clear log"
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        Item { Layout.preferredHeight: 8 }
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 166
                    color: Theme.surface

                    Rectangle {
                        anchors.top: parent.top
                        width: parent.width
                        height: 1
                        color: Theme.border
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        AppButton {
                            Layout.fillWidth: true
                            text: bridge.running ? "Analysis in progress..." : "Run analysis"
                            enabled: !bridge.running
                            onClicked: bridge.startAnalysis()
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            AppButton {
                                Layout.fillWidth: true
                                text: bridge.paused ? "Resume" : "Pause"
                                variant: "secondary"
                                enabled: bridge.running
                                onClicked: bridge.togglePause()
                            }

                            AppButton {
                                Layout.fillWidth: true
                                text: "Cancel"
                                variant: "danger"
                                enabled: bridge.running
                                onClicked: bridge.cancelAnalysis()
                            }
                        }

                        AppProgressBar {
                            Layout.fillWidth: true
                            value: bridge.progressValue
                        }

                        RowLayout {
                            Layout.fillWidth: true

                            Text {
                                text: bridge.progressText
                                color: Theme.textMuted
                                font.family: Theme.monoFamily
                                font.pixelSize: 10
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: bridge.statusText
                                color: Theme.textFaint
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                elide: Text.ElideRight
                                Layout.maximumWidth: 220
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 124
                    color: Theme.background

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 22
                        anchors.rightMargin: 22
                        anchors.topMargin: 16
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true

                            Text {
                                text: "Live results"
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: 20
                                font.weight: Font.Bold
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: bridge.statusText
                                color: Theme.textFaint
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                elide: Text.ElideRight
                                Layout.maximumWidth: 360
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            StatChip {
                                label: "Matched"
                                value: bridge.matchCount
                                accentColor: Theme.success
                            }

                            StatChip {
                                label: "Skipped"
                                value: bridge.skipCount
                                accentColor: Theme.textMuted
                            }

                            StatChip {
                                label: "Errors"
                                value: bridge.errorCount
                                accentColor: Theme.danger
                            }

                            StatChip {
                                label: "Processed"
                                value: bridge.processedCount
                                accentColor: Theme.accent
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: "of " + bridge.totalCount + " images"
                                color: Theme.textFaint
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? 58 : 0
                    visible: bridge.summaryText.length > 0
                    color: Theme.surface
                    border.width: 1
                    border.color: Theme.border
                    radius: Theme.radius
                    Layout.leftMargin: 22
                    Layout.rightMargin: 22
                    Layout.bottomMargin: 10

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 12
                        spacing: 12

                        Text {
                            text: bridge.summaryText.length > 0 ? bridge.summaryText.split("\n")[0] : ""
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        AppButton {
                            text: "Open folder"
                            variant: "secondary"
                            implicitHeight: 32
                            implicitWidth: 108
                            font.pixelSize: 12
                            onClicked: bridge.openDestination()
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 22
                    Layout.rightMargin: 22
                    Layout.topMargin: 4
                    Layout.bottomMargin: 10
                    spacing: 8

                    Text {
                        text: "Show"
                        color: Theme.textFaint
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                    }

                    AppButton {
                        objectName: "filterAll"
                        text: "All"
                        variant: bridge.resultFilter === "all" ? "secondary" : "ghost"
                        implicitHeight: 30
                        implicitWidth: 62
                        font.pixelSize: 11
                        onClicked: window.setResultFilter("all")
                    }

                    AppButton {
                        objectName: "filterMatches"
                        text: "Matches"
                        variant: bridge.resultFilter === "match" ? "secondary" : "ghost"
                        implicitHeight: 30
                        implicitWidth: 82
                        font.pixelSize: 11
                        onClicked: window.setResultFilter("match")
                    }

                    AppButton {
                        objectName: "filterSkipped"
                        text: "Skipped"
                        variant: bridge.resultFilter === "skip" ? "secondary" : "ghost"
                        implicitHeight: 30
                        implicitWidth: 82
                        font.pixelSize: 11
                        onClicked: window.setResultFilter("skip")
                    }

                    AppButton {
                        objectName: "filterErrors"
                        text: "Errors"
                        variant: bridge.resultFilter === "error" ? "secondary" : "ghost"
                        implicitHeight: 30
                        implicitWidth: 72
                        font.pixelSize: 11
                        onClicked: window.setResultFilter("error")
                    }

                    Item { Layout.fillWidth: true }

                    Text {
                        text: bridge.progressText
                        color: Theme.textFaint
                        font.family: Theme.monoFamily
                        font.pixelSize: 10
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    GridView {
                        id: resultsView
                        anchors.fill: parent
                        anchors.leftMargin: 22
                        anchors.rightMargin: 22
                        anchors.bottomMargin: 12
                        clip: true
                        cellWidth: Math.max(190, (width - 24) / 3)
                        cellHeight: 208
                        model: bridge.resultsProxy

                        delegate: ResultCard {
                            width: resultsView.cellWidth - 12
                            height: resultsView.cellHeight - 12
                            fileName: model.fileName
                            sourceUrl: model.sourceUrl
                            score: model.score
                            detScore: model.detScore
                            status: model.status
                            subfolder: model.subfolder
                            cached: model.cached
                            errorText: model.errorText
                            onClicked: window.openViewer(index)
                        }
                    }

                    ColumnLayout {
                        anchors.centerIn: parent
                        visible: resultsView.count === 0
                        spacing: 6

                        Text {
                            text: bridge.running ? "Scanning images..." : "No results yet"
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            Layout.alignment: Qt.AlignHCenter
                        }

                        Text {
                            text: bridge.running
                                  ? "Matched images will stream into this grid."
                                  : (bridge.matchCount + bridge.skipCount + bridge.errorCount > 0)
                                    ? "No images match this filter."
                                    : "Choose folders, then run an analysis."
                            color: Theme.textFaint
                            font.family: Theme.fontFamily
                            font.pixelSize: 12
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: window.logExpanded ? 190 : 44
                    color: Theme.surface

                    Rectangle {
                        anchors.top: parent.top
                        width: parent.width
                        height: 1
                        color: Theme.border
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: 16
                            Layout.rightMargin: 12
                            Layout.topMargin: 6
                            spacing: 8

                            Text {
                                text: "Activity log"
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }

                            Item { Layout.fillWidth: true }

                            AppButton {
                                text: "Clear"
                                variant: "ghost"
                                implicitHeight: 28
                                implicitWidth: 54
                                font.pixelSize: 10
                                onClicked: bridge.clearLog()
                            }

                            AppButton {
                                text: window.logExpanded ? "Hide" : "Show"
                                variant: "ghost"
                                implicitHeight: 28
                                implicitWidth: 54
                                font.pixelSize: 10
                                onClicked: window.logExpanded = !window.logExpanded
                            }
                        }

                        ListView {
                            id: logList
                            visible: window.logExpanded
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.leftMargin: 16
                            Layout.rightMargin: 12
                            Layout.bottomMargin: 8
                            clip: true
                            model: bridge.logModel
                            spacing: 1

                            delegate: Text {
                                width: logList.width
                                text: "[" + model.level + "]  " + model.message
                                color: model.level === "ERROR"
                                       ? Theme.danger
                                       : model.level === "WARNING"
                                         ? Theme.warning
                                         : Theme.textMuted
                                font.family: Theme.monoFamily
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: Theme.surface

            Rectangle {
                anchors.top: parent.top
                width: parent.width
                height: 1
                color: Theme.border
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 8

                Text {
                    text: "Imprint v" + bridge.version
                    color: Theme.textFaint
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: bridge.statusText
                    color: Theme.textFaint
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    elide: Text.ElideRight
                    Layout.maximumWidth: 600
                }
            }
        }
    }

    FocusScope {
        id: viewerScope
        anchors.fill: parent
        visible: viewerOpen
        focus: viewerOpen
        z: 100

        Keys.onEscapePressed: window.closeViewer()
        Keys.onLeftPressed: window.stepViewer(-1)
        Keys.onRightPressed: window.stepViewer(1)

        Rectangle {
            anchors.fill: parent
            color: "#B3000000"
        }

        MouseArea {
            anchors.fill: parent
            onClicked: window.closeViewer()
        }

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(parent.width - 100, 1100)
            height: Math.min(parent.height - 100, 760)
            radius: Theme.radiusLarge
            color: Theme.surface
            border.width: 1
            border.color: Theme.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text {
                        text: viewerData.fileName || ""
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        elide: Text.ElideMiddle
                        Layout.fillWidth: true
                    }

                    Text {
                        text: viewerData.status === "match" && viewerData.score >= 0
                              ? viewerData.score.toFixed(3)
                              : (viewerData.status || "").toUpperCase()
                        color: viewerData.status === "match"
                               ? Theme.success
                               : viewerData.status === "error"
                                 ? Theme.danger
                                 : Theme.textMuted
                        font.family: Theme.monoFamily
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                    }

                    AppButton {
                        text: "Close"
                        variant: "ghost"
                        implicitHeight: 32
                        implicitWidth: 70
                        font.pixelSize: 12
                        onClicked: window.closeViewer()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Theme.radius
                    color: Theme.background

                    Image {
                        anchors.fill: parent
                        anchors.margins: 8
                        source: viewerData.sourceUrl || ""
                        asynchronous: true
                        cache: false
                        fillMode: Image.PreserveAspectFit
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        text: viewerData.subfolder || viewerData.errorText || ""
                        color: viewerData.errorText ? Theme.danger : Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Text {
                        text: (viewerIndex + 1) + " / " + bridge.visibleResultCount
                        color: Theme.textFaint
                        font.family: Theme.monoFamily
                        font.pixelSize: 11
                    }

                    AppButton {
                        text: "Previous"
                        variant: "secondary"
                        implicitHeight: 32
                        implicitWidth: 92
                        font.pixelSize: 12
                        enabled: viewerIndex > 0
                        onClicked: window.stepViewer(-1)
                    }

                    AppButton {
                        text: "Next"
                        variant: "secondary"
                        implicitHeight: 32
                        implicitWidth: 76
                        font.pixelSize: 12
                        enabled: viewerIndex < bridge.visibleResultCount - 1
                        onClicked: window.stepViewer(1)
                    }
                }
            }
        }
    }
}
