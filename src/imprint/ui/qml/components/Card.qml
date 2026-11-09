import QtQuick

Rectangle {
    id: root
    property int cornerRadius: Theme.radiusLarge
    radius: cornerRadius
    color: Theme.surface
    border.width: 1
    border.color: Theme.border
}
