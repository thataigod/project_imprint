"""Rich pipeline events consumed by the v6 UI.

These events are intentionally separate from the v5 ``EngineEvent`` so
parity and benchmark fixtures keep their exact contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from imprint.domain.results import ImageStatus, RunSummary


class Stage(Enum):
    """High-level stage of an analysis run."""

    REFERENCES = auto()
    DISCOVERY = auto()
    PROCESSING = auto()
    COMPLETE = auto()


@dataclass(frozen=True)
class RunStarted:
    """Emitted once when a run begins."""

    model_name: str
    reference_folder: Path
    source_folder: Path
    destination_folder: Path


@dataclass(frozen=True)
class StageChanged:
    """Emitted when the pipeline moves to a new stage."""

    stage: Stage
    message: str


@dataclass(frozen=True)
class SourceDiscovered:
    """Emitted after the source folder scan with the total image count."""

    total: int


@dataclass(frozen=True)
class Progress:
    """Progress for the current stage."""

    current: int
    total: int
    message: str = ""


@dataclass(frozen=True)
class ImageProcessed:
    """Emitted for every source image that was handled."""

    source: Path
    status: ImageStatus
    score: float | None = None
    det_score: float | None = None
    subfolder: str | None = None
    destination: Path | None = None
    cached: bool = False
    error: str | None = None


@dataclass(frozen=True)
class SummaryEvent:
    """Emitted once at the end of a completed or cancelled run."""

    summary: RunSummary


@dataclass(frozen=True)
class Halted:
    """Emitted when the run cannot continue."""

    message: str


@dataclass(frozen=True)
class Finished:
    """Emitted last for every run, regardless of outcome."""

    cancelled: bool = False


PipelineEvent = (
    RunStarted
    | StageChanged
    | SourceDiscovered
    | Progress
    | ImageProcessed
    | SummaryEvent
    | Halted
    | Finished
)

__all__ = [
    "Finished",
    "Halted",
    "ImageProcessed",
    "PipelineEvent",
    "Progress",
    "RunStarted",
    "SourceDiscovered",
    "Stage",
    "StageChanged",
    "SummaryEvent",
]
