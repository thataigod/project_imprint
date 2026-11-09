"""Run the v6 QML interface as a module.

Usage:
    python -m imprint.ui
"""

from __future__ import annotations

import sys

from imprint.ui.app import main

if __name__ == "__main__":
    sys.exit(main())
