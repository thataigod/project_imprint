"""Compatibility shim for the legacy ``imprint.constants`` import path.

Canonical definitions live in :mod:`imprint.domain.constants`.
"""

from imprint.domain.constants import (
    CONFIG_FILENAME,
    COSINE_EPSILON,
    DEFAULT_DETECTION_SIZE,
    DEFAULT_MODEL,
    LOG_QUEUE_POLL_MS,
    MIN_REFERENCE_FACES,
    MODEL_REGISTRY,
    ONNX_PROVIDERS,
    SUPPORTED_EXTENSIONS,
    ModelProfile,
    get_model_by_display_name,
)

__all__ = [
    "CONFIG_FILENAME",
    "COSINE_EPSILON",
    "DEFAULT_DETECTION_SIZE",
    "DEFAULT_MODEL",
    "LOG_QUEUE_POLL_MS",
    "MIN_REFERENCE_FACES",
    "MODEL_REGISTRY",
    "ONNX_PROVIDERS",
    "SUPPORTED_EXTENSIONS",
    "ModelProfile",
    "get_model_by_display_name",
]
