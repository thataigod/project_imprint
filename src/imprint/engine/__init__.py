"""Face-sorting engine package.

The v5 implementation is retained as :mod:`imprint.engine.legacy` until
the v6 pipeline reaches parity.
"""

from imprint.engine.legacy import EventCallback, FaceAnalyser, FaceResult, SorterEngine

__all__ = ["EventCallback", "FaceAnalyser", "FaceResult", "SorterEngine"]
