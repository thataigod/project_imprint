"""Tooltip widget for Tkinter.

Provides a lightweight :class:`ToolTip` that displays a floating help
label when the user hovers over a widget.  This directly addresses the
UX gap identified in the code review: domain-specific settings like
"Distance Threshold" need inline explanations.

Usage::

    entry = ttk.Entry(parent)
    ToolTip(entry, text="Maximum cosine distance to consider a match.")
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional


class ToolTip:
    """Floating tooltip that appears on mouse hover.

    The tooltip is displayed as a borderless ``Toplevel`` window with a
    ``Label`` inside.  It appears after a configurable delay and
    disappears when the cursor leaves the widget.

    Args:
        widget: The Tkinter widget to attach the tooltip to.
        text: The help text to display.
        delay_ms: Milliseconds to wait before showing the tooltip.
        wrap_length: Maximum pixel width before text wraps.

    Attributes:
        widget: The attached widget.
        text: Current tooltip text (can be updated).
    """

    _BACKGROUND = "#333333"
    _FOREGROUND = "#f0f0f0"
    _FONT = ("Segoe UI", 9)
    _PADDING_X = 8
    _PADDING_Y = 4
    _OFFSET_X = 15
    _OFFSET_Y = 10

    def __init__(
        self,
        widget: tk.Widget,
        text: str,
        delay_ms: int = 500,
        wrap_length: int = 300,
    ) -> None:
        """Initialise and bind the tooltip to *widget*.

        Args:
            widget: Target widget.
            text: Help text to display on hover.
            delay_ms: Hover delay before the tooltip appears.
            wrap_length: Max width in pixels before wrapping.
        """
        self.widget = widget
        self.text = text
        self._delay_ms = delay_ms
        self._wrap_length = wrap_length
        self._tooltip_window: Optional[tk.Toplevel] = None
        self._after_id: Optional[str] = None

        self.widget.bind("<Enter>", self._on_enter)
        self.widget.bind("<Leave>", self._on_leave)
        self.widget.bind("<ButtonPress>", self._on_leave)

    # -- Event handlers -----------------------------------------------------

    def _on_enter(self, event: tk.Event) -> None:
        """Schedule tooltip display after the configured delay."""
        self._cancel_pending()
        self._after_id = self.widget.after(self._delay_ms, self._show)

    def _on_leave(self, event: tk.Event) -> None:
        """Cancel any pending display and hide the tooltip."""
        self._cancel_pending()
        self._hide()

    # -- Display logic ------------------------------------------------------

    def _show(self) -> None:
        """Create and position the tooltip window."""
        if self._tooltip_window is not None:
            return

        x = self.widget.winfo_rootx() + self._OFFSET_X
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + self._OFFSET_Y

        self._tooltip_window = tk.Toplevel(self.widget)
        self._tooltip_window.wm_overrideredirect(True)
        self._tooltip_window.wm_geometry(f"+{x}+{y}")
        self._tooltip_window.wm_attributes("-topmost", True)

        label = tk.Label(
            self._tooltip_window,
            text=self.text,
            background=self._BACKGROUND,
            foreground=self._FOREGROUND,
            font=self._FONT,
            relief="flat",
            padx=self._PADDING_X,
            pady=self._PADDING_Y,
            wraplength=self._wrap_length,
            justify="left",
        )
        label.pack()

    def _hide(self) -> None:
        """Destroy the tooltip window if it exists."""
        if self._tooltip_window is not None:
            self._tooltip_window.destroy()
            self._tooltip_window = None

    def _cancel_pending(self) -> None:
        """Cancel a pending ``after`` callback."""
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
