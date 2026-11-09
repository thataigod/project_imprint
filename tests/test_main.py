"""Tests for the application entry point."""

from __future__ import annotations

import runpy
import sys
from unittest.mock import patch

import pytest

from imprint.__main__ import _launch_legacy, _launch_qml, main


class TclError(Exception):
    """Stand-in for tkinter.TclError during dispatch tests."""


def test_launch_qml_delegates(monkeypatch) -> None:
    with patch("imprint.ui.app.main", return_value=7) as qml_main:
        assert _launch_qml() == 7
        qml_main.assert_called_once_with()


def test_launch_legacy_delegates() -> None:
    with patch("imprint.gui.app.Application") as app_class:
        assert _launch_legacy() == 0
        app_class.assert_called_once_with()
        app_class.return_value.mainloop.assert_called_once_with()


def test_main_launches_qml_by_default() -> None:
    with (
        patch("imprint.__main__._launch_qml", return_value=0) as qml,
        patch("imprint.__main__._launch_legacy") as legacy,
    ):
        assert main([]) == 0
        qml.assert_called_once_with()
        legacy.assert_not_called()


def test_main_launches_legacy_with_flag() -> None:
    with (
        patch("imprint.__main__._launch_qml") as qml,
        patch("imprint.__main__._launch_legacy", return_value=3) as legacy,
    ):
        assert main(["--legacy"]) == 3
        legacy.assert_called_once_with()
        qml.assert_not_called()


def test_main_reads_sys_argv(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["imprint", "--legacy"])
    with patch("imprint.__main__._launch_legacy", return_value=4) as legacy:
        assert main() == 4
        legacy.assert_called_once_with()


def test_main_qml_import_error(capsys) -> None:
    with patch(
        "imprint.__main__._launch_qml",
        side_effect=ImportError("No module named PySide6"),
    ):
        assert main([]) == 1
    assert "PySide6 is installed" in capsys.readouterr().err


def test_main_qml_runtime_error(capsys) -> None:
    with patch(
        "imprint.__main__._launch_qml",
        side_effect=RuntimeError("Failed to load QML interface"),
    ):
        assert main([]) == 1
    assert "Failed to load QML interface" in capsys.readouterr().err


def test_main_legacy_tcl_error(capsys) -> None:
    with patch("imprint.__main__._launch_legacy", side_effect=TclError("no display")):
        assert main(["--legacy"]) == 1
    assert "Could not initialize graphical user interface" in capsys.readouterr().err


def test_main_legacy_import_error(capsys) -> None:
    with patch(
        "imprint.__main__._launch_legacy",
        side_effect=ImportError("No module named _tkinter"),
    ):
        assert main(["--legacy"]) == 1
    assert "No module named _tkinter" in capsys.readouterr().err


def test_main_other_exception_propagates() -> None:
    with patch("imprint.__main__._launch_qml", side_effect=ValueError("Unexpected")):
        with pytest.raises(ValueError, match="Unexpected"):
            main([])


def test_main_legacy_other_exception_propagates() -> None:
    with patch("imprint.__main__._launch_legacy", side_effect=ValueError("Unexpected")):
        with pytest.raises(ValueError, match="Unexpected"):
            main(["--legacy"])


def test_runpy_entrypoint(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["imprint"])
    with patch("imprint.ui.app.main", return_value=0):
        with pytest.raises(SystemExit) as exc:
            runpy.run_module("imprint.__main__", run_name="__main__")
    assert exc.value.code == 0
