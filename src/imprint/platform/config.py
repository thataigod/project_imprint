"""Persistent INI configuration storage.

The :class:`ConfigManager` reads and writes the same ``config.ini`` file
and keys used by Imprint v5.  Keeping the on-disk contract stable lets a
v6 build pick up an existing user configuration without migration.
"""

from __future__ import annotations

import configparser
from pathlib import Path

from imprint.domain.constants import CONFIG_FILENAME
from imprint.domain.settings import AnalysisSettings, AppSettings, PathSettings


class ConfigManager:
    """Reads, writes, and validates a persistent INI configuration file.

    The manager guarantees that every expected key exists after
    :meth:`load` returns, falling back to defaults for any missing
    entries.  It never crashes on a malformed file - it simply fills
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
                self._SECTION_PATHS,
                "reference_folder",
                defaults.paths.reference_folder,
            ),
            source_folder=self._get(
                self._SECTION_PATHS,
                "source_folder",
                defaults.paths.source_folder,
            ),
            destination_folder=self._get(
                self._SECTION_PATHS,
                "destination_folder",
                defaults.paths.destination_folder,
            ),
        )

        analysis = AnalysisSettings(
            model_name=self._get(
                self._SECTION_SETTINGS,
                "model_name",
                defaults.analysis.model_name,
            ),
            distance_threshold=self._get_float(
                self._SECTION_SETTINGS,
                "distance_threshold",
                defaults.analysis.distance_threshold,
            ),
            confidence_threshold=self._get_float(
                self._SECTION_SETTINGS,
                "confidence_threshold",
                defaults.analysis.confidence_threshold,
            ),
            batch_size=self._get_int(
                self._SECTION_SETTINGS,
                "batch_size",
                defaults.analysis.batch_size,
            ),
            number_of_subfolders=self._get_int(
                self._SECTION_SETTINGS,
                "number_of_subfolders",
                defaults.analysis.number_of_subfolders,
            ),
        )

        return AppSettings(paths=paths, analysis=analysis)

    def save(self, settings: AppSettings) -> None:
        """Persist settings to the INI file.

        Args:
            settings: The settings to write.
        """
        self._parser.read_dict(
            {
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
            }
        )
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
