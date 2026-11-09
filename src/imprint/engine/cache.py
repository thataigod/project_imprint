"""SQLite-backed embedding cache for fast repeat runs.

Entries are keyed by absolute path, modification time, size, and model
name.  A changed image or a different recognition model therefore never
returns a stale embedding.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS embeddings (
    path       TEXT    NOT NULL,
    mtime_ns   INTEGER NOT NULL,
    size       INTEGER NOT NULL,
    model      TEXT    NOT NULL,
    det_score  REAL    NOT NULL,
    embedding  BLOB    NOT NULL,
    PRIMARY KEY (path, mtime_ns, size, model)
)
"""


@dataclass(frozen=True)
class CachedFace:
    """Best detected face stored for one image."""

    det_score: float
    embedding: NDArray[np.float32]


class EmbeddingCache:
    """Persist the best face embedding per image in SQLite.

    Args:
        filepath: Database location.  Parent directories are created.
        model_name: Recognition-model key that scopes all entries.
    """

    def __init__(self, filepath: Path, model_name: str) -> None:
        self.filepath = filepath
        self.model_name = model_name
        if filepath.parent != Path("."):
            filepath.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(filepath))
        self._connection.execute(_SCHEMA)
        self._connection.commit()

    def get(self, image_path: Path) -> CachedFace | None:
        """Return the cached face for *image_path*, or ``None``."""
        try:
            stat = image_path.stat()
            row: tuple[Any, ...] | None = self._connection.execute(
                "SELECT det_score, embedding FROM embeddings "
                "WHERE path = ? AND mtime_ns = ? AND size = ? AND model = ?",
                (
                    str(image_path.resolve()),
                    stat.st_mtime_ns,
                    stat.st_size,
                    self.model_name,
                ),
            ).fetchone()
        except (OSError, sqlite3.Error) as exc:
            logger.warning("Embedding cache read failed for %s: %s", image_path, exc)
            return None

        if row is None:
            return None

        embedding = np.frombuffer(row[1], dtype=np.float32).copy()
        return CachedFace(det_score=float(row[0]), embedding=embedding)

    def put(
        self,
        image_path: Path,
        det_score: float,
        embedding: NDArray[np.floating],
    ) -> None:
        """Store or refresh the best face for *image_path*."""
        try:
            stat = image_path.stat()
            flat = np.asarray(embedding, dtype=np.float32).reshape(-1)
            self._connection.execute(
                "INSERT OR REPLACE INTO embeddings "
                "(path, mtime_ns, size, model, det_score, embedding) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(image_path.resolve()),
                    stat.st_mtime_ns,
                    stat.st_size,
                    self.model_name,
                    float(det_score),
                    flat.tobytes(),
                ),
            )
            self._connection.commit()
        except (OSError, sqlite3.Error) as exc:
            logger.warning("Embedding cache write failed for %s: %s", image_path, exc)

    def close(self) -> None:
        """Close the underlying database connection."""
        self._connection.close()

    def __enter__(self) -> EmbeddingCache:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
