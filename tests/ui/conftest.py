"""Shared fixtures for UI tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from imprint.ui.bridge import AppBridge

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")


@pytest.fixture
def bridge(tmp_path: Path, qapp) -> AppBridge:
    """Create a bridge with isolated config and window settings."""
    settings = QSettings(str(tmp_path / "ui.ini"), QSettings.Format.IniFormat)
    instance = AppBridge(
        config_path=tmp_path / "config.ini",
        log_dir=tmp_path,
        qsettings=settings,
    )
    yield instance
    instance.shutdown()
