"""Tests for the ToolTip widget."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock, patch

import pytest

from imprint.gui.tooltips import ToolTip


@pytest.fixture(scope="module")
def tk_root():
    """Provide a root window for widget testing."""
    root = tk.Tk()
    yield root
    root.destroy()


def test_tooltip_init(tk_root: tk.Tk) -> None:
    """Verify ToolTip binds correctly on init."""
    widget = tk.Label(tk_root, text="Hover me")
    widget.pack()

    tooltip = ToolTip(widget, text="Tooltip text", delay_ms=100)

    assert tooltip.text == "Tooltip text"
    assert tooltip._delay_ms == 100
    assert tooltip._tooltip_window is None


def test_tooltip_on_enter(tk_root: tk.Tk) -> None:
    """Verify entering the widget schedules the tooltip."""
    widget = tk.Label(tk_root, text="Hover me")
    widget.pack()

    tooltip = ToolTip(widget, text="Test", delay_ms=10)

    with patch.object(widget, "after", return_value="after_id_1") as mock_after:
        tooltip._on_enter(MagicMock())
        mock_after.assert_called_once_with(10, tooltip._show)
        assert tooltip._after_id == "after_id_1"


def test_tooltip_on_leave(tk_root: tk.Tk) -> None:
    """Verify leaving the widget cancels pending tooltips and hides them."""
    widget = tk.Label(tk_root, text="Hover me")
    widget.pack()

    tooltip = ToolTip(widget, text="Test")
    tooltip._after_id = "after_id_1"

    with patch.object(widget, "after_cancel") as mock_cancel:
        tooltip._on_leave(MagicMock())
        mock_cancel.assert_called_once_with("after_id_1")
        assert tooltip._after_id is None


def test_tooltip_show_and_hide(tk_root: tk.Tk) -> None:
    """Verify the tooltip creates and destroys a toplevel window."""
    widget = tk.Label(tk_root, text="Hover me")
    widget.pack()
    # Need to update to get valid geometry
    tk_root.update_idletasks()

    tooltip = ToolTip(widget, text="Testing tooltip popup")

    # Show
    tooltip._show()
    assert tooltip._tooltip_window is not None
    assert isinstance(tooltip._tooltip_window, tk.Toplevel)

    # Calling show again should not create a new window
    orig_window = tooltip._tooltip_window
    tooltip._show()
    assert tooltip._tooltip_window is orig_window

    # Hide
    tooltip._hide()
    assert tooltip._tooltip_window is None

    # Hide again is a no-op
    tooltip._hide()
    assert tooltip._tooltip_window is None
