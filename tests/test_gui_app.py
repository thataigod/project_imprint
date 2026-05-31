"""Tests for the Tkinter GUI application."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from imprint.events import EngineEvent, MessageLevel
from imprint.gui.app import Application


@pytest.fixture
def gui_app():
    """Fixture providing a configured application instance."""
    with patch("imprint.gui.app.configure_logging"):
        with patch("tkinter.Tk.after"):  # Prevent polling from breaking tearDown
            app = Application()
            # Don't call mainloop, just update once to render
            app.update()
            yield app
            app.destroy()


def test_app_initialization(gui_app: Application) -> None:
    """Verify the app initializes correctly."""
    assert gui_app.title() == "Imprint Face Sorter v5.0.0"
    assert str(gui_app._run_button.cget("state")) == "normal"
    assert str(gui_app._cancel_button.cget("state")) == "disabled"


def test_app_start_analysis(gui_app: Application) -> None:
    """Verify that clicking start validates config and launches the engine."""
    with patch("imprint.gui.app.ConfigManager.load") as mock_load:
        mock_settings = MagicMock()
        mock_load.return_value = mock_settings

        with patch("imprint.gui.app.validate_path_settings", return_value=[]) as mock_vp:
            with patch("imprint.gui.app.validate_analysis_settings", return_value=[]) as mock_va:
                with patch("imprint.gui.app.SorterEngine") as mock_engine:
                    gui_app._start_analysis()

                    mock_vp.assert_called_once()
                    mock_va.assert_called_once()
                    mock_engine.assert_called_once()

                    assert str(gui_app._run_button.cget("state")) == "disabled"
                    assert str(gui_app._cancel_button.cget("state")) == "normal"


def test_app_start_validation_failure(gui_app: Application) -> None:
    """Verify that start button shows an error if settings are invalid."""
    with patch("imprint.gui.app.ConfigManager.load"):
        with patch("imprint.gui.app.validate_path_settings", return_value=["Path error"]):
            with patch("tkinter.messagebox.showerror") as mock_showerror:
                gui_app._start_analysis()
                mock_showerror.assert_called_once()
                assert str(gui_app._run_button.cget("state")) == "normal"


def test_app_cancel_clicked(gui_app: Application) -> None:
    """Verify cancel sets the flag and disables the button."""
    gui_app._cancel_event.clear()
    gui_app._cancel_button.configure(state="normal")

    gui_app._cancel_analysis()

    assert gui_app._cancel_event.is_set()
    assert str(gui_app._cancel_button.cget("state")) == "disabled"


def test_app_process_events_progress(gui_app: Application) -> None:
    """Verify progress events update the UI."""
    event = EngineEvent.progress(10, 100, "Testing")
    gui_app._event_queue.put(event)

    gui_app._poll_event_queue()

    # Progress variables should be updated
    assert gui_app._progress_var.get() == 10
    assert gui_app._status_var.get() == "Testing"


def test_app_process_events_finished(gui_app: Application) -> None:
    """Verify finished events reset the UI."""
    gui_app._run_button.configure(state="disabled")
    event = EngineEvent.finished()
    gui_app._event_queue.put(event)

    gui_app._poll_event_queue()

    assert str(gui_app._run_button.cget("state")) == "normal"
    assert str(gui_app._cancel_button.cget("state")) == "disabled"
    assert "Finished" in gui_app._status_var.get()


def test_app_process_events_message(gui_app: Application) -> None:
    """Verify message events show dialogs."""
    event = EngineEvent.show_message(MessageLevel.ERROR, "Bad thing")
    gui_app._event_queue.put(event)

    with patch("tkinter.messagebox.showerror") as mock_showerror:
        gui_app._poll_event_queue()
        mock_showerror.assert_called_once_with("Error", "Bad thing", parent=gui_app)


def test_app_poll_logs(gui_app: Application) -> None:
    """Verify log queue polling updates the text widget."""
    gui_app._log_queue.put("INFO: Test log")
    gui_app._poll_log_queue()

    text = gui_app._log_text.get("1.0", "end-1c")
    assert "INFO: Test log" in text
