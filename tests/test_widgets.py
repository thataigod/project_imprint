"""Tests for the reusable Tkinter widgets."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock, patch

import pytest

from imprint.gui.widgets import ModelSelector, PathSelector, SettingEntry


@pytest.fixture(scope="module")
def tk_root():
    """Provide a root window for widget testing."""
    root = tk.Tk()
    yield root
    root.destroy()


def test_path_selector_init(tk_root: tk.Tk) -> None:
    """Verify PathSelector initializes correctly."""
    selector = PathSelector(
        tk_root, label_text="Test Label", dialog_title="Test Dialog", tooltip_text="Test Tooltip"
    )
    selector.pack()

    assert selector.path_var.get() == ""
    assert len(selector.input_widgets) == 2  # Entry and Button
    assert "Test Label" in selector.winfo_children()[0].cget("text")


def test_path_selector_browse(tk_root: tk.Tk) -> None:
    """Verify browsing for a folder updates the path variable."""
    selector = PathSelector(tk_root, "Label", "Dialog", "Tooltip")

    with patch("tkinter.filedialog.askdirectory", return_value="/fake/path"):
        selector._browse()
        assert selector.path_var.get() == "/fake/path"


def test_path_selector_browse_cancelled(tk_root: tk.Tk) -> None:
    """Verify canceling the browse dialog doesn't overwrite an existing path."""
    selector = PathSelector(tk_root, "Label", "Dialog", "Tooltip")
    selector.path_var.set("/existing/path")

    with patch("tkinter.filedialog.askdirectory", return_value=""):
        selector._browse()
        assert selector.path_var.get() == "/existing/path"


def test_model_selector_init(tk_root: tk.Tk) -> None:
    """Verify ModelSelector initializes correctly."""
    mock_on_select = MagicMock()
    selector = ModelSelector(
        tk_root,
        model_display_names=["Model A", "Model B"],
        on_select=mock_on_select,
        tooltip_text="Tooltip",
    )
    selector.pack()

    assert selector.model_var.get() == ""
    assert len(selector.input_widgets) == 1

    # Simulate a user selecting the second option
    selector.model_var.set("Model B")
    selector._handle_selection(None)
    mock_on_select.assert_called_once_with("Model B")


def test_setting_entry_init(tk_root: tk.Tk) -> None:
    """Verify SettingEntry initializes correctly."""
    entry = SettingEntry(tk_root, label_text="Test Setting:", tooltip_text="Test Tooltip")
    entry.pack()

    assert entry.value_var.get() == ""
    assert len(entry.input_widgets) == 1
