"""Compatibility shim for the legacy ``imprint.logging_setup`` import path.

Canonical implementation lives in :mod:`imprint.platform.logging`.
"""

from imprint.platform.logging import QueueHandler, configure_logging

__all__ = ["QueueHandler", "configure_logging"]
