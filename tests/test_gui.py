"""Unit tests for the Tkinter GUI.

Contains basic smoke tests to ensure the application window
initialises and destroys cleanly without exceptions.
"""

from __future__ import annotations

import tkinter as tk

import pytest

from imprint.gui.app import Application


class TestApplicationGUI:
    """Smoke tests for the main Application window."""

    def test_application_init_and_destroy(self) -> None:
        """The main window should initialize and destroy without crashing."""
        # Create the app (this builds all widgets and variables)
        app = Application()
        
        # Verify it is a valid Tk instance
        assert isinstance(app, tk.Tk)
        assert app.title() == "Imprint GPU Face Sorter"
        
        # Call update to process any pending geometry/draw events
        app.update()
        
        # Destroy the app cleanly
        app.destroy()
