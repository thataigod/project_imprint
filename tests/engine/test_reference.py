"""Tests for reference extraction and medoid pruning."""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

from imprint.engine.cache import EmbeddingCache
from imprint.engine.reference import (
    build_core_references,
    extract_reference_embeddings,
    prune_to_core_set,
)
from tests.engine.helpers import (
    BASE,
    OUTLIER,
    SIMILAR,
    FakeFace,
    MarkerAnalyser,
    reference_mapping,
    write_image,
)


def make_reference_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "reference"
    folder.mkdir()
    write_image(folder / "ref_base.png", 1)
    write_image(folder / "ref_similar.png", 2)
    write_image(folder / "ref_low.png", 3)
    write_image(folder / "ref_no_face.png", 4)
    (folder / "corrupt.jpg").write_bytes(b"not an image")
    return folder


class TestExtractReferenceEmbeddings:
    def test_filters_low_confidence_and_unreadable(self, tmp_path: Path) -> None:
        folder = make_reference_folder(tmp_path)
        mapping = reference_mapping()
        mapping[3] = [FakeFace(0.20, BASE)]
        progress: list[tuple[int, int]] = []

        result = extract_reference_embeddings(
            MarkerAnalyser(mapping),
            folder,
            confidence=0.85,
            on_progress=lambda current, total: progress.append((current, total)),
        )

        assert result is not None
        embeddings, names = result
        assert names == ["ref_base.png", "ref_similar.png"]
        assert len(embeddings) == 2
        assert progress == [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)]

    def test_cancellation_returns_none(self, tmp_path: Path) -> None:
        folder = make_reference_folder(tmp_path)
        cancel = threading.Event()
        cancel.set()

        result = extract_reference_embeddings(
            MarkerAnalyser(reference_mapping()),
            folder,
            confidence=0.85,
            cancel_event=cancel,
        )
        assert result is None

    def test_cache_is_used_on_repeat_runs(self, tmp_path: Path) -> None:
        folder = make_reference_folder(tmp_path)
        mapping = reference_mapping()
        mapping[3] = [FakeFace(0.20, OUTLIER)]
        cache = EmbeddingCache(tmp_path / "cache.sqlite3", "buffalo_s")
        try:
            first = extract_reference_embeddings(
                MarkerAnalyser(mapping),
                folder,
                confidence=0.85,
                cache=cache,
            )
            assert first is not None
            assert first[1] == ["ref_base.png", "ref_similar.png"]

            second = extract_reference_embeddings(
                MarkerAnalyser({}),
                folder,
                confidence=0.85,
                cache=cache,
            )
            assert second is not None
            assert second[1] == ["ref_base.png", "ref_similar.png"]
        finally:
            cache.close()


class TestPruneToCoreSet:
    def test_discards_outlier_relative_to_medoid(self, tmp_path: Path) -> None:
        names = ["base.png", "similar.png", "outlier.png"]
        result = prune_to_core_set(
            [BASE, SIMILAR, OUTLIER],
            names,
            threshold=0.5,
        )

        assert result is not None
        assert result.medoid_name == "base.png"
        assert result.kept_names == ("base.png", "similar.png")
        assert len(result.embeddings) == 2

    def test_empty_input_returns_none(self) -> None:
        assert prune_to_core_set([], [], 0.5) is None

    def test_single_embedding_is_its_own_core(self) -> None:
        result = prune_to_core_set([BASE], ["only.png"], 0.5)
        assert result is not None
        assert result.kept_names == ("only.png",)
        assert np.allclose(result.embeddings[0], BASE)


class TestBuildCoreReferences:
    def test_success(self, tmp_path: Path) -> None:
        folder = make_reference_folder(tmp_path)
        result = build_core_references(
            MarkerAnalyser(reference_mapping()),
            folder,
            threshold=0.5,
            confidence=0.85,
        )
        assert result.references is not None
        assert result.references.kept_names == ("ref_base.png", "ref_similar.png")
        assert result.error is None
        assert result.cancelled is False

    def test_insufficient_references_reports_error(self, tmp_path: Path) -> None:
        folder = tmp_path / "reference"
        folder.mkdir()
        write_image(folder / "only.png", 1)

        result = build_core_references(
            MarkerAnalyser(reference_mapping()),
            folder,
            threshold=0.5,
            confidence=0.85,
        )
        assert result.references is None
        assert result.error is not None
        assert "Found only 1 reference face(s)" in result.error

    def test_cancellation_is_reported(self, tmp_path: Path) -> None:
        folder = make_reference_folder(tmp_path)
        cancel = threading.Event()
        cancel.set()

        result = build_core_references(
            MarkerAnalyser(reference_mapping()),
            folder,
            threshold=0.5,
            confidence=0.85,
            cancel_event=cancel,
        )
        assert result.cancelled is True
        assert result.references is None
