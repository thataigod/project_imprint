"""Unit tests for imprint.math_utils.

Covers cosine distance, distance matrices, medoid finding,
and vectorized minimum distance computation.
"""

from __future__ import annotations

import unittest.mock

import numpy as np
import pytest
from numpy.typing import NDArray

from imprint.math_utils import (
    cosine_distance,
    cosine_distance_matrix,
    find_medoid_index,
    min_distance_to_references,
)


class TestCosineDistance:
    """Tests for cosine_distance()."""

    def test_identical_vectors_return_zero(self) -> None:
        """Identical vectors should have distance ≈ 0."""
        vec = np.array([1.0, 2.0, 3.0])
        assert cosine_distance(vec, vec) == pytest.approx(0.0, abs=1e-6)

    def test_orthogonal_vectors_return_one(self) -> None:
        """Orthogonal vectors should have distance ≈ 1."""
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert cosine_distance(a, b) == pytest.approx(1.0, abs=1e-6)

    def test_opposite_vectors_return_two(self) -> None:
        """Opposite vectors should have distance ≈ 2."""
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        assert cosine_distance(a, b) == pytest.approx(2.0, abs=1e-6)

    def test_similar_vectors_have_small_distance(
        self,
        sample_embedding: NDArray[np.floating],
        similar_embedding: NDArray[np.floating],
    ) -> None:
        """Slightly perturbed vectors should have small distance."""
        dist = cosine_distance(sample_embedding, similar_embedding)
        assert 0.0 < dist < 0.1

    def test_different_vectors_have_large_distance(
        self,
        sample_embedding: NDArray[np.floating],
        different_embedding: NDArray[np.floating],
    ) -> None:
        """Very different vectors should have a larger distance."""
        dist = cosine_distance(sample_embedding, different_embedding)
        assert dist > 0.1

    def test_mismatched_lengths_raise_value_error(self) -> None:
        """Vectors of different lengths should raise ValueError."""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0])
        with pytest.raises(ValueError, match="Vector length mismatch"):
            cosine_distance(a, b)

    def test_2d_input_is_flattened(self) -> None:
        """2-D inputs should be flattened before comparison."""
        a = np.array([[1.0, 2.0, 3.0]])
        b = np.array([1.0, 2.0, 3.0])
        assert cosine_distance(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_zero_vector_does_not_crash(self) -> None:
        """A zero vector should not raise (epsilon prevents div-by-zero)."""
        a = np.array([0.0, 0.0, 0.0])
        b = np.array([1.0, 2.0, 3.0])
        result = cosine_distance(a, b)
        assert isinstance(result, float)

    def test_returns_python_float(self) -> None:
        """The return type should be a native Python float."""
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        result = cosine_distance(a, b)
        assert type(result) is float


class TestCosineDistanceMatrix:
    """Tests for cosine_distance_matrix()."""

    def test_diagonal_is_zero(self) -> None:
        """Diagonal entries (self-distance) should be ≈ 0."""
        embeddings = np.random.default_rng(42).standard_normal((5, 128))
        matrix = cosine_distance_matrix(embeddings)
        np.testing.assert_allclose(np.diag(matrix), 0.0, atol=1e-6)

    def test_symmetry(self) -> None:
        """The distance matrix should be symmetric."""
        embeddings = np.random.default_rng(42).standard_normal((5, 128))
        matrix = cosine_distance_matrix(embeddings)
        np.testing.assert_allclose(matrix, matrix.T, atol=1e-10)

    def test_shape(self) -> None:
        """Output shape should be (n, n)."""
        n = 7
        embeddings = np.random.default_rng(42).standard_normal((n, 64))
        matrix = cosine_distance_matrix(embeddings)
        assert matrix.shape == (n, n)

    def test_non_negative(self) -> None:
        """All distances should be non-negative."""
        embeddings = np.random.default_rng(42).standard_normal((5, 128))
        matrix = cosine_distance_matrix(embeddings)
        assert np.all(matrix >= -1e-10)

    def test_single_embedding(self) -> None:
        """A single embedding should yield a 1x1 zero matrix."""
        embeddings = np.array([[1.0, 2.0, 3.0]])
        matrix = cosine_distance_matrix(embeddings)
        assert matrix.shape == (1, 1)
        assert matrix[0, 0] == pytest.approx(0.0, abs=1e-6)

    def test_fallback_without_scipy(self) -> None:
        """Verify the pure-NumPy fallback works when scipy is unavailable."""
        a = np.array([[1, 0], [0, 1]])

        # We mock __import__ to raise ImportError specifically for scipy
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if "scipy" in name:
                raise ImportError("Mocked missing scipy")
            return original_import(name, *args, **kwargs)

        with unittest.mock.patch("builtins.__import__", side_effect=mock_import):
            matrix = cosine_distance_matrix(a)

        assert matrix.shape == (2, 2)
        assert matrix[0, 0] == pytest.approx(0.0, abs=1e-5)
        assert matrix[1, 1] == pytest.approx(0.0, abs=1e-5)
        assert matrix[0, 1] > 0.5
        assert matrix[1, 0] > 0.5


class TestFindMedoidIndex:
    """Tests for find_medoid_index()."""

    def test_known_medoid(self) -> None:
        """The medoid should be the point closest to all others."""
        # Create a cluster where index 1 is clearly central
        dist_matrix = np.array([
            [0.0, 0.1, 0.9],
            [0.1, 0.0, 0.8],
            [0.9, 0.8, 0.0],
        ])
        assert find_medoid_index(dist_matrix) == 1

    def test_single_point(self) -> None:
        """A single point is always the medoid."""
        dist_matrix = np.array([[0.0]])
        assert find_medoid_index(dist_matrix) == 0

    def test_returns_int(self) -> None:
        """Return type should be a native Python int."""
        dist_matrix = np.array([[0.0, 0.5], [0.5, 0.0]])
        result = find_medoid_index(dist_matrix)
        assert type(result) is int


class TestMinDistanceToReferences:
    """Tests for min_distance_to_references()."""

    def test_exact_match_returns_zero(
        self, sample_embedding: NDArray[np.floating]
    ) -> None:
        """An exact match in the reference set should return ≈ 0."""
        ref_matrix = np.stack([sample_embedding, sample_embedding * 0.5])
        dist = min_distance_to_references(sample_embedding, ref_matrix)
        assert dist == pytest.approx(0.0, abs=1e-6)

    def test_closest_reference_is_selected(
        self,
        sample_embedding: NDArray[np.floating],
        similar_embedding: NDArray[np.floating],
        different_embedding: NDArray[np.floating],
    ) -> None:
        """Should return the distance to the closest reference."""
        ref_matrix = np.stack([similar_embedding, different_embedding])
        dist = min_distance_to_references(sample_embedding, ref_matrix)
        expected = cosine_distance(sample_embedding, similar_embedding)
        assert dist == pytest.approx(expected, abs=1e-6)

    def test_single_reference(
        self, sample_embedding: NDArray[np.floating]
    ) -> None:
        """Works with a single reference embedding."""
        other = np.ones_like(sample_embedding)
        other /= np.linalg.norm(other)
        ref_matrix = np.stack([other])
        dist = min_distance_to_references(sample_embedding, ref_matrix)
        expected = cosine_distance(sample_embedding, other)
        assert dist == pytest.approx(expected, abs=1e-6)

    def test_returns_python_float(
        self, sample_embedding: NDArray[np.floating]
    ) -> None:
        """Return type should be a native Python float."""
        ref_matrix = np.stack([sample_embedding])
        result = min_distance_to_references(sample_embedding, ref_matrix)
        assert type(result) is float
