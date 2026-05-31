"""Shared test fixtures for the Imprint test suite.

Provides reusable fixtures for temporary directories, mock embeddings,
mock face analysers, and settings objects.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import numpy as np
import pytest
from numpy.typing import NDArray

from imprint.config import AnalysisSettings, AppSettings, PathSettings


@dataclass
class MockFace:
    """Lightweight mock of a detected face result.

    Attributes:
        det_score: Detection confidence.
        embedding: Face embedding vector.
    """

    det_score: float
    embedding: NDArray[np.floating]


class MockFaceAnalyser:
    """Mock face analyser that returns pre-configured faces.

    This replaces the real InsightFace FaceAnalysis for unit testing
    without GPU or model downloads.

    Args:
        faces_per_image: List of face lists to return sequentially.
            Each call to ``get()`` pops the next item.
    """

    def __init__(self, faces_per_image: list[list[MockFace]] | None = None) -> None:
        """Initialise with a sequence of face results.

        Args:
            faces_per_image: Pre-configured face results.
        """
        self._faces = list(faces_per_image or [])
        self._call_count = 0
        self.prepared = False

    def prepare(self, ctx_id: int, det_size: tuple[int, int]) -> None:
        """Mock prepare — just records that it was called."""
        self.prepared = True

    def get(self, img: NDArray[np.uint8]) -> list[MockFace]:
        """Return the next pre-configured face list.

        Args:
            img: Ignored in mock.

        Returns:
            The next set of faces, or empty list if exhausted.
        """
        if self._call_count < len(self._faces):
            result = self._faces[self._call_count]
            self._call_count += 1
            return result
        return []


@pytest.fixture
def sample_embedding() -> NDArray[np.floating]:
    """Return a deterministic 512-dimensional embedding vector."""
    rng = np.random.default_rng(42)
    vec = rng.standard_normal(512).astype(np.float32)
    return vec / np.linalg.norm(vec)


@pytest.fixture
def similar_embedding(sample_embedding: NDArray[np.floating]) -> NDArray[np.floating]:
    """Return an embedding slightly perturbed from sample_embedding."""
    rng = np.random.default_rng(123)
    noise = rng.standard_normal(512).astype(np.float32) * 0.01
    vec = sample_embedding + noise
    return vec / np.linalg.norm(vec)


@pytest.fixture
def different_embedding() -> NDArray[np.floating]:
    """Return an embedding very different from sample_embedding."""
    rng = np.random.default_rng(999)
    vec = rng.standard_normal(512).astype(np.float32)
    return vec / np.linalg.norm(vec)


@pytest.fixture
def tmp_folders(tmp_path: Path) -> dict[str, Path]:
    """Create reference, source, and destination directories.

    Returns:
        Dict with keys 'reference', 'source', 'destination'.
    """
    folders = {
        "reference": tmp_path / "reference",
        "source": tmp_path / "source",
        "destination": tmp_path / "destination",
    }
    for folder in folders.values():
        folder.mkdir()
    return folders


@pytest.fixture
def default_path_settings(tmp_folders: dict[str, Path]) -> PathSettings:
    """Return PathSettings pointing to temp directories."""
    return PathSettings(
        reference_folder=str(tmp_folders["reference"]),
        source_folder=str(tmp_folders["source"]),
        destination_folder=str(tmp_folders["destination"]),
    )


@pytest.fixture
def default_analysis_settings() -> AnalysisSettings:
    """Return default analysis settings suitable for testing."""
    return AnalysisSettings(
        model_name="antelopev2",
        distance_threshold=0.5,
        confidence_threshold=0.5,
        batch_size=4,
        number_of_subfolders=5,
    )


@pytest.fixture
def cancel_event() -> threading.Event:
    """Return a fresh threading.Event for cancellation."""
    return threading.Event()
