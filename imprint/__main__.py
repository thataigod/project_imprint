"""Entry point for running Imprint as a module.

Usage:
    python -m imprint
"""

import sys


def main() -> None:
    """Launch the Imprint Face Sorter GUI application."""
    try:
        from imprint.gui.app import Application

        app = Application()
        app.mainloop()
    except Exception as exc:
        exc_type_name = type(exc).__name__
        if exc_type_name == "TclError" or isinstance(exc, ImportError):
            print(
                f"Error: Could not initialize graphical user interface.\n"
                f"Details: {exc}\n\n"
                f"Please ensure that:\n"
                f"  1. A display server (X11, Wayland, or Windows Desktop) is running.\n"
                f"  2. Tcl/Tk is installed and properly configured on your system.\n"
                f"  3. You are not running in a headless SSH or Docker session without a virtual framebuffer.",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            raise



if __name__ == "__main__":
    sys.exit(main())
