"""Compatibility shim for the legacy ``imprint.config`` import path.

Canonical settings live in :mod:`imprint.domain.settings`; persistence
lives in :mod:`imprint.platform.config`.
"""

from imprint.domain.settings import (
    AnalysisSettings,
    AppSettings,
    PathSettings,
    validate_analysis_settings,
    validate_path_settings,
)
from imprint.platform.config import ConfigManager

__all__ = [
    "AnalysisSettings",
    "AppSettings",
    "ConfigManager",
    "PathSettings",
    "validate_analysis_settings",
    "validate_path_settings",
]
