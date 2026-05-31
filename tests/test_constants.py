"""Unit tests for imprint.constants.

Covers model registry, supported extensions, and lookup functions.
"""

from __future__ import annotations

import pytest

from imprint.constants import (
    DEFAULT_MODEL,
    MODEL_REGISTRY,
    SUPPORTED_EXTENSIONS,
    ModelProfile,
    get_model_by_display_name,
)


class TestSupportedExtensions:
    """Tests for SUPPORTED_EXTENSIONS."""

    def test_common_formats_included(self) -> None:
        """Common image formats should be in the set."""
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            assert ext in SUPPORTED_EXTENSIONS

    def test_is_frozen_set(self) -> None:
        """Extensions should be immutable."""
        assert isinstance(SUPPORTED_EXTENSIONS, frozenset)

    def test_all_lowercase(self) -> None:
        """All extensions should be lowercase."""
        for ext in SUPPORTED_EXTENSIONS:
            assert ext == ext.lower()

    def test_all_start_with_dot(self) -> None:
        """All extensions should start with a dot."""
        for ext in SUPPORTED_EXTENSIONS:
            assert ext.startswith(".")


class TestModelRegistry:
    """Tests for MODEL_REGISTRY."""

    def test_default_model_exists(self) -> None:
        """The DEFAULT_MODEL should be in the registry."""
        assert DEFAULT_MODEL in MODEL_REGISTRY

    def test_all_entries_are_model_profiles(self) -> None:
        """Every registry value should be a ModelProfile."""
        for profile in MODEL_REGISTRY.values():
            assert isinstance(profile, ModelProfile)

    def test_registry_has_three_models(self) -> None:
        """The registry should contain exactly 3 models."""
        assert len(MODEL_REGISTRY) == 3

    def test_code_names_match_keys(self) -> None:
        """Each key should match its profile's code_name."""
        for key, profile in MODEL_REGISTRY.items():
            assert key == profile.code_name

    def test_unique_display_names(self) -> None:
        """All display names should be unique."""
        names = [p.display_name for p in MODEL_REGISTRY.values()]
        assert len(names) == len(set(names))

    def test_positive_thresholds(self) -> None:
        """All recommended thresholds should be positive."""
        for profile in MODEL_REGISTRY.values():
            assert profile.recommended_threshold > 0

    def test_positive_batch_sizes(self) -> None:
        """All recommended batch sizes should be positive."""
        for profile in MODEL_REGISTRY.values():
            assert profile.recommended_batch_size > 0

    def test_model_profile_is_frozen(self) -> None:
        """ModelProfile instances should be immutable."""
        profile = MODEL_REGISTRY[DEFAULT_MODEL]
        with pytest.raises(AttributeError):
            profile.code_name = "hacked"  # type: ignore[misc]


class TestGetModelByDisplayName:
    """Tests for get_model_by_display_name()."""

    def test_finds_existing_model(self) -> None:
        """Should return the correct profile for a known display name."""
        for profile in MODEL_REGISTRY.values():
            result = get_model_by_display_name(profile.display_name)
            assert result is not None
            assert result.code_name == profile.code_name

    def test_returns_none_for_unknown(self) -> None:
        """Should return None for an unrecognised display name."""
        result = get_model_by_display_name("Nonexistent Model")
        assert result is None
