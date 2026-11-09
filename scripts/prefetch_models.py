"""Download the InsightFace model packs used by Imprint.

Run this once before packaging or on a machine without internet access:

    python scripts/prefetch_models.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from imprint.domain.constants import MODEL_REGISTRY  # noqa: E402


def prefetch(model_names: list[str]) -> int:
    from insightface.app import FaceAnalysis

    for model_name in model_names:
        profile = MODEL_REGISTRY.get(model_name)
        if profile is None:
            print(f"Unknown model: {model_name}", file=sys.stderr)
            return 2

        kwargs: dict[str, object] = {
            "allowed_modules": ["detection", "recognition"],
            "providers": ["CPUExecutionProvider"],
        }
        if profile.use_rec_name:
            kwargs["rec_name"] = model_name
        else:
            kwargs["name"] = model_name

        print(f"Downloading/loading {profile.display_name}...")
        FaceAnalysis(**kwargs)
        print(f"Ready: {profile.display_name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prefetch InsightFace models.")
    parser.add_argument(
        "models",
        nargs="*",
        default=list(MODEL_REGISTRY),
        help="Model code names (default: all).",
    )
    args = parser.parse_args(argv)
    return prefetch(list(args.models))


if __name__ == "__main__":
    sys.exit(main())
