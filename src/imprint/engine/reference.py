"""Reference embedding extraction and medoid-based pruning.

This module reproduces the v5 algorithm exactly while allowing an
optional embedding cache and cooperative cancellation.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from imprint.domain.constants import MIN_REFERENCE_FACES
from imprint.domain.math import (
    cosine_distance,
    cosine_distance_matrix,
    find_medoid_index,
)
from imprint.engine.cache import EmbeddingCache
from imprint.engine.images import discover_reference_images
from imprint.engine.protocols import FaceAnalyser

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class ReferenceSet:
    """The pruned, consistent reference embeddings used for matching."""

    embeddings: tuple[NDArray[np.floating], ...]
    medoid_name: str
    kept_names: tuple[str, ...]


@dataclass(frozen=True)
class ReferenceBuildResult:
    """Outcome of building the reference set."""

    references: ReferenceSet | None = None
    error: str | None = None
    cancelled: bool = False


def extract_reference_embeddings(
    analyser: FaceAnalyser,
    ref_folder: Path,
    confidence: float,
    *,
    cache: EmbeddingCache | None = None,
    cancel_event: threading.Event | None = None,
    on_progress: ProgressCallback | None = None,
) -> tuple[list[NDArray[np.floating]], list[str]] | None:
    """Extract the best face embedding from each reference image.

    Returns:
        ``(embeddings, file_names)`` or ``None`` if cancelled.
    """
    all_embeddings: list[NDArray[np.floating]] = []
    file_names: list[str] = []
    ref_images = discover_reference_images(ref_folder)
    total = len(ref_images)

    for index, image_path in enumerate(ref_images):
        if cancel_event is not None and cancel_event.is_set():
            return None
        if on_progress is not None:
            on_progress(index + 1, total)

        try:
            cached = cache.get(image_path) if cache is not None else None
            if cached is not None:
                det_score = cached.det_score
                embedding = cached.embedding
                source = "cache"
            else:
                image = cv2.imread(str(image_path))
                if image is None:
                    logger.warning("Could not read reference image: %s", image_path.name)
                    continue

                faces = analyser.get(np.asarray(image))
                if not faces:
                    logger.warning("No face detected in: %s", image_path.name)
                    continue

                best_face = max(faces, key=lambda face: face.det_score)
                det_score = best_face.det_score
                embedding = best_face.embedding
                source = "model"
                if cache is not None:
                    cache.put(image_path, det_score, embedding)

            if det_score < confidence:
                logger.warning(
                    "SKIP REF: %s (confidence %.2f < %.2f)",
                    image_path.name,
                    det_score,
                    confidence,
                )
                continue

            all_embeddings.append(embedding)
            file_names.append(image_path.name)
            logger.debug("Reference %s accepted via %s", image_path.name, source)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error processing reference %s: %s", image_path.name, exc)

    return all_embeddings, file_names


def prune_to_core_set(
    all_embeddings: list[NDArray[np.floating]],
    file_names: list[str],
    threshold: float,
) -> ReferenceSet | None:
    """Reduce candidate embeddings to a consistent core group."""
    if not all_embeddings:
        return None

    embed_matrix = np.array(all_embeddings)
    dist_matrix = cosine_distance_matrix(embed_matrix)

    medoid_idx = find_medoid_index(dist_matrix)
    medoid_embedding = all_embeddings[medoid_idx]
    logger.info("  Medoid (most representative): %s", file_names[medoid_idx])

    core: list[NDArray[np.floating]] = [medoid_embedding]
    kept_names: list[str] = [file_names[medoid_idx]]
    logger.info("Building core set (consistency < %.4f)...", threshold)
    logger.info("  Keeping: %s (medoid)", file_names[medoid_idx])

    for index, embedding in enumerate(all_embeddings):
        if index == medoid_idx:
            continue
        distance = cosine_distance(embedding, medoid_embedding)
        if distance < threshold:
            core.append(embedding)
            kept_names.append(file_names[index])
            logger.info("  Keeping: %s (dist=%.4f)", file_names[index], distance)
        else:
            logger.warning("  Discarding outlier: %s (dist=%.4f)", file_names[index], distance)

    return ReferenceSet(
        embeddings=tuple(core),
        medoid_name=file_names[medoid_idx],
        kept_names=tuple(kept_names),
    )


def build_core_references(
    analyser: FaceAnalyser,
    ref_folder: Path,
    threshold: float,
    confidence: float,
    *,
    cache: EmbeddingCache | None = None,
    cancel_event: threading.Event | None = None,
    on_progress: ProgressCallback | None = None,
) -> ReferenceBuildResult:
    """Extract reference faces and prune them to a consistent core set."""
    extracted = extract_reference_embeddings(
        analyser,
        ref_folder,
        confidence,
        cache=cache,
        cancel_event=cancel_event,
        on_progress=on_progress,
    )
    if extracted is None:
        return ReferenceBuildResult(cancelled=True)

    all_embeddings, file_names = extracted
    if len(all_embeddings) < MIN_REFERENCE_FACES:
        return ReferenceBuildResult(
            error=(
                f"Found only {len(all_embeddings)} reference face(s) passing the "
                f"confidence threshold ({confidence}).  Need at least "
                f"{MIN_REFERENCE_FACES}.\n\n"
                f"Try lowering the 'Face Confidence' value or provide clearer images."
            )
        )

    logger.info(
        "Found %d candidates. Computing consistency matrix...",
        len(all_embeddings),
    )
    core = prune_to_core_set(all_embeddings, file_names, threshold)
    if core is None:  # pragma: no cover - unreachable with a non-empty candidate list
        return ReferenceBuildResult(error="Could not form a consistent core reference group.")

    logger.info("Core reference set built with %d embedding(s).", len(core.embeddings))
    return ReferenceBuildResult(references=core)


__all__ = [
    "ReferenceBuildResult",
    "ReferenceSet",
    "build_core_references",
    "extract_reference_embeddings",
    "prune_to_core_set",
]
