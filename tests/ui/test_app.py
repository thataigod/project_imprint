"""Tests for the QML bootstrap module."""

from __future__ import annotations

import runpy
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication

from imprint.ui import app as ui_app
from imprint.ui.app import create_application, load_qml, main
from imprint.ui.bridge import AppBridge


def test_load_qml(bridge: AppBridge, qapp) -> None:
    engine = load_qml(bridge)
    assert engine.rootObjects()
    engine.deleteLater()


def test_filter_button_updates_bridge(bridge: AppBridge, qapp) -> None:
    engine = load_qml(bridge)
    root = engine.rootObjects()[0]
    button = root.findChild(QObject, "filterMatches")
    assert button is not None
    button.clicked.emit()
    qapp.processEvents()
    assert bridge.resultFilter == "match"
    engine.deleteLater()


def test_load_qml_missing_file(bridge: AppBridge, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Failed to load QML interface"):
        load_qml(bridge, tmp_path / "missing.qml")


def test_create_application_reuses_instance(bridge: AppBridge, qapp) -> None:
    app, engine, returned_bridge = create_application(bridge=bridge)
    assert app is QGuiApplication.instance()
    assert returned_bridge is bridge
    assert engine.rootObjects()
    engine.deleteLater()


def test_main_returns_event_loop_result(monkeypatch) -> None:
    fake_app = MagicMock()
    fake_app.exec.return_value = 0
    monkeypatch.setattr(
        ui_app,
        "create_application",
        MagicMock(return_value=(fake_app, MagicMock(), MagicMock())),
    )
    assert main() == 0
    fake_app.exec.assert_called_once_with()


def test_ui_main_module(monkeypatch) -> None:
    monkeypatch.setattr(ui_app, "main", MagicMock(return_value=0))
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("imprint.ui.__main__", run_name="__main__")
    assert exc.value.code == 0
