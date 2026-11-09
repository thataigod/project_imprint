#!/usr/bin/env python3
"""Convenience entry point for launching Imprint Face Sorter.

This script exists so that `start.bat` can simply call `python run.py`
without requiring the package to be installed via pip.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from imprint.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
