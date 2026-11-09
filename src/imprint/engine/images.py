"""Image discovery and overlapped decoding.

The v6 pipeline decodes images on a small thread pool while the GPU
worker runs inference, keeping both resources busy without changing the
order in which results are processed.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from imprint.domain.constants import SUPPORTED_EXTENSIONS


@dataclass(frozen=True)
class DecodedImage:
    """One decoded image or the error that prevented decoding."""

    path: Path
    image: NDArray[Any] | None
    error: str | None = None


def discover_images(folder: Path) -> list[Path]:
    """Recursively discover supported images under *folder*."""
    return sorted(
        p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def discover_reference_images(folder: Path) -> list[Path]:
    """Discover supported images directly inside *folder*.

    Reference scans intentionally stay non-recursive to match v5.
    """
    return sorted(
        p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


class ImageDecoder:
    """Yield decoded images in order while reading ahead on a thread pool.

    Args:
        paths: Image paths to decode, in processing order.
        max_workers: Number of decode threads.
        window: Maximum number of outstanding decode tasks.
    """

    def __init__(
        self,
        paths: Sequence[Path],
        max_workers: int = 2,
        window: int | None = None,
    ) -> None:
        self._paths = list(paths)
        self._max_workers = max(1, max_workers)
        self._window = max(1, window if window is not None else self._max_workers * 2)

    def __iter__(self) -> Iterator[DecodedImage]:
        if not self._paths:
            return

        executor = ThreadPoolExecutor(max_workers=self._max_workers)
        pending: deque[tuple[Path, Future[DecodedImage]]] = deque()
        next_index = 0

        try:
            while next_index < len(self._paths) and len(pending) < self._window:
                path = self._paths[next_index]
                pending.append((path, executor.submit(self._decode, path)))
                next_index += 1

            while pending:
                path, future = pending.popleft()
                try:
                    yield future.result()
                except Exception as exc:  # pragma: no cover - defensive
                    yield DecodedImage(path, None, str(exc))

                if next_index < len(self._paths):
                    next_path = self._paths[next_index]
                    pending.append((next_path, executor.submit(self._decode, next_path)))
                    next_index += 1
        finally:
            for _, future in pending:
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _decode(path: Path) -> DecodedImage:
        image = cv2.imread(str(path))
        if image is None:
            return DecodedImage(path, None, f"Could not read image: {path.name}")
        return DecodedImage(path, np.asarray(image))
