"""Entry point for Imprint.

The default interface is the v6 PySide6/QML application.  Pass
``--legacy`` to launch the Tkinter interface during the transition.

Usage:
    python -m imprint
    python -m imprint --legacy
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

_LEGACY_ERROR = (
    "Error: Could not initialize graphical user interface.\n"
    "Details: {details}\n\n"
    "Please ensure that:\n"
    "  1. A display server (X11, Wayland, or Windows Desktop) is running.\n"
    "  2. Tcl/Tk is installed and properly configured on your system.\n"
    "  3. You are not running in a headless SSH or Docker session without a virtual framebuffer."
)

_QML_ERROR = (
    "Error: Could not start the v6 interface.\n"
    "Details: {details}\n\n"
    "Please ensure that:\n"
    "  1. PySide6 is installed (pip install -r requirements.txt).\n"
    "  2. A display server (X11, Wayland, or Windows Desktop) is running.\n"
    "  3. You are not running in a headless SSH or Docker session without a virtual framebuffer.\n\n"
    "The legacy Tkinter interface is still available with --legacy."
)


def _launch_qml() -> int:
    """Launch the v6 QML application."""
    from imprint.ui.app import main as qml_main

    return qml_main()


def _launch_legacy() -> int:
    """Launch the legacy Tkinter application."""
    from imprint.gui.app import Application

    app = Application()
    app.mainloop()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the requested interface and return a process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--legacy" in args:
        try:
            return _launch_legacy()
        except Exception as exc:
            if type(exc).__name__ == "TclError" or isinstance(exc, ImportError):
                print(_LEGACY_ERROR.format(details=exc), file=sys.stderr)
                return 1
            raise

    try:
        return _launch_qml()
    except ImportError as exc:
        print(_QML_ERROR.format(details=exc), file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(_QML_ERROR.format(details=exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
