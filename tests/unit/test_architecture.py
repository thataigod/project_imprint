"""Tests for the v6 package layout and v5 compatibility contract."""

from __future__ import annotations

import configparser
from pathlib import Path

import imprint
from imprint.config import AnalysisSettings as LegacyAnalysisSettings
from imprint.config import AppSettings
from imprint.config import ConfigManager as LegacyConfigManager
from imprint.config import PathSettings as LegacyPathSettings
from imprint.constants import MODEL_REGISTRY as LEGACY_MODEL_REGISTRY
from imprint.domain.constants import MODEL_REGISTRY
from imprint.domain.math import cosine_distance
from imprint.domain.settings import AnalysisSettings, PathSettings
from imprint.engine import SorterEngine
from imprint.engine.legacy import SorterEngine as LegacySorterEngine
from imprint.events import EngineEvent as LegacyEngineEvent
from imprint.events.types import EngineEvent
from imprint.math_utils import cosine_distance as legacy_cosine_distance
from imprint.platform.config import ConfigManager


def test_package_uses_src_layout() -> None:
    package_root = Path(imprint.__file__).resolve().parent
    assert package_root.name == "imprint"
    assert package_root.parent.name == "src"


def test_compatibility_shims_reexport_canonical_objects() -> None:
    assert LegacyAnalysisSettings is AnalysisSettings
    assert LegacyPathSettings is PathSettings
    assert LegacyConfigManager is ConfigManager
    assert LEGACY_MODEL_REGISTRY is MODEL_REGISTRY
    assert legacy_cosine_distance is cosine_distance
    assert LegacyEngineEvent is EngineEvent
    assert LegacySorterEngine is SorterEngine


def test_v5_config_keys_are_preserved(tmp_path: Path) -> None:
    config_path = tmp_path / "config.ini"
    manager = ConfigManager(filepath=config_path)
    manager.save(
        AppSettings(
            paths=LegacyPathSettings(
                reference_folder="/ref",
                source_folder="/src",
                destination_folder="/dst",
            ),
            analysis=AnalysisSettings(
                model_name="buffalo_l",
                distance_threshold=0.3,
                confidence_threshold=0.9,
                batch_size=16,
                number_of_subfolders=5,
            ),
        )
    )

    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    assert set(parser.sections()) == {"Paths", "Settings"}
    assert set(parser["Paths"]) == {
        "reference_folder",
        "source_folder",
        "destination_folder",
    }
    assert set(parser["Settings"]) == {
        "model_name",
        "distance_threshold",
        "confidence_threshold",
        "batch_size",
        "number_of_subfolders",
        "cache_enabled",
    }
    assert parser["Settings"]["model_name"] == "buffalo_l"
    assert parser["Paths"]["reference_folder"] == "/ref"
