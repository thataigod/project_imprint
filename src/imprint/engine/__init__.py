"""Face-sorting engine package.

``EngineV6`` is the production pipeline.  ``SorterEngine`` remains an alias
for the v5 implementation, retained as a parity and benchmark fixture.
"""

from imprint.domain.results import ImageStatus, MatchRecord, RunSummary
from imprint.engine.legacy import (
    EventCallback,
    FaceAnalyser,
    FaceResult,
    SorterEngine,
)
from imprint.engine.legacy import SorterEngine as LegacySorterEngine
from imprint.engine.pipeline import EngineOptions, EngineV6

__all__ = [
    "EngineOptions",
    "EngineV6",
    "EventCallback",
    "FaceAnalyser",
    "FaceResult",
    "ImageStatus",
    "LegacySorterEngine",
    "MatchRecord",
    "RunSummary",
    "SorterEngine",
]
