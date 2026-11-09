"""Protocols that decouple the engine from InsightFace.

The protocols keep the pipeline fully testable without a GPU, model
downloads, or the InsightFace runtime.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray


@runtime_checkable
class FaceResult(Protocol):
    """Minimal interface for a single detected face."""

    @property
    def det_score(self) -> float: ...  # noqa: E704

    @property
    def embedding(self) -> NDArray[np.floating]: ...  # noqa: E704


@runtime_checkable
class FaceAnalyser(Protocol):
    """Minimal interface wrapping InsightFace's FaceAnalysis."""

    def prepare(self, ctx_id: int, det_size: tuple[int, int]) -> None: ...  # noqa: E704

    def get(self, img: NDArray[Any]) -> list[FaceResult]: ...  # noqa: E704
