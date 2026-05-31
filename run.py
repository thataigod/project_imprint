#!/usr/bin/env python3
"""Convenience entry point for launching Imprint Face Sorter.

This script exists so that `start.bat` can simply call `python run.py`
without requiring the package to be installed via pip.
"""

from imprint.__main__ import main

if __name__ == "__main__":
    main()
