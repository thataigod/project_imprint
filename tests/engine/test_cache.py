"""Tests for the SQLite embedding cache."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from imprint.engine.cache import EmbeddingCache
from tests.engine.helpers import write_image


def make_cache(tmp_path: Path, model: str = "buffalo_s") -> EmbeddingCache:
    return EmbeddingCache(tmp_path / "cache" / "embeddings.sqlite3", model)


def test_round_trip_creates_parent_and_preserves_values(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    write_image(image, 10)
    embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)

    cache = make_cache(tmp_path)
    try:
        assert cache.get(image) is None
        cache.put(image, 0.97, embedding)
        cached = cache.get(image)
        assert cached is not None
        assert cached.det_score == 0.97
        assert np.allclose(cached.embedding, embedding)
        assert cache.filepath.exists()
    finally:
        cache.close()


def test_missing_files_are_ignored(tmp_path: Path) -> None:
    missing = tmp_path / "missing.png"
    cache = make_cache(tmp_path)
    try:
        cache.put(missing, 0.9, np.array([1.0], dtype=np.float32))
        assert cache.get(missing) is None
    finally:
        cache.close()


def test_size_change_invalidates_entry(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    write_image(image, 10)
    cache = make_cache(tmp_path)
    try:
        cache.put(image, 0.9, np.array([1.0], dtype=np.float32))
        image.write_bytes(image.read_bytes() + b"extra")
        assert cache.get(image) is None
    finally:
        cache.close()


def test_mtime_change_invalidates_entry(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    write_image(image, 10)
    cache = make_cache(tmp_path)
    try:
        cache.put(image, 0.9, np.array([1.0], dtype=np.float32))
        stat = image.stat()
        os.utime(image, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
        assert cache.get(image) is None
    finally:
        cache.close()


def test_model_name_scopes_entries(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    write_image(image, 10)
    cache = make_cache(tmp_path, model="buffalo_s")
    try:
        cache.put(image, 0.9, np.array([1.0], dtype=np.float32))
    finally:
        cache.close()

    other = make_cache(tmp_path, model="antelopev2")
    try:
        assert other.get(image) is None
    finally:
        other.close()


def test_read_and_write_failures_are_suppressed(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    write_image(image, 10)
    cache = make_cache(tmp_path)
    cache.close()

    assert cache.get(image) is None
    cache.put(image, 0.9, np.array([1.0], dtype=np.float32))


def test_context_manager_closes_cache(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    write_image(image, 10)
    with make_cache(tmp_path) as cache:
        cache.put(image, 0.9, np.array([[1.0, 2.0]], dtype=np.float32))
        cached = cache.get(image)
        assert cached is not None
        assert cached.embedding.tolist() == [1.0, 2.0]
