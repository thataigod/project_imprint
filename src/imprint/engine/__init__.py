"""Face-sorting engine package.

``EngineV6`` is the new pipeline.  ``SorterEngine`` remains an alias for
the v5 implementation until the QML front end reaches parity.
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
