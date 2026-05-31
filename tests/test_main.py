"""Tests for the application entry point."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from imprint.__main__ import main


def test_main_execution() -> None:
    """The main function should initialize the application and call mainloop."""
    with patch("imprint.gui.app.Application") as mock_app_class:
        mock_app_instance = MagicMock()
        mock_app_class.return_value = mock_app_instance

        main()

        # Verify the Application was instantiated
        mock_app_class.assert_called_once_with()
        # Verify mainloop was called
        mock_app_instance.mainloop.assert_called_once_with()


def test_main_execution_via_runpy() -> None:
    """Execute the module via runpy to cover the if __name__ == '__main__' block."""
    import runpy

    with patch("imprint.gui.app.Application") as mock_app_class:
        with patch.object(sys, "exit") as mock_exit:
            # Running as __main__ will trigger the block at the bottom of the file
            runpy.run_module("imprint.__main__", run_name="__main__")

            mock_app_class.assert_called_once()
            mock_app_class.return_value.mainloop.assert_called_once()
            mock_exit.assert_called_once_with(None)


def test_main_tcl_error() -> None:
    """The main function should exit gracefully with code 1 if a TclError is raised."""
    import tkinter

    with patch("imprint.gui.app.Application", side_effect=tkinter.TclError("no display name")):
        with patch.object(sys, "exit") as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)


def test_main_import_error() -> None:
    """The main function should exit gracefully with code 1 if an ImportError is raised."""
    with patch(
        "imprint.gui.app.Application", side_effect=ImportError("No module named '_tkinter'")
    ):
        with patch.object(sys, "exit") as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)


def test_main_other_exception_propagates() -> None:
    """The main function should propagate any other unexpected exceptions."""
    import pytest

    with patch("imprint.gui.app.Application", side_effect=ValueError("Unexpected error")):
        with pytest.raises(ValueError, match="Unexpected error"):
            main()
