"""Main application window for the Imprint Face Sorter.

This module contains the :class:`Application` class which orchestrates
the Tkinter GUI, manages user interactions, and launches the sorter
engine on a background thread.

**Thread-safety guarantee**: Every GUI mutation triggered by the engine
is routed through ``self.after()`` or the log queue, ensuring zero
direct Tkinter calls from the worker thread.
"""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from imprint import __version__
from imprint.config import (
    AnalysisSettings,
    AppSettings,
    ConfigManager,
    PathSettings,
    validate_analysis_settings,
    validate_path_settings,
)
from imprint.constants import (
    LOG_QUEUE_POLL_MS,
    MODEL_REGISTRY,
    get_model_by_display_name,
)
from imprint.engine import SorterEngine
from imprint.events import EngineEvent, EventType, MessageLevel
from imprint.gui.widgets import ModelSelector, PathSelector, SettingEntry
from imprint.logging_setup import configure_logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tooltip texts (centralised for easy editing)
# ---------------------------------------------------------------------------

_TIPS = {
    "reference": (
        "Folder containing clear photos of the person you want to find. "
        "Use multiple angles for best results. The app will automatically "
        "prune poor-quality or inconsistent photos."
    ),
    "source": (
        "Folder containing all the images you want to sort through. "
        "Subfolders are scanned recursively."
    ),
    "destination": (
        "Folder where matched images will be copied, organised into "
        "score-based subdirectories."
    ),
    "model": (
        "Antelope v2 = best accuracy (slowest). "
        "Buffalo L = balanced. "
        "Buffalo S = fastest (least accurate). "
        "Changing model auto-suggests threshold & batch size."
    ),
    "threshold": (
        "Maximum cosine distance to consider a match. "
        "Lower = stricter (fewer but more accurate matches). "
        "Also used to determine reference-set consistency."
    ),
    "confidence": (
        "Minimum face-detection confidence (0.0–1.0). "
        "Higher values reject blurry or partial faces. "
        "0.85 is a good starting point."
    ),
    "batch_size": (
        "Number of images per progress-update group. "
        "Does not affect accuracy — only controls how often "
        "the progress bar updates."
    ),
    "subfolders": (
        "How many score-range subdirectories to create in the "
        "destination folder. More subfolders = finer score granularity."
    ),
}


class Application(tk.Tk):
    """Main Imprint Face Sorter application window.

    The application is structured as:

    1. **Folder selectors** — reference, source, destination.
    2. **Settings panel** — model, threshold, confidence, batch, subfolders.
    3. **Action buttons** — Run / Cancel.
    4. **Progress bar** and status label.
    5. **Log panel** with right-click context menu.

    All engine events are funnelled through a thread-safe queue and
    processed on the main thread via :meth:`_poll_event_queue`.
    """

    _WINDOW_TITLE = f"Imprint Face Sorter v{__version__}"
    _WINDOW_MIN_SIZE = (720, 780)
    _WINDOW_DEFAULT_SIZE = "750x800"

    def __init__(self) -> None:
        """Initialise the application, load config, and build the UI."""
        super().__init__()
        self.title(self._WINDOW_TITLE)
        self.geometry(self._WINDOW_DEFAULT_SIZE)
        self.minsize(*self._WINDOW_MIN_SIZE)

        # -- State ----------------------------------------------------------
        self._config_manager = ConfigManager()
        self._settings = self._config_manager.load()
        self._cancel_event = threading.Event()
        self._event_queue: queue.Queue[EngineEvent] = queue.Queue()
        self._input_widgets: list[tk.Widget] = []

        # -- Logging --------------------------------------------------------
        self._log_queue: queue.Queue[str] = queue.Queue()
        configure_logging(self._log_queue)

        # -- Build UI -------------------------------------------------------
        self._build_ui()
        self._populate_from_settings()

        # -- Start polling --------------------------------------------------
        self._poll_log_queue()
        self._poll_event_queue()

    # ======================================================================
    # UI Construction
    # ======================================================================

    def _build_ui(self) -> None:
        """Construct the complete user interface."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        self._build_paths_section(main_frame)
        self._build_settings_section(main_frame)
        self._build_action_section(main_frame)
        self._build_log_section(main_frame)

    def _build_paths_section(self, parent: ttk.Frame) -> None:
        """Build the folder-selection section."""
        frame = ttk.LabelFrame(parent, text="1. Select Folders", padding=10)
        frame.pack(fill="x", pady=(0, 8))

        self._ref_selector = PathSelector(
            frame,
            label_text="Reference Folder (Your Character):",
            dialog_title="Select Reference Folder",
            tooltip_text=_TIPS["reference"],
        )
        self._ref_selector.pack(fill="x", pady=2)

        self._src_selector = PathSelector(
            frame,
            label_text="Source Folder (Images to Sort):",
            dialog_title="Select Source Folder",
            tooltip_text=_TIPS["source"],
        )
        self._src_selector.pack(fill="x", pady=2)

        self._dest_selector = PathSelector(
            frame,
            label_text="Destination Folder (Matches):",
            dialog_title="Select Destination Folder",
            tooltip_text=_TIPS["destination"],
        )
        self._dest_selector.pack(fill="x", pady=2)

        # Collect input widgets for state toggling
        for selector in (self._ref_selector, self._src_selector, self._dest_selector):
            self._input_widgets.extend(selector.input_widgets)

    def _build_settings_section(self, parent: ttk.Frame) -> None:
        """Build the settings / configuration section."""
        frame = ttk.LabelFrame(parent, text="2. Configure Settings", padding=10)
        frame.pack(fill="x", pady=(0, 8))

        # Model selector
        display_names = [p.display_name for p in MODEL_REGISTRY.values()]
        self._model_selector = ModelSelector(
            frame,
            model_display_names=display_names,
            on_select=self._on_model_selected,
            tooltip_text=_TIPS["model"],
        )
        self._model_selector.pack(fill="x", pady=2)
        self._input_widgets.extend(self._model_selector.input_widgets)

        # Numeric settings
        self._threshold_entry = SettingEntry(
            frame,
            label_text="Distance Threshold (lower=stricter):",
            tooltip_text=_TIPS["threshold"],
        )
        self._threshold_entry.pack(fill="x", pady=2)
        self._input_widgets.extend(self._threshold_entry.input_widgets)

        self._confidence_entry = SettingEntry(
            frame,
            label_text="Face Confidence (0.0 to 1.0):",
            tooltip_text=_TIPS["confidence"],
        )
        self._confidence_entry.pack(fill="x", pady=2)
        self._input_widgets.extend(self._confidence_entry.input_widgets)

        self._batch_entry = SettingEntry(
            frame,
            label_text="Batch Size (progress grouping):",
            tooltip_text=_TIPS["batch_size"],
        )
        self._batch_entry.pack(fill="x", pady=2)
        self._input_widgets.extend(self._batch_entry.input_widgets)

        self._subfolders_entry = SettingEntry(
            frame,
            label_text="Number of Subfolders:",
            tooltip_text=_TIPS["subfolders"],
        )
        self._subfolders_entry.pack(fill="x", pady=2)
        self._input_widgets.extend(self._subfolders_entry.input_widgets)

    def _build_action_section(self, parent: ttk.Frame) -> None:
        """Build the run/cancel buttons, progress bar, and status label."""
        frame = ttk.Frame(parent, padding=(0, 5))
        frame.pack(fill="x", pady=(0, 8))

        # Run button
        self._run_button = ttk.Button(
            frame,
            text="Save Config & Run Analysis",
            command=self._start_analysis,
        )
        self._run_button.pack(fill="x", pady=(0, 4))

        # Cancel button
        self._cancel_button = ttk.Button(
            frame,
            text="Cancel",
            command=self._cancel_analysis,
            state="disabled",
        )
        self._cancel_button.pack(fill="x", pady=(0, 4))

        # Progress bar
        self._progress_var = tk.DoubleVar()
        self._progress_bar = ttk.Progressbar(
            frame, variable=self._progress_var, maximum=100
        )
        self._progress_bar.pack(fill="x", pady=(0, 4))

        # Status label
        self._status_var = tk.StringVar(value="Ready.")
        self._status_label = ttk.Label(
            frame, textvariable=self._status_var, wraplength=680
        )
        self._status_label.pack(fill="x")

    def _build_log_section(self, parent: ttk.Frame) -> None:
        """Build the scrollable log panel with a right-click context menu."""
        frame = ttk.LabelFrame(parent, text="Log", padding=10)
        frame.pack(fill="both", expand=True)

        self._log_text = scrolledtext.ScrolledText(
            frame,
            state="disabled",
            height=10,
            wrap="word",
            font=("Consolas", 9),
            background="#1e1e1e",
            foreground="#d4d4d4",
            insertbackground="#d4d4d4",
        )
        self._log_text.pack(fill="both", expand=True)

        # Context menu
        self._log_menu = tk.Menu(self, tearoff=0)
        self._log_menu.add_command(label="Copy", command=self._copy_log)
        self._log_menu.add_separator()
        self._log_menu.add_command(label="Select All", command=self._select_all_log)
        self._log_menu.add_separator()
        self._log_menu.add_command(label="Clear", command=self._clear_log)
        self._log_text.bind("<Button-3>", self._show_log_menu)

    # ======================================================================
    # Settings Management
    # ======================================================================

    def _populate_from_settings(self) -> None:
        """Fill UI fields from the loaded settings."""
        paths = self._settings.paths
        analysis = self._settings.analysis

        self._ref_selector.path_var.set(paths.reference_folder)
        self._src_selector.path_var.set(paths.source_folder)
        self._dest_selector.path_var.set(paths.destination_folder)

        # Find display name for the model code
        profile = MODEL_REGISTRY.get(analysis.model_name)
        if profile:
            self._model_selector.model_var.set(profile.display_name)
        else:
            # Fallback to first model
            first = next(iter(MODEL_REGISTRY.values()))
            self._model_selector.model_var.set(first.display_name)

        self._threshold_entry.value_var.set(str(analysis.distance_threshold))
        self._confidence_entry.value_var.set(str(analysis.confidence_threshold))
        self._batch_entry.value_var.set(str(analysis.batch_size))
        self._subfolders_entry.value_var.set(str(analysis.number_of_subfolders))

    def _collect_settings(self) -> AppSettings:
        """Read current UI field values into an AppSettings object.

        Returns:
            The settings as currently displayed in the GUI.

        Raises:
            ValueError: If any numeric field contains an invalid value.
        """
        profile = get_model_by_display_name(self._model_selector.model_var.get())
        model_code = profile.code_name if profile else "antelopev2"

        paths = PathSettings(
            reference_folder=self._ref_selector.path_var.get().strip(),
            source_folder=self._src_selector.path_var.get().strip(),
            destination_folder=self._dest_selector.path_var.get().strip(),
        )

        analysis = AnalysisSettings(
            model_name=model_code,
            distance_threshold=float(self._threshold_entry.value_var.get()),
            confidence_threshold=float(self._confidence_entry.value_var.get()),
            batch_size=int(self._batch_entry.value_var.get()),
            number_of_subfolders=int(self._subfolders_entry.value_var.get()),
        )

        return AppSettings(paths=paths, analysis=analysis)

    def _on_model_selected(self, display_name: str) -> None:
        """Auto-populate recommended settings when a model is selected.

        Args:
            display_name: Human-readable model name from the combobox.
        """
        profile = get_model_by_display_name(display_name)
        if profile is None:
            return
        self._threshold_entry.value_var.set(str(profile.recommended_threshold))
        self._batch_entry.value_var.set(str(profile.recommended_batch_size))
        logger.info(
            "Selected model: %s. Recommended settings applied.", display_name
        )

    # ======================================================================
    # Analysis Lifecycle
    # ======================================================================

    def _start_analysis(self) -> None:
        """Validate settings and launch the engine on a background thread."""
        # Validate
        try:
            settings = self._collect_settings()
        except ValueError as exc:
            messagebox.showerror(
                "Invalid Input",
                f"Please check settings.\n\n"
                f"All numeric fields must be valid numbers.\n"
                f"Batch Size & Subfolders must be whole numbers > 0.\n\n"
                f"Error: {exc}",
                parent=self,
            )
            return

        path_errors = validate_path_settings(settings.paths)
        analysis_errors = validate_analysis_settings(settings.analysis)
        all_errors = path_errors + analysis_errors

        if all_errors:
            messagebox.showerror(
                "Validation Error",
                "Please fix the following issues:\n\n"
                + "\n".join(f"• {e}" for e in all_errors),
                parent=self,
            )
            return

        # Save config
        self._config_manager.save(settings)

        # Prepare UI
        self._set_ui_running(True)
        self._clear_log()
        self._cancel_event.clear()

        # Launch engine
        engine = SorterEngine(
            paths=settings.paths,
            analysis=settings.analysis,
            emit=self._enqueue_event,
            cancel_event=self._cancel_event,
        )
        worker = threading.Thread(target=engine.run, daemon=True)
        worker.start()

    def _cancel_analysis(self) -> None:
        """Request the engine to stop gracefully."""
        logger.warning("Cancel requested by user.")
        self._cancel_event.set()
        self._cancel_button.config(state="disabled")

    def _set_ui_running(self, running: bool) -> None:
        """Toggle the UI between 'running' and 'idle' states.

        Args:
            running: True to disable inputs; False to re-enable them.
        """
        state = "disabled" if running else "normal"
        for widget in self._input_widgets:
            widget.config(state=state)

        if running:
            self._run_button.config(state="disabled", text="Analysis in Progress...")
            self._cancel_button.config(state="normal")
        else:
            self._run_button.config(state="normal", text="Save Config & Run Analysis")
            self._cancel_button.config(state="disabled")
            self._progress_var.set(0)

    # ======================================================================
    # Thread-Safe Event Handling
    # ======================================================================

    def _enqueue_event(self, event: EngineEvent) -> None:
        """Thread-safe callback: enqueue an event for main-thread processing.

        This method is called from the worker thread and must NOT touch
        any Tkinter widgets.

        Args:
            event: The engine event to enqueue.
        """
        self._event_queue.put(event)

    def _poll_event_queue(self) -> None:
        """Drain the event queue and process events on the main thread."""
        try:
            while True:
                event = self._event_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.after(LOG_QUEUE_POLL_MS, self._poll_event_queue)

    def _handle_event(self, event: EngineEvent) -> None:
        """Dispatch a single engine event to the appropriate handler.

        This runs on the main thread, so Tkinter calls are safe.

        Args:
            event: The event to handle.
        """
        if event.event_type == EventType.PROGRESS:
            if event.total > 0:
                pct = (event.current / event.total) * 100
                self._progress_var.set(pct)
            self._status_var.set(event.message)

        elif event.event_type == EventType.STATUS:
            self._status_var.set(event.message)

        elif event.event_type == EventType.MESSAGE:
            if event.level == MessageLevel.ERROR:
                messagebox.showerror("Error", event.message, parent=self)
            elif event.level == MessageLevel.WARNING:
                messagebox.showwarning("Warning", event.message, parent=self)
            else:
                messagebox.showinfo("Information", event.message, parent=self)

        elif event.event_type == EventType.HALTED:
            self._set_ui_running(False)
            self._status_var.set(
                event.message or "Analysis halted. Check log for details."
            )

        elif event.event_type == EventType.FINISHED:
            self._set_ui_running(False)
            self._status_var.set("Finished. See summary in log or message box.")

    # ======================================================================
    # Log Panel
    # ======================================================================

    def _poll_log_queue(self) -> None:
        """Drain the log queue and append entries to the log panel."""
        try:
            while True:
                record = self._log_queue.get_nowait()
                self._log_text.config(state="normal")
                self._log_text.insert("end", record + "\n")
                self._log_text.yview("end")
                self._log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.after(LOG_QUEUE_POLL_MS, self._poll_log_queue)

    def _show_log_menu(self, event: tk.Event) -> None:
        """Display the log context menu.

        Args:
            event: The right-click event.
        """
        has_selection = bool(self._log_text.tag_ranges("sel"))
        self._log_menu.entryconfig("Copy", state="normal" if has_selection else "disabled")
        self._log_menu.tk_popup(event.x_root, event.y_root)

    def _copy_log(self) -> None:
        """Copy the selected log text to the clipboard."""
        if self._log_text.tag_ranges("sel"):
            self._log_text.event_generate("<<Copy>>")

    def _select_all_log(self) -> None:
        """Select all text in the log panel."""
        self._log_text.tag_add("sel", "1.0", "end")
        self._log_text.mark_set("insert", "1.0")
        self._log_text.see("insert")

    def _clear_log(self) -> None:
        """Clear all text from the log panel."""
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")
