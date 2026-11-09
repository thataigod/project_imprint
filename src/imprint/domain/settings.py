"""Typed settings containers and validation rules.

These models are UI- and storage-agnostic.  Persistence lives in
:mod:`imprint.platform.config`, while the numeric rules remain here so
both the desktop UI and the engine validate the same way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from imprint.domain.constants import DEFAULT_MODEL, MODEL_REGISTRY

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
        confidence_threshold: Min face-detection confidence (0.0-1.0).
        batch_size: Images per progress-update group.
        number_of_subfolders: Tiered output subdirectory count.
        cache_enabled: Reuse embeddings from the SQLite cache.
    """

    model_name: str = DEFAULT_MODEL
    distance_threshold: float = 0.5
    confidence_threshold: float = 0.85
    batch_size: int = 8
    number_of_subfolders: int = 10
    cache_enabled: bool = True


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

    Checks that all paths are provided, that they exist on disk,
    and that source / destination do not overlap dangerously.

    Args:
        settings: The path settings to validate.

    Returns:
        A list of human-readable error messages.
    """
    errors: list[str] = []

    if not settings.reference_folder:
        errors.append("Reference folder is required.")
    elif not Path(settings.reference_folder).is_dir():
        errors.append("Reference folder does not exist or is not a directory.")

    if not settings.source_folder:
        errors.append("Source folder is required.")
    elif not Path(settings.source_folder).is_dir():
        errors.append("Source folder does not exist or is not a directory.")

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
