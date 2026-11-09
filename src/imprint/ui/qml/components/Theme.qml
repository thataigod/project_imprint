pragma Singleton

import QtQuick

QtObject {
    id: theme
    property bool dark: true

    readonly property string fontFamily: "Segoe UI"
    readonly property string monoFamily: "Consolas"

    readonly property color background: dark ? "#0B0F14" : "#F3F6FB"
    readonly property color surface: dark ? "#111823" : "#FFFFFF"
    readonly property color surfaceAlt: dark ? "#182131" : "#EEF2F8"
    readonly property color surfaceHover: dark ? "#1E2A3D" : "#E5ECF6"
    readonly property color surfacePressed: dark ? "#243349" : "#DCE6F2"
    readonly property color border: dark ? "#243044" : "#D6E0EC"

    readonly property color text: dark ? "#E8EEF7" : "#101828"
    readonly property color textMuted: dark ? "#93A4BC" : "#4A5A70"
    readonly property color textFaint: dark ? "#64748B" : "#7A8AA0"

    readonly property color accent: "#5B8CFF"
    readonly property color accentHover: "#7AA2FF"
    readonly property color accentPressed: "#4775E0"
    readonly property color accentSoft: dark ? "#1D2C4D" : "#E3EBFF"
    readonly property color accentText: "#FFFFFF"

    readonly property color success: "#3DD68C"
    readonly property color successSoft: dark ? "#143528" : "#E0F7EC"
    readonly property color warning: "#F5B54A"
    readonly property color warningSoft: dark ? "#392C13" : "#FDF3DF"
    readonly property color danger: "#FF6B6B"
    readonly property color dangerHover: "#FF8585"
    readonly property color dangerPressed: "#E05555"
    readonly property color dangerSoft: dark ? "#3A1B1F" : "#FDE8E8"
    readonly property color dangerText: "#FFFFFF"

    readonly property int radius: 9
    readonly property int radiusLarge: 14
    readonly property int spacing: 14
}
