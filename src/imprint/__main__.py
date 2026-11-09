"""Entry point for the Imprint desktop application.

Usage:
    python -m imprint
    python -m imprint --self-test
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

_QML_ERROR = (
    "Error: Could not start the v6 interface.\n"
    "Details: {details}\n\n"
    "Please ensure that:\n"
    "  1. PySide6 is installed (pip install -r requirements.txt).\n"
    "  2. A display server (X11, Wayland, or Windows Desktop) is running.\n"
    "  3. You are not running in a headless SSH or Docker session without a virtual framebuffer."
)


def _launch_qml() -> int:
    """Launch the v6 QML application."""
    from imprint.ui.app import main as qml_main

    return qml_main()


def _self_test() -> int:
    """Import critical runtime dependencies for packaged-build verification."""
    try:
        import onnxruntime
        from insightface.app import FaceAnalysis
        from PySide6.QtCore import qVersion
    except Exception as exc:
        print(f"Self-test failed: {exc}", file=sys.stderr)
        return 1

    if FaceAnalysis is None or not qVersion() or onnxruntime is None:
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the QML interface and return a process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--self-test" in args:
        return _self_test()

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
