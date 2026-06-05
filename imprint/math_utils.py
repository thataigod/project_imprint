"""Mathematical utilities for face-embedding comparison.

All functions in this module operate on numpy arrays and are designed
to be deterministic, side-effect-free, and fully unit-testable without
any GPU or model dependencies.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from imprint.constants import COSINE_EPSILON


def cosine_distance(a: NDArray[np.floating], b: NDArray[np.floating]) -> float:
    """Compute the cosine distance between two 1-D vectors.

    Cosine distance is defined as ``1 - cosine_similarity``.  A small
    epsilon is added to the denominator to prevent division by zero.

    Args:
        a: First embedding vector (any shape; will be flattened).
        b: Second embedding vector (any shape; will be flattened).

    Returns:
        A scalar float in the range ``[0, 2]`` where 0 means identical
        direction and 2 means opposite direction.

    Raises:
        ValueError: If the flattened vectors have different lengths.
    """
    a_flat = a.flatten().astype(np.float64)
    b_flat = b.flatten().astype(np.float64)

    if a_flat.shape != b_flat.shape:
        raise ValueError(f"Vector length mismatch: {a_flat.shape[0]} vs {b_flat.shape[0]}")

    norm_a = np.linalg.norm(a_flat)
    norm_b = np.linalg.norm(b_flat)
    similarity = np.dot(a_flat, b_flat) / (norm_a * norm_b + COSINE_EPSILON)
    return float(1.0 - similarity)


def cosine_distance_matrix(
    embeddings: NDArray[np.floating],
) -> NDArray[np.floating]:
    """Compute the pairwise cosine-distance matrix for a set of embeddings.

    Uses scipy if available, otherwise falls back to a vectorised numpy
    implementation.

    Args:
        embeddings: 2-D array of shape ``(n, d)`` where each row is an
            embedding vector of dimensionality *d*.

    Returns:
        A symmetric ``(n, n)`` distance matrix where entry ``[i, j]``
        is the cosine distance between embeddings *i* and *j*.
    """
    try:
        from scipy.spatial.distance import pdist, squareform

        return squareform(pdist(embeddings, metric="cosine")).astype(np.float64)  # type: ignore[no-any-return]  # scipy stubs return Any
    except ImportError:
        # Vectorised numpy fallback
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalised = embeddings / (norms + COSINE_EPSILON)
        similarity_matrix = normalised @ normalised.T
        return (1.0 - similarity_matrix).astype(np.float64)  # type: ignore[no-any-return]  # ndarray.astype returns Any to mypy


def find_medoid_index(distance_matrix: NDArray[np.floating]) -> int:
    """Find the index of the medoid in a precomputed distance matrix.

    The medoid is the point that minimises the sum of distances to all
    other points — i.e. the most "central" or representative element.

    Args:
        distance_matrix: Symmetric ``(n, n)`` distance matrix.

    Returns:
        The integer index of the medoid row/column.
    """
    total_distances = np.sum(distance_matrix, axis=1)
    return int(np.argmin(total_distances))


def min_distance_to_references(
    target: NDArray[np.floating],
    reference_matrix: NDArray[np.floating],
) -> float:
    """Compute the minimum cosine distance from a target to a reference set.

    This is the **vectorised** replacement for a Python-level loop over
    individual ``cosine_distance`` calls.

    Args:
        target: 1-D embedding vector of shape ``(d,)``.
        reference_matrix: 2-D array of shape ``(k, d)`` containing *k*
            reference embeddings.

    Returns:
        The smallest cosine distance found.
    """
    target_flat = target.flatten().astype(np.float64)
    refs = reference_matrix.astype(np.float64)

    target_norm = np.linalg.norm(target_flat)
    ref_norms = np.linalg.norm(refs, axis=1)

    similarities = np.dot(refs, target_flat) / (ref_norms * target_norm + COSINE_EPSILON)
    distances = 1.0 - similarities
    return float(np.min(distances))
