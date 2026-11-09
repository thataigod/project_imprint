"""Shared fixtures and marker-based fake analysers for engine tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from imprint.domain.settings import AnalysisSettings, PathSettings

BASE = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
SIMILAR = np.array([1.0, 0.3, 0.0, 0.0], dtype=np.float32)
SIMILAR /= np.linalg.norm(SIMILAR)
OUTLIER = np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32)
DIFFERENT = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)


@dataclass
class FakeFace:
    """Minimal InsightFace-like face result."""

    det_score: float
    embedding: NDArray[np.float32]


class MarkerAnalyser:
    """Return faces based on the first pixel of the decoded image."""

    def __init__(
        self,
        mapping: dict[int, list[FakeFace]],
        fail_markers: set[int] | None = None,
    ) -> None:
        self.mapping = mapping
        self.fail_markers = fail_markers or set()
        self.prepared = False

    def prepare(self, ctx_id: int, det_size: tuple[int, int]) -> None:
        self.prepared = True

    def get(self, img: NDArray[Any]) -> list[FakeFace]:
        marker = int(img[0, 0, 0])
        if marker in self.fail_markers:
            raise RuntimeError(f"inference failed for marker {marker}")
        return list(self.mapping.get(marker, []))


def write_image(path: Path, marker: int) -> None:
    """Write a tiny PNG whose first pixel encodes *marker*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image = np.full((8, 8, 3), marker, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def reference_mapping() -> dict[int, list[FakeFace]]:
    return {
        1: [FakeFace(0.99, BASE)],
        2: [FakeFace(0.99, SIMILAR)],
        3: [FakeFace(0.99, OUTLIER)],
    }


def source_mapping() -> dict[int, list[FakeFace]]:
    return {
        10: [FakeFace(0.99, BASE)],
        11: [FakeFace(0.99, SIMILAR)],
        12: [FakeFace(0.99, DIFFERENT)],
        13: [FakeFace(0.20, BASE)],
        14: [],
        15: [FakeFace(0.99, BASE)],
        16: [FakeFace(0.99, BASE)],
    }


def make_engine_env(tmp_path: Path) -> tuple[PathSettings, AnalysisSettings]:
    """Create reference/source/destination folders and fixture images."""
    reference = tmp_path / "reference"
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    for folder in (reference, source, destination):
        folder.mkdir(parents=True)

    write_image(reference / "ref_base.png", 1)
    write_image(reference / "ref_similar.png", 2)
    write_image(reference / "ref_outlier.png", 3)

    write_image(source / "exact.png", 10)
    write_image(source / "near.png", 11)
    write_image(source / "no_match.png", 12)
    write_image(source / "low_conf.png", 13)
    write_image(source / "no_face.png", 14)
    (source / "corrupt.jpg").write_bytes(b"not an image")
    write_image(source / "a" / "duplicate.png", 15)
    write_image(source / "b" / "duplicate.png", 16)

    paths = PathSettings(
        reference_folder=str(reference),
        source_folder=str(source),
        destination_folder=str(destination),
    )
    analysis = AnalysisSettings(
        model_name="buffalo_s",
        distance_threshold=0.5,
        confidence_threshold=0.85,
        batch_size=2,
        number_of_subfolders=10,
    )
    return paths, analysis


def snapshot(root: Path) -> list[tuple[str, bytes]]:
    """Return relative paths and contents for every file under *root*."""
    return sorted(
        (path.relative_to(root).as_posix(), path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    )
