"""Tests for the application entry point."""

from __future__ import annotations

import builtins
import runpy
import sys
from unittest.mock import patch

import pytest

from imprint.__main__ import _launch_qml, _self_test, main


def test_launch_qml_delegates(monkeypatch) -> None:
    with patch("imprint.ui.app.main", return_value=7) as qml_main:
        assert _launch_qml() == 7
        qml_main.assert_called_once_with()


def test_main_launches_qml() -> None:
    with patch("imprint.__main__._launch_qml", return_value=0) as qml:
        assert main([]) == 0
        qml.assert_called_once_with()


def test_main_reads_sys_argv(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["imprint"])
    with patch("imprint.__main__._launch_qml", return_value=4) as qml:
        assert main() == 4
        qml.assert_called_once_with()


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


def test_main_other_exception_propagates() -> None:
    with patch("imprint.__main__._launch_qml", side_effect=ValueError("Unexpected")):
        with pytest.raises(ValueError, match="Unexpected"):
            main([])


def test_main_self_test_dispatch() -> None:
    with patch("imprint.__main__._self_test", return_value=0) as self_test:
        assert main(["--self-test"]) == 0
        self_test.assert_called_once_with()


def test_self_test_success() -> None:
    assert _self_test() == 0


def test_self_test_failure(monkeypatch, capsys) -> None:
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("insightface"):
            raise ImportError("missing insightface")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert _self_test() == 1
    assert "Self-test failed" in capsys.readouterr().err


def test_self_test_missing_face_analyser(monkeypatch) -> None:
    import types

    package = types.ModuleType("insightface")
    package.__path__ = []
    app_module = types.ModuleType("insightface.app")
    app_module.FaceAnalysis = None
    monkeypatch.setitem(sys.modules, "insightface", package)
    monkeypatch.setitem(sys.modules, "insightface.app", app_module)

    assert _self_test() == 1


def test_runpy_entrypoint(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["imprint"])
    with patch("imprint.ui.app.main", return_value=0):
        with pytest.raises(SystemExit) as exc:
            runpy.run_module("imprint.__main__", run_name="__main__")
    assert exc.value.code == 0
