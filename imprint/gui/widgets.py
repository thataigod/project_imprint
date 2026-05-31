"""Reusable compound GUI widgets for the Imprint application.

This module provides higher-level widgets composed from Tkinter
primitives, keeping the main :mod:`imprint.gui.app` module focused
on layout orchestration and business logic rather than low-level
widget construction.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable

from imprint.gui.tooltips import ToolTip


class PathSelector(ttk.Frame):
    """A labelled entry field with a Browse button.

    Encapsulates the common pattern of ``[Label] [Entry] [Browse...]``
    used for folder selection throughout the application.

    Args:
        parent: Parent widget.
        label_text: Label displayed to the left of the entry.
        dialog_title: Title for the folder-selection dialog.
        tooltip_text: Optional help text displayed on hover.

    Attributes:
        path_var: The :class:`tk.StringVar` holding the selected path.
    """

    def __init__(
        self,
        parent: tk.Widget,
        label_text: str,
        dialog_title: str = "Select Folder",
        tooltip_text: str | None = None,
    ) -> None:
        """Initialise the path selector.

        Args:
            parent: Container widget.
            label_text: Descriptive label.
            dialog_title: Title shown in the browse dialog.
            tooltip_text: Help text for the tooltip.
        """
        super().__init__(parent)

        self.path_var = tk.StringVar()
        self._dialog_title = dialog_title
        self._input_widgets: list[tk.Widget] = []

        # Label
        label = ttk.Label(self, text=label_text, width=32, anchor="w")
        label.pack(side="left", padx=(0, 5))

        # Entry
        self._entry = ttk.Entry(self, textvariable=self.path_var, width=50)
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._input_widgets.append(self._entry)

        # Browse button
        self._browse_btn = ttk.Button(self, text="Browse...", command=self._browse, width=10)
        self._browse_btn.pack(side="left")
        self._input_widgets.append(self._browse_btn)

        # Tooltip
        if tooltip_text:
            ToolTip(self._entry, text=tooltip_text)

    @property
    def input_widgets(self) -> list[tk.Widget]:
        """Return the interactive widgets for state toggling."""
        return list(self._input_widgets)

    def _browse(self) -> None:
        """Open a folder selection dialog."""
        path = filedialog.askdirectory(title=self._dialog_title)
        if path:
            self.path_var.set(path)


class SettingEntry(ttk.Frame):
    """A labelled entry field for a single setting value.

    Provides a consistent layout for numeric / text settings with
    an optional tooltip for inline help.

    Args:
        parent: Parent widget.
        label_text: Descriptive label.
        tooltip_text: Optional help text.
        entry_width: Character width of the entry field.

    Attributes:
        value_var: The :class:`tk.StringVar` holding the current value.
    """

    def __init__(
        self,
        parent: tk.Widget,
        label_text: str,
        tooltip_text: str | None = None,
        entry_width: int = 30,
    ) -> None:
        """Initialise the setting entry.

        Args:
            parent: Container widget.
            label_text: Descriptive label.
            tooltip_text: Help text for the tooltip.
            entry_width: Width of the input field.
        """
        super().__init__(parent)

        self.value_var = tk.StringVar()

        label = ttk.Label(self, text=label_text, width=32, anchor="w")
        label.pack(side="left", padx=(0, 5))

        self._entry = ttk.Entry(self, textvariable=self.value_var, width=entry_width)
        self._entry.pack(side="left")

        if tooltip_text:
            ToolTip(self._entry, text=tooltip_text)

    @property
    def input_widgets(self) -> list[tk.Widget]:
        """Return the interactive widgets for state toggling."""
        return [self._entry]


class ModelSelector(ttk.Frame):
    """A labelled combobox for selecting a recognition model.

    Fires an optional callback when the selection changes, allowing
    the parent to auto-populate recommended settings.

    Args:
        parent: Parent widget.
        model_display_names: List of human-readable model names.
        on_select: Optional callback invoked with the selected display name.
        tooltip_text: Optional help text.

    Attributes:
        model_var: The :class:`tk.StringVar` holding the current selection.
    """

    def __init__(
        self,
        parent: tk.Widget,
        model_display_names: list[str],
        on_select: Callable[[str], None] | None = None,
        tooltip_text: str | None = None,
    ) -> None:
        """Initialise the model selector.

        Args:
            parent: Container widget.
            model_display_names: Available model labels.
            on_select: Callback when selection changes.
            tooltip_text: Help text for the tooltip.
        """
        super().__init__(parent)

        self.model_var = tk.StringVar()
        self._on_select = on_select

        label = ttk.Label(self, text="Recognition Model:", width=32, anchor="w")
        label.pack(side="left", padx=(0, 5))

        self._combobox = ttk.Combobox(
            self,
            textvariable=self.model_var,
            values=model_display_names,
            state="readonly",
            width=35,
        )
        self._combobox.pack(side="left")
        self._combobox.bind("<<ComboboxSelected>>", self._handle_selection)

        if tooltip_text:
            ToolTip(self._combobox, text=tooltip_text)

    @property
    def input_widgets(self) -> list[tk.Widget]:
        """Return the interactive widgets for state toggling."""
        return [self._combobox]

    def _handle_selection(self, event: tk.Event) -> None:
        """Invoke the on_select callback with the chosen display name."""
        if self._on_select:
            self._on_select(self.model_var.get())
