"""Compatibility shim for the legacy ``imprint.math_utils`` import path.

Canonical implementations live in :mod:`imprint.domain.math`.
"""

from imprint.domain.math import (
    cosine_distance,
    cosine_distance_matrix,
    find_medoid_index,
    min_distance_to_references,
)

__all__ = [
    "cosine_distance",
    "cosine_distance_matrix",
    "find_medoid_index",
    "min_distance_to_references",
]
