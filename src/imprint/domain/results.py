"""Result models produced by the v6 engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class ImageStatus(Enum):
    """Outcome of processing a single source image."""

    MATCH = auto()
    SKIP = auto()
    ERROR = auto()


@dataclass(frozen=True)
class MatchRecord:
    """A source image copied into the destination folder."""

    source: Path
    destination: Path
    score: float
    subfolder: str
    cached: bool = False


@dataclass(frozen=True)
class RunSummary:
    """Final counts and match records for one analysis run."""

    total: int
    processed: int
    matched: int
    skipped: int
    errors: int
    cancelled: bool
    matches: tuple[MatchRecord, ...] = field(default_factory=tuple)

    def message(self) -> str:
        """Return a human-readable summary compatible with the v5 wording."""
        if self.cancelled:
            return (
                "Analysis Cancelled.\n\n"
                f"Of {self.processed} images scanned:\n"
                f"  \u2022 Matches found: {self.matched}\n"
                f"  \u2022 Skipped: {self.skipped}\n"
                f"  \u2022 Errors: {self.errors}"
            )
        return (
            "Analysis Complete!\n\n"
            f"Of {self.total} total images:\n"
            f"  \u2022 Matches found: {self.matched}\n"
            f"  \u2022 Skipped (no match/face/low confidence): {self.skipped}\n"
            f"  \u2022 Errors (corrupt/unreadable): {self.errors}"
        )
