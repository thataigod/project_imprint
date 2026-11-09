"""Bootstrap for the v6 PySide6/QML desktop application."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from imprint.ui.bridge import AppBridge

QML_DIR = Path(__file__).resolve().parent / "qml"
MAIN_QML = QML_DIR / "Main.qml"


def load_qml(
    bridge: AppBridge,
    qml_path: Path | None = None,
) -> QQmlApplicationEngine:
    """Create a QML engine, expose the bridge, and load the main window."""
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("bridge", bridge)
    path = qml_path or MAIN_QML
    engine.load(QUrl.fromLocalFile(str(path)))
    if not engine.rootObjects():
        raise RuntimeError(f"Failed to load QML interface: {path}")
    return engine


def create_application(
    argv: list[str] | None = None,
    *,
    bridge: AppBridge | None = None,
) -> tuple[QGuiApplication, QQmlApplicationEngine, AppBridge]:
    """Create or reuse the Qt application and load the QML interface."""
    existing = QGuiApplication.instance()
    if existing is None:  # pragma: no cover - only on a cold start
        app = QGuiApplication(argv if argv is not None else sys.argv)
    else:
        app = cast(QGuiApplication, existing)

    app.setApplicationName("Imprint Face Sorter")
    app.setOrganizationName("Imprint")
    QQuickStyle.setStyle("Basic")

    app_bridge = bridge or AppBridge()
    engine = load_qml(app_bridge)
    app.aboutToQuit.connect(app_bridge.shutdown)
    return app, engine, app_bridge


def main() -> int:
    """Run the QML application event loop."""
    app, _engine, _bridge = create_application()
    return int(app.exec())
