"""Unit tests for imprint.config.

Covers ConfigManager load/save, validation functions, and edge cases
like missing files, malformed values, and path overlap detection.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from imprint.config import (
    AnalysisSettings,
    AppSettings,
    ConfigManager,
    PathSettings,
    validate_analysis_settings,
    validate_path_settings,
)


class TestConfigManager:
    """Tests for ConfigManager load/save lifecycle."""

    def test_creates_file_on_first_load(self, tmp_path: Path) -> None:
        """Loading when no file exists should create one with defaults."""
        config_path = tmp_path / "config.ini"
        manager = ConfigManager(filepath=config_path)
        settings = manager.load()

        assert config_path.exists()
        assert settings.analysis.model_name == "antelopev2"
        assert settings.analysis.distance_threshold == 0.5
        assert settings.analysis.confidence_threshold == 0.85
        assert settings.analysis.batch_size == 8
        assert settings.analysis.number_of_subfolders == 10

    def test_save_and_reload_preserves_values(self, tmp_path: Path) -> None:
        """Saving then reloading should preserve all values."""
        config_path = tmp_path / "config.ini"
        manager = ConfigManager(filepath=config_path)

        original = AppSettings(
            paths=PathSettings(
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
        manager.save(original)

        reloaded = manager.load()
        assert reloaded.paths.reference_folder == "/ref"
        assert reloaded.paths.source_folder == "/src"
        assert reloaded.paths.destination_folder == "/dst"
        assert reloaded.analysis.model_name == "buffalo_l"
        assert reloaded.analysis.distance_threshold == pytest.approx(0.3)
        assert reloaded.analysis.confidence_threshold == pytest.approx(0.9)
        assert reloaded.analysis.batch_size == 16
        assert reloaded.analysis.number_of_subfolders == 5

    def test_malformed_values_use_defaults(self, tmp_path: Path) -> None:
        """Malformed numeric values should fall back to defaults."""
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[Paths]\n"
            "reference_folder = /ref\n"
            "[Settings]\n"
            "distance_threshold = not_a_number\n"
            "batch_size = xyz\n",
            encoding="utf-8",
        )
        manager = ConfigManager(filepath=config_path)
        settings = manager.load()

        # Should use defaults for malformed values
        assert settings.analysis.distance_threshold == 0.5
        assert settings.analysis.batch_size == 8
        # Should preserve valid values
        assert settings.paths.reference_folder == "/ref"

    def test_missing_sections_use_defaults(self, tmp_path: Path) -> None:
        """A config file with missing sections should fill in defaults."""
        config_path = tmp_path / "config.ini"
        config_path.write_text("[Paths]\nreference_folder = /ref\n", encoding="utf-8")
        manager = ConfigManager(filepath=config_path)
        settings = manager.load()

        assert settings.paths.reference_folder == "/ref"
        assert settings.analysis.model_name == "antelopev2"

    def test_empty_file_uses_all_defaults(self, tmp_path: Path) -> None:
        """An empty config file should yield all default values."""
        config_path = tmp_path / "config.ini"
        config_path.write_text("", encoding="utf-8")
        manager = ConfigManager(filepath=config_path)
        settings = manager.load()

        defaults = AppSettings()
        assert settings.analysis.model_name == defaults.analysis.model_name
        assert settings.analysis.distance_threshold == defaults.analysis.distance_threshold


class TestValidateAnalysisSettings:
    """Tests for validate_analysis_settings()."""

    def test_valid_settings_return_no_errors(self) -> None:
        """Valid settings should produce an empty error list."""
        settings = AnalysisSettings()
        errors = validate_analysis_settings(settings)
        assert errors == []

    def test_unknown_model_name(self) -> None:
        """An unrecognised model name should produce an error."""
        settings = AnalysisSettings(model_name="nonexistent_model")
        errors = validate_analysis_settings(settings)
        assert any("Unknown model" in e for e in errors)

    def test_negative_threshold(self) -> None:
        """A negative distance threshold should produce an error."""
        settings = AnalysisSettings(distance_threshold=-0.1)
        errors = validate_analysis_settings(settings)
        assert any("positive" in e.lower() for e in errors)

    def test_zero_threshold(self) -> None:
        """A zero distance threshold should produce an error."""
        settings = AnalysisSettings(distance_threshold=0.0)
        errors = validate_analysis_settings(settings)
        assert any("positive" in e.lower() for e in errors)

    def test_confidence_out_of_range_high(self) -> None:
        """Confidence > 1.0 should produce an error."""
        settings = AnalysisSettings(confidence_threshold=1.5)
        errors = validate_analysis_settings(settings)
        assert any("between 0.0 and 1.0" in e for e in errors)

    def test_confidence_out_of_range_low(self) -> None:
        """Confidence < 0.0 should produce an error."""
        settings = AnalysisSettings(confidence_threshold=-0.1)
        errors = validate_analysis_settings(settings)
        assert any("between 0.0 and 1.0" in e for e in errors)

    def test_batch_size_zero(self) -> None:
        """Batch size of 0 should produce an error."""
        settings = AnalysisSettings(batch_size=0)
        errors = validate_analysis_settings(settings)
        assert any("batch" in e.lower() for e in errors)

    def test_negative_subfolders(self) -> None:
        """Negative subfolder count should produce an error."""
        settings = AnalysisSettings(number_of_subfolders=-1)
        errors = validate_analysis_settings(settings)
        assert any("subfolder" in e.lower() for e in errors)

    def test_multiple_errors_at_once(self) -> None:
        """Multiple invalid fields should all produce errors."""
        settings = AnalysisSettings(
            model_name="bad",
            distance_threshold=-1.0,
            confidence_threshold=2.0,
            batch_size=0,
            number_of_subfolders=0,
        )
        errors = validate_analysis_settings(settings)
        assert len(errors) >= 4


class TestValidatePathSettings:
    """Tests for validate_path_settings()."""

    def test_valid_paths_return_no_errors(self, tmp_path: Path) -> None:
        """Valid, non-overlapping paths should produce no errors."""
        ref = tmp_path / "ref"
        src = tmp_path / "src"
        ref.mkdir()
        src.mkdir()
        settings = PathSettings(
            reference_folder=str(ref),
            source_folder=str(src),
            destination_folder=str(tmp_path / "dst"),
        )
        errors = validate_path_settings(settings)
        assert errors == []

    def test_paths_must_exist(self, tmp_path: Path) -> None:
        """Non-existent reference or source folders should produce errors."""
        settings = PathSettings(
            reference_folder=str(tmp_path / "nonexistent_ref"),
            source_folder=str(tmp_path / "nonexistent_src"),
            destination_folder=str(tmp_path / "dst"),
        )
        errors = validate_path_settings(settings)
        assert any("Reference folder does not exist" in e for e in errors)
        assert any("Source folder does not exist" in e for e in errors)

    def test_empty_reference_folder(self, tmp_path: Path) -> None:
        """An empty reference folder should produce an error."""
        src = tmp_path / "src"
        src.mkdir()
        settings = PathSettings(
            reference_folder="",
            source_folder=str(src),
            destination_folder=str(tmp_path / "dst"),
        )
        errors = validate_path_settings(settings)
        assert any("reference" in e.lower() for e in errors)

    def test_empty_source_folder(self, tmp_path: Path) -> None:
        """An empty source folder should produce an error."""
        ref = tmp_path / "ref"
        ref.mkdir()
        settings = PathSettings(
            reference_folder=str(ref),
            source_folder="",
            destination_folder=str(tmp_path / "dst"),
        )
        errors = validate_path_settings(settings)
        assert any("source" in e.lower() for e in errors)

    def test_empty_destination_folder(self, tmp_path: Path) -> None:
        """An empty destination folder should produce an error."""
        ref = tmp_path / "ref"
        ref.mkdir()
        src = tmp_path / "src"
        src.mkdir()
        settings = PathSettings(
            reference_folder=str(ref),
            source_folder=str(src),
            destination_folder="",
        )
        errors = validate_path_settings(settings)
        assert any("destination" in e.lower() for e in errors)

    def test_source_equals_destination(self, tmp_path: Path) -> None:
        """Source = destination should produce an error."""
        ref = tmp_path / "ref"
        ref.mkdir()
        same = tmp_path / "same"
        same.mkdir()
        settings = PathSettings(
            reference_folder=str(ref),
            source_folder=str(same),
            destination_folder=str(same),
        )
        errors = validate_path_settings(settings)
        assert any("different" in e.lower() for e in errors)

    def test_destination_inside_source(self, tmp_path: Path) -> None:
        """Destination inside source should produce an error."""
        ref = tmp_path / "ref"
        ref.mkdir()
        src = tmp_path / "source"
        src.mkdir()
        dst = src / "output"
        settings = PathSettings(
            reference_folder=str(ref),
            source_folder=str(src),
            destination_folder=str(dst),
        )
        errors = validate_path_settings(settings)
        assert any("inside" in e.lower() for e in errors)

    def test_reference_equals_destination(self, tmp_path: Path) -> None:
        """Reference = destination should produce an error."""
        same = tmp_path / "same"
        same.mkdir()
        src = tmp_path / "src"
        src.mkdir()
        settings = PathSettings(
            reference_folder=str(same),
            source_folder=str(src),
            destination_folder=str(same),
        )
        errors = validate_path_settings(settings)
        assert any("different" in e.lower() for e in errors)
