"""The v6 analysis pipeline.

Results are identical to v5: the best face per image is compared
against a medoid-pruned reference set using cosine distance, and matches
are copied into score-tiered subfolders with duplicate-safe names.

On top of the v5 flow this pipeline overlaps image decoding with GPU
inference, supports an optional embedding cache, pause/resume, and emits
rich events for the QML UI.
"""

from __future__ import annotations

import logging
import math
import shutil
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
from numpy.typing import NDArray

from imprint.domain.constants import (
    DEFAULT_DETECTION_SIZE,
    MODEL_REGISTRY,
    ONNX_PROVIDERS,
)
from imprint.domain.math import min_distance_to_references
from imprint.domain.results import ImageStatus, MatchRecord, RunSummary
from imprint.domain.settings import AnalysisSettings, PathSettings
from imprint.engine.cache import CachedFace, EmbeddingCache
from imprint.engine.images import ImageDecoder, discover_images
from imprint.engine.protocols import FaceAnalyser
from imprint.engine.reference import build_core_references
from imprint.engine.scoring import score_subfolder, unique_destination
from imprint.events.pipeline import (
    Finished,
    Halted,
    ImageProcessed,
    PipelineEvent,
    Progress,
    RunStarted,
    Stage,
    StageChanged,
    SummaryEvent,
)

logger = logging.getLogger(__name__)

PipelineCallback = Callable[[PipelineEvent], None]


@dataclass(frozen=True)
class EngineOptions:
    """Optional v6 performance and caching settings.

    Attributes:
        decode_workers: Decode threads used to read ahead of inference.
        decode_window: Maximum outstanding decode tasks.
        cache_path: SQLite cache location.  ``None`` disables caching.
    """

    decode_workers: int = 2
    decode_window: int | None = None
    cache_path: Path | None = None


class EngineV6:
    """GPU face-similarity sorter with the v6 execution pipeline."""

    def __init__(
        self,
        paths: PathSettings,
        analysis: AnalysisSettings,
        emit: PipelineCallback,
        cancel_event: threading.Event,
        face_analyser: FaceAnalyser | None = None,
        *,
        options: EngineOptions | None = None,
        pause_event: threading.Event | None = None,
    ) -> None:
        self._paths = paths
        self._settings = analysis
        self._emit = emit
        self._cancel = cancel_event
        self._pause = pause_event
        self._analyser = face_analyser
        self._options = options or EngineOptions()

    # -- Public entry point ------------------------------------------------

    def run(self) -> RunSummary | None:
        """Execute the full pipeline on the calling thread."""
        summary: RunSummary | None = None
        try:
            summary = self._run_pipeline()
        except Exception as exc:  # pragma: no cover - defensive
            logger.critical("Unhandled error in engine: %s", exc, exc_info=True)
            self._emit(Halted(f"An unexpected error occurred:\n\n{exc}"))
        finally:
            self._emit(Finished(cancelled=self._cancel.is_set()))
        return summary

    # -- Pipeline stages ---------------------------------------------------

    def _run_pipeline(self) -> RunSummary | None:
        self._emit(
            RunStarted(
                model_name=self._settings.model_name,
                reference_folder=Path(self._paths.reference_folder),
                source_folder=Path(self._paths.source_folder),
                destination_folder=Path(self._paths.destination_folder),
            )
        )
        if self._wait_while_paused():
            return None

        analyser = self._analyser if self._analyser is not None else self._load_analyser()
        if analyser is None:
            return None

        cache = self._open_cache()
        try:
            self._emit(
                StageChanged(Stage.REFERENCES, "Stage 1: Extracting reference embeddings...")
            )
            reference_result = build_core_references(
                analyser,
                Path(self._paths.reference_folder),
                self._settings.distance_threshold,
                self._settings.confidence_threshold,
                cache=cache,
                cancel_event=self._cancel,
                on_progress=self._reference_progress,
            )
            if reference_result.cancelled or self._cancel.is_set():
                return None
            if reference_result.references is None:
                self._emit(Halted(reference_result.error or "Failed to build core reference set."))
                return None

            self._emit(StageChanged(Stage.DISCOVERY, "Discovering source images..."))
            source_images = discover_images(Path(self._paths.source_folder))
            if not source_images:
                self._emit(Halted("No supported images found in the source folder."))
                return None
            if self._cancel.is_set():
                return None

            self._emit(
                StageChanged(
                    Stage.PROCESSING,
                    f"Processing {len(source_images)} images...",
                )
            )
            self._emit(Progress(0, len(source_images), "Starting analysis..."))
            reference_matrix = np.array(reference_result.references.embeddings)
            summary = self._process_source_images(
                analyser,
                source_images,
                reference_matrix,
                cache,
            )
            self._emit(SummaryEvent(summary))
            self._emit(StageChanged(Stage.COMPLETE, "Analysis complete."))
            logger.info("=" * 40)
            logger.info(summary.message())
            logger.info("=" * 40)
            return summary
        finally:
            if cache is not None:
                cache.close()

    def _load_analyser(self) -> FaceAnalyser | None:
        model_name = self._settings.model_name
        self._emit(StageChanged(Stage.REFERENCES, f"Loading '{model_name}' model..."))

        try:
            from insightface.app import FaceAnalysis

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
            return cast(FaceAnalyser, app)
        except Exception as exc:
            logger.error("Failed to load model '%s': %s", model_name, exc)
            self._emit(Halted(f"Failed to load model '{model_name}':\n\n{exc}"))
            return None

    def _open_cache(self) -> EmbeddingCache | None:
        if self._options.cache_path is None:
            return None
        try:
            return EmbeddingCache(self._options.cache_path, self._settings.model_name)
        except (OSError, sqlite3.Error) as exc:
            logger.warning("Embedding cache disabled: %s", exc)
            return None

    def _reference_progress(self, current: int, total: int) -> None:
        self._emit(Progress(current, total, "Extracting reference embeddings..."))

    # -- Source processing -------------------------------------------------

    def _process_source_images(
        self,
        analyser: FaceAnalyser,
        images: list[Path],
        reference_matrix: NDArray[np.floating],
        cache: EmbeddingCache | None,
    ) -> RunSummary:
        total = len(images)
        batch_size = max(1, self._settings.batch_size)
        num_subfolders = max(1, self._settings.number_of_subfolders)
        step_size = self._settings.distance_threshold / num_subfolders
        confidence = self._settings.confidence_threshold
        threshold = self._settings.distance_threshold
        dest_root = Path(self._paths.destination_folder)

        cached_faces: dict[Path, CachedFace | None] = {}
        if cache is not None:
            for image_path in images:
                cached_faces[image_path] = cache.get(image_path)
        missing = [path for path in images if cached_faces.get(path) is None]
        decoder = ImageDecoder(
            missing,
            max_workers=self._options.decode_workers,
            window=self._options.decode_window,
        )
        decoded_images = iter(decoder)

        matched = skipped = errors = processed = 0
        matches: list[MatchRecord] = []
        used_names: dict[Path, int] = {}
        num_batches = math.ceil(total / batch_size)
        stopped = False

        for batch_index in range(num_batches):
            if self._cancel.is_set() or self._wait_while_paused():
                stopped = True
                break

            start = batch_index * batch_size
            end = min(start + batch_size, total)
            self._emit(
                Progress(
                    start,
                    total,
                    f"Processing batch {batch_index + 1}/{num_batches}...",
                )
            )

            for image_path in images[start:end]:
                if self._cancel.is_set() or self._wait_while_paused():
                    stopped = True
                    break

                cached_face = cached_faces.get(image_path)
                if cached_face is not None:
                    event, record = self._process_face(
                        image_path,
                        cached_face,
                        reference_matrix,
                        threshold,
                        confidence,
                        step_size,
                        num_subfolders,
                        dest_root,
                        used_names,
                        cached=True,
                    )
                else:
                    decoded = next(decoded_images)
                    if decoded.image is None:
                        event = ImageProcessed(
                            source=image_path,
                            status=ImageStatus.ERROR,
                            error=decoded.error,
                        )
                        record = None
                    else:
                        event, record = self._analyse_and_process(
                            analyser,
                            image_path,
                            decoded.image,
                            reference_matrix,
                            threshold,
                            confidence,
                            step_size,
                            num_subfolders,
                            dest_root,
                            used_names,
                            cache,
                        )

                self._emit(event)
                processed += 1
                if event.status is ImageStatus.MATCH:
                    matched += 1
                    assert record is not None
                    matches.append(record)
                elif event.status is ImageStatus.SKIP:
                    skipped += 1
                else:
                    errors += 1

            if stopped:
                break

        return RunSummary(
            total=total,
            processed=processed,
            matched=matched,
            skipped=skipped,
            errors=errors,
            cancelled=self._cancel.is_set(),
            matches=tuple(matches),
        )

    def _analyse_and_process(
        self,
        analyser: FaceAnalyser,
        image_path: Path,
        image: NDArray[np.uint8],
        reference_matrix: NDArray[np.floating],
        threshold: float,
        confidence: float,
        step_size: float,
        num_subfolders: int,
        dest_root: Path,
        used_names: dict[Path, int],
        cache: EmbeddingCache | None,
    ) -> tuple[ImageProcessed, MatchRecord | None]:
        try:
            faces = analyser.get(image)
        except Exception as exc:
            logger.error("Error processing %s: %s", image_path.name, exc)
            return (
                ImageProcessed(
                    source=image_path,
                    status=ImageStatus.ERROR,
                    error=str(exc),
                ),
                None,
            )

        if not faces:
            return (
                ImageProcessed(source=image_path, status=ImageStatus.SKIP),
                None,
            )

        best_face = max(faces, key=lambda face: face.det_score)
        face = CachedFace(
            det_score=best_face.det_score,
            embedding=np.asarray(best_face.embedding, dtype=np.float32),
        )
        if cache is not None:
            cache.put(image_path, face.det_score, face.embedding)

        return self._process_face(
            image_path,
            face,
            reference_matrix,
            threshold,
            confidence,
            step_size,
            num_subfolders,
            dest_root,
            used_names,
            cached=False,
        )

    def _process_face(
        self,
        image_path: Path,
        face: CachedFace,
        reference_matrix: NDArray[np.floating],
        threshold: float,
        confidence: float,
        step_size: float,
        num_subfolders: int,
        dest_root: Path,
        used_names: dict[Path, int],
        *,
        cached: bool,
    ) -> tuple[ImageProcessed, MatchRecord | None]:
        if face.det_score < confidence:
            return (
                ImageProcessed(
                    source=image_path,
                    status=ImageStatus.SKIP,
                    det_score=face.det_score,
                    cached=cached,
                ),
                None,
            )

        distance = min_distance_to_references(face.embedding, reference_matrix)
        if distance > threshold:
            return (
                ImageProcessed(
                    source=image_path,
                    status=ImageStatus.SKIP,
                    score=distance,
                    det_score=face.det_score,
                    cached=cached,
                ),
                None,
            )

        try:
            subfolder = score_subfolder(distance, step_size, num_subfolders)
            dest_dir = dest_root / subfolder
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = unique_destination(dest_dir, image_path.name, used_names)

            if not dest_path.resolve().is_relative_to(dest_root.resolve()):
                logger.error(  # pragma: no cover - defensive
                    "Blocked path traversal attempt: %s",  # pragma: no cover
                    image_path.name,  # pragma: no cover
                )  # pragma: no cover
                return (  # pragma: no cover
                    ImageProcessed(
                        source=image_path,
                        status=ImageStatus.ERROR,
                        error="Blocked path traversal attempt.",
                        cached=cached,
                    ),
                    None,
                )

            logger.info(
                "MATCH: %s (score=%.4f) -> %s",
                image_path.name,
                distance,
                subfolder,
            )
            shutil.copy2(str(image_path), str(dest_path))
            record = MatchRecord(
                source=image_path,
                destination=dest_path,
                score=distance,
                subfolder=subfolder,
                cached=cached,
            )
            return (
                ImageProcessed(
                    source=image_path,
                    status=ImageStatus.MATCH,
                    score=distance,
                    det_score=face.det_score,
                    subfolder=subfolder,
                    destination=dest_path,
                    cached=cached,
                ),
                record,
            )
        except Exception as exc:
            logger.error("Error copying %s: %s", image_path.name, exc)
            return (
                ImageProcessed(
                    source=image_path,
                    status=ImageStatus.ERROR,
                    score=distance,
                    det_score=face.det_score,
                    cached=cached,
                    error=str(exc),
                ),
                None,
            )

    def _wait_while_paused(self) -> bool:
        """Block while paused.  Returns ``True`` if cancellation won."""
        if self._pause is None:
            return False
        while self._pause.is_set():
            if self._cancel.wait(0.05):
                return True
        return False
