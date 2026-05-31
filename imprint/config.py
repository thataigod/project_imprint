"""Configuration management with validation.

The :class:`ConfigManager` reads and writes an INI-format configuration
file, applies sensible defaults for missing keys, and validates all
values before they are consumed by the rest of the application.
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from imprint.constants import CONFIG_FILENAME, DEFAULT_MODEL, MODEL_REGISTRY


# ---------------------------------------------------------------------------
# Typed settings containers
# ---------------------------------------------------------------------------

@dataclass
class PathSettings:
    """User-configured folder paths.

    Attributes:
        reference_folder: Directory containing reference face images.
        source_folder: Directory of images to sort.
        destination_folder: Directory where matched images are copied.
    """

    reference_folder: str = ""
    source_folder: str = ""
    destination_folder: str = ""


@dataclass
class AnalysisSettings:
    """Numeric / model settings that govern the analysis.

    Attributes:
        model_name: Code name of the recognition model.
        distance_threshold: Max cosine distance to consider a match.
        confidence_threshold: Min face-detection confidence (0.0–1.0).
        batch_size: Images per progress-update group.
        number_of_subfolders: Tiered output subdirectory count.
    """

    model_name: str = DEFAULT_MODEL
    distance_threshold: float = 0.5
    confidence_threshold: float = 0.85
    batch_size: int = 8
    number_of_subfolders: int = 10


@dataclass
class AppSettings:
    """Top-level container holding all application settings.

    Attributes:
        paths: Folder path settings.
        analysis: Numeric / model analysis settings.
    """

    paths: PathSettings = field(default_factory=PathSettings)
    analysis: AnalysisSettings = field(default_factory=AnalysisSettings)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

class ConfigValidationError(ValueError):
    """Raised when a configuration value is out of range or invalid."""


def validate_analysis_settings(settings: AnalysisSettings) -> list[str]:
    """Validate numeric analysis settings and return a list of error strings.

    Args:
        settings: The analysis settings to validate.

    Returns:
        A list of human-readable error messages.  Empty if everything is valid.
    """
    errors: list[str] = []

    if settings.model_name not in MODEL_REGISTRY:
        errors.append(
            f"Unknown model '{settings.model_name}'. "
            f"Valid options: {', '.join(MODEL_REGISTRY.keys())}"
        )

    if settings.distance_threshold <= 0:
        errors.append("Distance threshold must be a positive number.")

    if not 0.0 <= settings.confidence_threshold <= 1.0:
        errors.append("Confidence threshold must be between 0.0 and 1.0.")

    if settings.batch_size < 1:
        errors.append("Batch size must be at least 1.")

    if settings.number_of_subfolders < 1:
        errors.append("Number of subfolders must be at least 1.")

    return errors


def validate_path_settings(settings: PathSettings) -> list[str]:
    """Validate path settings and return a list of error strings.

    Checks that all paths are provided and that source / destination
    do not overlap dangerously.

    Args:
        settings: The path settings to validate.

    Returns:
        A list of human-readable error messages.
    """
    errors: list[str] = []

    if not settings.reference_folder:
        errors.append("Reference folder is required.")
    if not settings.source_folder:
        errors.append("Source folder is required.")
    if not settings.destination_folder:
        errors.append("Destination folder is required.")

    # Guard against overlapping paths
    if settings.source_folder and settings.destination_folder:
        src = Path(settings.source_folder).resolve()
        dst = Path(settings.destination_folder).resolve()
        if src == dst:
            errors.append("Source and destination folders must be different.")
        if dst.is_relative_to(src):
            errors.append(
                "Destination folder must not be inside the source folder "
                "(this would cause recursive copying)."
            )

    if settings.reference_folder and settings.destination_folder:
        ref = Path(settings.reference_folder).resolve()
        dst = Path(settings.destination_folder).resolve()
        if ref == dst:
            errors.append("Reference and destination folders must be different.")

    return errors


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------

class ConfigManager:
    """Reads, writes, and validates a persistent INI configuration file.

    The manager guarantees that every expected key exists after
    :meth:`load` returns, falling back to defaults for any missing
    entries.  It never crashes on a malformed file — it simply fills
    in defaults and overwrites the file.

    Args:
        filepath: Path to the INI file.  Created automatically if absent.
    """

    _SECTION_PATHS = "Paths"
    _SECTION_SETTINGS = "Settings"

    def __init__(self, filepath: Path | None = None) -> None:
        """Initialise the config manager.

        Args:
            filepath: Override for the config file location.
                Defaults to ``CONFIG_FILENAME`` in the current directory.
        """
        self.filepath = filepath or Path(CONFIG_FILENAME)
        self._parser = configparser.ConfigParser()

    def load(self) -> AppSettings:
        """Load settings from disk, applying defaults for missing keys.

        If the file does not exist, it is created with all default values.

        Returns:
            A fully-populated :class:`AppSettings` instance.
        """
        defaults = AppSettings()

        if self.filepath.exists():
            self._parser.read(str(self.filepath), encoding="utf-8")
        else:
            self.save(defaults)
            return defaults

        paths = PathSettings(
            reference_folder=self._get(
                self._SECTION_PATHS, "reference_folder",
                defaults.paths.reference_folder,
            ),
            source_folder=self._get(
                self._SECTION_PATHS, "source_folder",
                defaults.paths.source_folder,
            ),
            destination_folder=self._get(
                self._SECTION_PATHS, "destination_folder",
                defaults.paths.destination_folder,
            ),
        )

        analysis = AnalysisSettings(
            model_name=self._get(
                self._SECTION_SETTINGS, "model_name",
                defaults.analysis.model_name,
            ),
            distance_threshold=self._get_float(
                self._SECTION_SETTINGS, "distance_threshold",
                defaults.analysis.distance_threshold,
            ),
            confidence_threshold=self._get_float(
                self._SECTION_SETTINGS, "confidence_threshold",
                defaults.analysis.confidence_threshold,
            ),
            batch_size=self._get_int(
                self._SECTION_SETTINGS, "batch_size",
                defaults.analysis.batch_size,
            ),
            number_of_subfolders=self._get_int(
                self._SECTION_SETTINGS, "number_of_subfolders",
                defaults.analysis.number_of_subfolders,
            ),
        )

        return AppSettings(paths=paths, analysis=analysis)

    def save(self, settings: AppSettings) -> None:
        """Persist settings to the INI file.

        Args:
            settings: The settings to write.
        """
        self._parser.read_dict({
            self._SECTION_PATHS: {
                "reference_folder": settings.paths.reference_folder,
                "source_folder": settings.paths.source_folder,
                "destination_folder": settings.paths.destination_folder,
            },
            self._SECTION_SETTINGS: {
                "model_name": settings.analysis.model_name,
                "distance_threshold": str(settings.analysis.distance_threshold),
                "confidence_threshold": str(settings.analysis.confidence_threshold),
                "batch_size": str(settings.analysis.batch_size),
                "number_of_subfolders": str(settings.analysis.number_of_subfolders),
            },
        })
        with open(self.filepath, "w", encoding="utf-8") as fh:
            self._parser.write(fh)

    # -- Private helpers ----------------------------------------------------

    def _get(self, section: str, key: str, default: str) -> str:
        """Read a string value with fallback."""
        try:
            return self._parser.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def _get_float(self, section: str, key: str, default: float) -> float:
        """Read a float value with fallback."""
        try:
            return self._parser.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def _get_int(self, section: str, key: str, default: int) -> int:
        """Read an int value with fallback."""
        try:
            return self._parser.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
