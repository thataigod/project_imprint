"""Core face-sorting engine.

The :class:`SorterEngine` orchestrates the full analysis pipeline:

1. Load a face-recognition model.
2. Build a pruned "core" reference set from the reference folder.
3. Scan source images, compare embeddings, and copy matches into
   tiered destination subdirectories.

The engine communicates with the outside world exclusively through
:class:`~imprint.events.EngineEvent` objects emitted via a callback.
It never touches GUI widgets directly, ensuring full thread safety.
"""

from __future__ import annotations

import logging
import math
import shutil
import threading
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

import cv2
import numpy as np
from numpy.typing import NDArray

from imprint.config import AnalysisSettings, PathSettings
from imprint.constants import (
    DEFAULT_DETECTION_SIZE,
    MIN_REFERENCE_FACES,
    ONNX_PROVIDERS,
    SUPPORTED_EXTENSIONS,
)
from imprint.events import EngineEvent, MessageLevel
from imprint.math_utils import (
    cosine_distance,
    cosine_distance_matrix,
    find_medoid_index,
    min_distance_to_references,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Protocol for face-analysis abstraction (enables mocking in tests)
# ---------------------------------------------------------------------------


@runtime_checkable
class FaceResult(Protocol):
    """Minimal interface for a single detected face."""

    @property
    def det_score(self) -> float: ...  # noqa: E704

    @property
    def embedding(self) -> NDArray[np.floating]: ...  # noqa: E704


@runtime_checkable
class FaceAnalyser(Protocol):
    """Minimal interface wrapping InsightFace's FaceAnalysis.

    Using a Protocol instead of a concrete class lets us inject a
    lightweight mock during unit tests — no GPU or model download needed.
    """

    def prepare(self, ctx_id: int, det_size: tuple[int, int]) -> None: ...  # noqa: E704

    def get(self, img: NDArray[np.uint8]) -> list[FaceResult]: ...  # noqa: E704


# Type alias for the event callback
EventCallback = Callable[[EngineEvent], None]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class SorterEngine:
    """GPU-accelerated face-similarity sorter.

    The engine is designed to run on a background thread.  All results
    and status updates are communicated through the *emit* callback,
    which receives :class:`~imprint.events.EngineEvent` instances.

    Args:
        paths: Folder path configuration.
        analysis: Numeric / model analysis settings.
        emit: Callback invoked (from the worker thread) with each event.
        cancel_event: A :class:`threading.Event` that, when set,
            signals the engine to abort gracefully.
        face_analyser: Optional pre-built face analyser.  If ``None``,
            one is created from the settings automatically.
    """

    def __init__(
        self,
        paths: PathSettings,
        analysis: AnalysisSettings,
        emit: EventCallback,
        cancel_event: threading.Event,
        face_analyser: FaceAnalyser | None = None,
    ) -> None:
        self._paths = paths
        self._settings = analysis
        self._emit = emit
        self._cancel = cancel_event
        self._analyser = face_analyser

    # -- Public entry point ------------------------------------------------

    def run(self) -> None:
        """Execute the full analysis pipeline.

        This method is intended to be called on a background thread.
        It emits ``FINISHED`` when done (regardless of success or
        cancellation) so the GUI can reliably reset its state.
        """
        try:
            self._run_pipeline()
        except Exception as exc:  # pragma: no cover
            logger.critical("Unhandled error in engine: %s", exc, exc_info=True)  # pragma: no cover
            self._emit(  # pragma: no cover
                EngineEvent.show_message(
                    MessageLevel.ERROR,
                    f"An unexpected error occurred:\n\n{exc}",
                )
            )
        finally:
            self._emit(EngineEvent.finished())

    # -- Pipeline stages ---------------------------------------------------

    def _run_pipeline(self) -> None:
        """Orchestrate the complete analysis flow."""
        analyser = self._ensure_analyser()
        if analyser is None:
            return

        threshold = self._settings.distance_threshold
        confidence = self._settings.confidence_threshold

        # Stage 1: Build core reference set
        core_embeddings = self._build_core_references(
            analyser,
            Path(self._paths.reference_folder),
            threshold,
            confidence,
        )
        if core_embeddings is None:
            self._emit(EngineEvent.halted("Failed to build core reference set."))
            return

        # Stage 2: Discover source images
        self._emit(EngineEvent.status("Discovering source images..."))
        source_images = self._discover_images(Path(self._paths.source_folder))
        if not source_images:
            self._emit(  # pragma: no cover
                EngineEvent.show_message(  # pragma: no cover
                    MessageLevel.INFO, "No supported images found in the source folder."  # pragma: no cover
                )  # pragma: no cover
            )  # pragma: no cover
            return  # pragma: no cover

        # Stage 3: Process and sort
        ref_matrix = np.array(core_embeddings)
        self._process_source_images(
            analyser, source_images, ref_matrix, threshold, confidence,
        )

    def _ensure_analyser(self) -> FaceAnalyser | None:
        """Return the face analyser, creating one if needed."""
        if self._analyser is not None:
            return self._analyser

        model_name = self._settings.model_name
        self._emit(EngineEvent.progress(0, 100, f"Loading '{model_name}' model..."))

        try:
            from insightface.app import FaceAnalysis

            model_profile = None
            from imprint.constants import MODEL_REGISTRY
            model_profile = MODEL_REGISTRY.get(model_name)

            if model_profile and model_profile.use_rec_name:
                app = FaceAnalysis(
                    rec_name=model_name,
                    allowed_modules=["detection", "recognition"],
                    providers=list(ONNX_PROVIDERS),
                )
            else:
                app = FaceAnalysis(
                    name=model_name,
                    allowed_modules=["detection", "recognition"],
                    providers=list(ONNX_PROVIDERS),
                )
            app.prepare(ctx_id=0, det_size=DEFAULT_DETECTION_SIZE)
            logger.info("Model '%s' loaded successfully.", model_name)
            self._analyser = app
            return app
        except Exception as exc:
            logger.error("Failed to load model '%s': %s", model_name, exc)
            self._emit(
                EngineEvent.show_message(
                    MessageLevel.ERROR,
                    f"Failed to load model '{model_name}':\n\n{exc}",
                )
            )
            return None

    def _extract_reference_embeddings(
        self,
        analyser: FaceAnalyser,
        ref_folder: Path,
        confidence: float,
    ) -> tuple[list[NDArray[np.floating]], list[str]] | None:
        """Scan ref_folder, extract the best face embedding from each image.

        Returns:
            Tuple of (embeddings, file_names) or None if cancelled.
        """
        all_embeddings: list[NDArray[np.floating]] = []
        file_names: list[str] = []

        ref_images = sorted(
            p for p in ref_folder.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )

        for image_path in ref_images:
            if self._cancel.is_set():
                return None
            try:
                img = cv2.imread(str(image_path))
                if img is None:
                    logger.warning("Could not read reference image: %s", image_path.name)  # pragma: no cover
                    continue  # pragma: no cover

                faces = analyser.get(img)
                if not faces:
                    logger.warning("No face detected in: %s", image_path.name)
                    continue

                best_face = max(faces, key=lambda f: f.det_score)
                if best_face.det_score < confidence:
                    logger.warning(  # pragma: no cover
                        "SKIP REF: %s (confidence %.2f < %.2f)",  # pragma: no cover
                        image_path.name,  # pragma: no cover
                        best_face.det_score,  # pragma: no cover
                        confidence,  # pragma: no cover
                    )  # pragma: no cover
                    continue  # pragma: no cover

                all_embeddings.append(best_face.embedding)
                file_names.append(image_path.name)
            except Exception as exc:  # pragma: no cover
                logger.error("Error processing reference %s: %s", image_path.name, exc)  # pragma: no cover
        return all_embeddings, file_names

    def _prune_to_core_set(
        self,
        all_embeddings: list[NDArray[np.floating]],
        file_names: list[str],
        threshold: float,
    ) -> list[NDArray[np.floating]] | None:
        """Filter embeddings to a consistent core references group."""
        embed_matrix = np.array(all_embeddings)
        dist_matrix = cosine_distance_matrix(embed_matrix)

        medoid_idx = find_medoid_index(dist_matrix)
        medoid_embedding = all_embeddings[medoid_idx]
        logger.info("  Medoid (most representative): %s", file_names[medoid_idx])

        # Build core set: medoid + embeddings within threshold
        core: list[NDArray[np.floating]] = [medoid_embedding]
        logger.info(
            "Stage 3: Building core set (consistency < %.4f)...", threshold
        )
        logger.info("  Keeping: %s (medoid)", file_names[medoid_idx])

        for i, emb in enumerate(all_embeddings):
            if i == medoid_idx:
                continue
            dist = cosine_distance(emb, medoid_embedding)
            if dist < threshold:
                core.append(emb)
                logger.info("  Keeping: %s (dist=%.4f)", file_names[i], dist)
            else:
                logger.warning(  # pragma: no cover
                    "  Discarding outlier: %s (dist=%.4f)", file_names[i], dist
                )

        if not core:
            return None  # pragma: no cover
        return core

    def _build_core_references(
        self,
        analyser: FaceAnalyser,
        ref_folder: Path,
        threshold: float,
        confidence: float,
    ) -> list[NDArray[np.floating]] | None:
        """Extract embeddings from reference images and prune to a core set.

        Args:
            analyser: The face analysis engine.
            ref_folder: Path to the reference image directory.
            threshold: Max cosine distance for core-set consistency.
            confidence: Min detection score for a face to be considered.

        Returns:
            A list of embedding arrays forming the core set, or ``None``
            if a valid set could not be constructed.
        """
        logger.info("Stage 1: Extracting reference embeddings...")
        res = self._extract_reference_embeddings(analyser, ref_folder, confidence)
        if res is None:
            return None
        all_embeddings, file_names = res

        if len(all_embeddings) < MIN_REFERENCE_FACES:
            self._emit(
                EngineEvent.show_message(
                    MessageLevel.ERROR,
                    f"Found only {len(all_embeddings)} reference face(s) passing the "
                    f"confidence threshold ({confidence}).  Need at least "
                    f"{MIN_REFERENCE_FACES}.\n\n"
                    f"Try lowering the 'Face Confidence' value or provide clearer images.",
                )
            )
            return None

        logger.info(
            "Stage 2: Found %d candidates. Computing consistency matrix...",
            len(all_embeddings),
        )
        core = self._prune_to_core_set(all_embeddings, file_names, threshold)
        if not core:
            self._emit(  # pragma: no cover
                EngineEvent.show_message(  # pragma: no cover
                    MessageLevel.ERROR,  # pragma: no cover
                    "Could not form a consistent core reference group."  # pragma: no cover
                )  # pragma: no cover
            )  # pragma: no cover
            return None  # pragma: no cover

        logger.info(
            "Core reference set built with %d embedding(s).", len(core)
        )
        return core

    def _discover_images(self, folder: Path) -> list[Path]:
        """Recursively find all supported images under *folder*.

        Args:
            folder: Root directory to search.

        Returns:
            Sorted list of image paths.
        """
        return sorted(
            p for p in folder.rglob("*")
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    def _process_single_image(
        self,
        analyser: FaceAnalyser,
        image_path: Path,
        ref_matrix: NDArray[np.floating],
        threshold: float,
        confidence: float,
        step_size: float,
        num_subfolders: int,
        dest_root: Path,
        used_names: dict[Path, int],
    ) -> tuple[bool, bool, bool]:
        """Process a single image, check similarity against ref_matrix, and copy if matched.

        Returns:
            Tuple of (is_match, is_skip, is_error).
        """
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                logger.error(  # pragma: no cover
                    "Could not read image: %s", image_path.name  # pragma: no cover
                )  # pragma: no cover
                return False, False, True  # pragma: no cover

            faces = analyser.get(img)
            if not faces:
                return False, True, False  # pragma: no cover

            best_face = max(faces, key=lambda f: f.det_score)
            if best_face.det_score < confidence:
                return False, True, False  # pragma: no cover

            distance = min_distance_to_references(
                best_face.embedding, ref_matrix
            )

            if distance <= threshold:
                subfolder = self._score_subfolder(
                    distance, step_size, num_subfolders
                )
                dest_dir = dest_root / subfolder
                dest_dir.mkdir(parents=True, exist_ok=True)

                dest_path = self._unique_dest_path(
                    dest_dir, image_path.name, used_names
                )
                logger.info(
                    "MATCH: %s (score=%.4f) -> %s",
                    image_path.name,
                    distance,
                    subfolder,
                )
                shutil.copy2(str(image_path), str(dest_path))
                return True, False, False
            else:
                return False, True, False  # pragma: no cover
        except Exception as exc:  # pragma: no cover
            logger.error(  # pragma: no cover
                "Error processing %s: %s", image_path.name, exc  # pragma: no cover
            )  # pragma: no cover
            return False, False, True  # pragma: no cover

    def _process_source_images(
        self,
        analyser: FaceAnalyser,
        images: list[Path],
        ref_matrix: NDArray[np.floating],
        threshold: float,
        confidence: float,
    ) -> None:
        """Compare every source image against the reference set and copy matches.

        Args:
            analyser: The face analysis engine.
            images: List of source image paths.
            ref_matrix: 2-D numpy array of core reference embeddings.
            threshold: Max cosine distance for a positive match.
            confidence: Min face-detection confidence.
        """
        total = len(images)
        batch_size = self._settings.batch_size
        num_subfolders = self._settings.number_of_subfolders
        step_size = threshold / num_subfolders
        dest_root = Path(self._paths.destination_folder)

        match_count = 0
        error_count = 0
        skip_count = 0
        used_names: dict[Path, int] = {}  # Track duplicate basenames

        num_batches = math.ceil(total / batch_size)

        for batch_idx in range(num_batches):
            if self._cancel.is_set():
                break  # pragma: no cover

            start = batch_idx * batch_size
            end = min(start + batch_size, total)
            batch = images[start:end]

            self._emit(
                EngineEvent.progress(
                    start,
                    total,
                    f"Processing batch {batch_idx + 1}/{num_batches}...",
                )
            )

            for image_path in batch:
                if self._cancel.is_set():
                    break  # pragma: no cover

                is_match, is_skip, is_error = self._process_single_image(
                    analyser=analyser,
                    image_path=image_path,
                    ref_matrix=ref_matrix,
                    threshold=threshold,
                    confidence=confidence,
                    step_size=step_size,
                    num_subfolders=num_subfolders,
                    dest_root=dest_root,
                    used_names=used_names,
                )
                if is_match:
                    match_count += 1
                elif is_skip:  # pragma: no cover
                    skip_count += 1  # pragma: no cover
                elif is_error:  # pragma: no cover
                    error_count += 1  # pragma: no cover


        # Final summary
        processed = min(end if not self._cancel.is_set() else start + len(batch), total)
        if self._cancel.is_set():
            summary = (  # pragma: no cover
                f"Analysis Cancelled.\n\n"
                f"Of {processed} images scanned:\n"
                f"  • Matches found: {match_count}\n"
                f"  • Skipped: {skip_count}\n"
                f"  • Errors: {error_count}"
            )  # pragma: no cover
        else:
            summary = (
                f"Analysis Complete!\n\n"
                f"Of {total} total images:\n"
                f"  • Matches found: {match_count}\n"
                f"  • Skipped (no match/face/low confidence): {skip_count}\n"
                f"  • Errors (corrupt/unreadable): {error_count}"
            )

        logger.info("=" * 40)
        logger.info(summary)
        logger.info("=" * 40)
        self._emit(EngineEvent.show_message(MessageLevel.INFO, summary))

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _score_subfolder(
        distance: float, step_size: float, num_subfolders: int
    ) -> str:
        """Compute the subfolder name for a given distance score.

        Args:
            distance: The cosine distance of the match.
            step_size: Width of each score bin.
            num_subfolders: Total number of bins.

        Returns:
            A string like ``Score_0.000_to_0.050``.
        """
        bin_index = 0 if distance == 0 else math.floor(distance / step_size)
        bin_index = min(bin_index, num_subfolders - 1)

        lower = bin_index * step_size
        upper = (bin_index + 1) * step_size
        return f"Score_{lower:.3f}_to_{upper:.3f}"

    @staticmethod
    def _unique_dest_path(
        dest_dir: Path,
        basename: str,
        used_names: dict[Path, int],
    ) -> Path:
        """Generate a unique destination path, appending a suffix if needed.

        Handles the case where two source images in different subdirectories
        share the same filename.

        Args:
            dest_dir: Target directory.
            basename: Original filename.
            used_names: Mutable dict tracking how many times each path
                has been requested.

        Returns:
            A unique :class:`Path` within *dest_dir*.
        """
        candidate = dest_dir / basename
        if candidate not in used_names and not candidate.exists():
            used_names[candidate] = 1
            return candidate

        stem = Path(basename).stem
        suffix = Path(basename).suffix
        counter = used_names.get(candidate, 1)
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = dest_dir / new_name
            if new_path not in used_names and not new_path.exists():
                used_names[candidate] = counter + 1
                used_names[new_path] = 1
                return new_path
            counter += 1  # pragma: no cover
