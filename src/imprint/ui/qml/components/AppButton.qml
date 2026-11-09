import QtQuick
import QtQuick.Controls

Button {
    id: control
    property string variant: "primary"

    implicitHeight: 40
    implicitWidth: Math.max(96, contentItem.implicitWidth + 28)
    padding: 14
    font.family: Theme.fontFamily
    font.pixelSize: 14
    font.weight: Font.DemiBold

    contentItem: Text {
        text: control.text
        font: control.font
        color: {
            if (!control.enabled) {
                return Theme.textFaint
            }
            if (control.variant === "primary") {
                return Theme.accentText
            }
            if (control.variant === "danger") {
                return Theme.dangerText
            }
            if (control.variant === "ghost") {
                return Theme.textMuted
            }
            return Theme.text
        }
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: Theme.radius
        color: {
            if (!control.enabled) {
                return Theme.surfaceAlt
            }
            if (control.variant === "primary") {
                return control.down ? Theme.accentPressed : control.hovered ? Theme.accentHover : Theme.accent
            }
            if (control.variant === "danger") {
                return control.down ? Theme.dangerPressed : control.hovered ? Theme.dangerHover : Theme.dangerSoft
            }
            if (control.variant === "ghost") {
                return control.hovered ? Theme.surfaceAlt : "transparent"
            }
            return control.down ? Theme.surfacePressed : control.hovered ? Theme.surfaceHover : Theme.surfaceAlt
        }
        border.width: control.variant === "secondary" || control.variant === "danger" ? 1 : 0
        border.color: control.variant === "danger" ? Theme.danger : Theme.border
        Behavior on color {
            ColorAnimation { duration: 110 }
        }
    }
}
