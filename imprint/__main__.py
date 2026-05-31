"""Entry point for running Imprint as a module.

Usage:
    python -m imprint
"""

import sys


def main() -> None:
    """Launch the Imprint Face Sorter GUI application."""
    from imprint.gui.app import Application

    app = Application()
    app.mainloop()


if __name__ == "__main__":
    sys.exit(main())
