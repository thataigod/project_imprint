"""Benchmark legacy versus v6 engine throughput and cache speedup.

This uses a deterministic fake analyser so it measures pipeline, I/O, copy,
and cache overhead without requiring a GPU.
"""

from __future__ import annotations

import argparse
import gc
import shutil
import sys
import tempfile
import threading
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from imprint.domain.settings import AnalysisSettings, PathSettings  # noqa: E402
from imprint.engine import LegacySorterEngine  # noqa: E402
from imprint.engine.pipeline import EngineOptions, EngineV6  # noqa: E402
from imprint.events.pipeline import ImageProcessed  # noqa: E402

EMBEDDING = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)


@dataclass
class FakeFace:
    det_score: float
    embedding: NDArray[np.float32]


class FixedAnalyser:
    """Return one confident face for every image."""

    def __init__(self, delay_ms: float = 0.0) -> None:
        self._delay = delay_ms / 1000.0

    def prepare(self, ctx_id: int, det_size: tuple[int, int]) -> None:
        return None

    def get(self, img: NDArray[Any]) -> list[FakeFace]:
        if self._delay:
            time.sleep(self._delay)
        return [FakeFace(0.99, EMBEDDING)]


def write_images(folder: Path, count: int, size: int) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    image = np.zeros((size, size, 3), dtype=np.uint8)
    for index in range(count):
        assert cv2.imwrite(str(folder / f"image_{index:06d}.png"), image)


def make_paths(root: Path) -> PathSettings:
    reference = root / "reference"
    source = root / "source"
    destination = root / "destination"
    write_images(reference, 3, 16)
    source.mkdir(parents=True)
    destination.mkdir()
    return PathSettings(
        reference_folder=str(reference),
        source_folder=str(source),
        destination_folder=str(destination),
    )


def run_legacy(paths: PathSettings, analysis: AnalysisSettings, delay_ms: float) -> float:
    start = time.perf_counter()
    LegacySorterEngine(
        paths=paths,
        analysis=analysis,
        emit=lambda event: None,
        cancel_event=threading.Event(),
        face_analyser=FixedAnalyser(delay_ms),  # type: ignore[arg-type]
    ).run()
    return time.perf_counter() - start


def run_v6(
    paths: PathSettings,
    analysis: AnalysisSettings,
    *,
    cache_path: Path | None,
    delay_ms: float,
) -> tuple[float, int]:
    events: list[ImageProcessed] = []
    start = time.perf_counter()
    EngineV6(
        paths=paths,
        analysis=analysis,
        emit=lambda event: events.append(event) if isinstance(event, ImageProcessed) else None,
        cancel_event=threading.Event(),
        face_analyser=FixedAnalyser(delay_ms),  # type: ignore[arg-type]
        options=EngineOptions(cache_path=cache_path),
    ).run()
    elapsed = time.perf_counter() - start
    return elapsed, sum(event.cached for event in events)


def clear_destination(paths: PathSettings) -> None:
    destination = Path(paths.destination_folder)
    shutil.rmtree(destination)
    destination.mkdir()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark Imprint engines.")
    parser.add_argument("--images", type=int, default=300, help="Source image count.")
    parser.add_argument("--size", type=int, default=16, help="Generated image size.")
    parser.add_argument(
        "--inference-ms",
        type=float,
        default=0.0,
        help="Fake per-image inference delay in milliseconds.",
    )
    args = parser.parse_args(argv)
    if args.images < 1:
        parser.error("--images must be positive")

    with tempfile.TemporaryDirectory(prefix="imprint-bench-") as temp:
        root = Path(temp)
        analysis = AnalysisSettings(
            model_name="buffalo_s",
            distance_threshold=0.5,
            confidence_threshold=0.5,
            batch_size=8,
            number_of_subfolders=10,
            cache_enabled=True,
        )

        legacy_paths = make_paths(root / "legacy")
        write_images(Path(legacy_paths.source_folder), args.images, args.size)
        gc.collect()
        legacy_time = run_legacy(legacy_paths, analysis, args.inference_ms)

        v6_paths = make_paths(root / "v6")
        write_images(Path(v6_paths.source_folder), args.images, args.size)
        cache_path = root / "cache.sqlite3"
        gc.collect()
        tracemalloc.start()
        v6_cold, _ = run_v6(
            v6_paths,
            analysis,
            cache_path=cache_path,
            delay_ms=args.inference_ms,
        )
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        clear_destination(v6_paths)
        gc.collect()
        v6_warm, cached_count = run_v6(
            v6_paths,
            analysis,
            cache_path=cache_path,
            delay_ms=args.inference_ms,
        )

        print(f"Images: {args.images}")
        print(f"Inference delay: {args.inference_ms:.1f} ms/image")
        print(f"v5 engine:            {legacy_time:.3f}s")
        print(f"v6 cold cache:        {v6_cold:.3f}s")
        print(f"v6 warm cache:        {v6_warm:.3f}s ({cached_count} cache hits)")
        if v6_warm > 0:
            print(f"Cache speedup:        {v6_cold / v6_warm:.2f}x")
        print(f"Python peak memory:   {peak / 1024 / 1024:.1f} MiB")
        return 0


if __name__ == "__main__":
    sys.exit(main())
