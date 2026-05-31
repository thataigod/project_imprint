"""Application-wide constants and model configurations.

This module centralises all magic numbers, supported file types, model
definitions, and default values so they can be maintained in one place
and imported throughout the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# File types
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
    ".jpg", ".jpeg", ".png", ".webp",
})
"""Image file extensions (lowercase, including dot) that the engine will process."""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIG_FILENAME: str = "config.ini"
"""Name of the persistent configuration file."""

DEFAULT_DETECTION_SIZE: tuple[int, int] = (640, 640)
"""Pixel dimensions passed to the face-detection model."""

COSINE_EPSILON: float = 1e-6
"""Small value added to norms to avoid division-by-zero in cosine distance."""

LOG_QUEUE_POLL_MS: int = 100
"""Milliseconds between GUI polls of the logging queue."""

MIN_REFERENCE_FACES: int = 2
"""Minimum number of valid reference faces required to build a core set."""

# ---------------------------------------------------------------------------
# Execution providers
# ---------------------------------------------------------------------------

ONNX_PROVIDERS: tuple[str, ...] = (
    "CUDAExecutionProvider",
    "CPUExecutionProvider",
)
"""Ordered list of ONNX Runtime execution providers."""

# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelProfile:
    """Immutable description of a supported face-recognition model.

    Attributes:
        code_name: Internal identifier passed to InsightFace.
        display_name: Human-readable label shown in the GUI.
        recommended_threshold: Suggested cosine-distance threshold.
        recommended_batch_size: Suggested batch size for progress grouping.
        use_rec_name: If True, model is loaded via ``rec_name`` kwarg
            instead of ``name`` (required for antelopev2).
    """

    code_name: str
    display_name: str
    recommended_threshold: float
    recommended_batch_size: int
    use_rec_name: bool = False


MODEL_REGISTRY: dict[str, ModelProfile] = {
    "antelopev2": ModelProfile(
        code_name="antelopev2",
        display_name="Antelope v2 (SOTA Accuracy)",
        recommended_threshold=0.5,
        recommended_batch_size=8,
        use_rec_name=True,
    ),
    "buffalo_l": ModelProfile(
        code_name="buffalo_l",
        display_name="Buffalo L (Balanced)",
        recommended_threshold=0.6,
        recommended_batch_size=16,
    ),
    "buffalo_s": ModelProfile(
        code_name="buffalo_s",
        display_name="Buffalo S (Fastest)",
        recommended_threshold=0.6,
        recommended_batch_size=32,
    ),
}
"""Registry of supported face-recognition models keyed by code name."""

DEFAULT_MODEL: str = "antelopev2"
"""Code name of the model selected by default."""


def get_model_by_display_name(display_name: str) -> ModelProfile | None:
    """Look up a model profile by its human-readable display name.

    Args:
        display_name: The display name string shown in the GUI.

    Returns:
        The matching ``ModelProfile``, or ``None`` if not found.
    """
    for profile in MODEL_REGISTRY.values():
        if profile.display_name == display_name:
            return profile
    return None
