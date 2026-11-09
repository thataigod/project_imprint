"""Pure helpers for score tiering and duplicate-safe destination names."""

from __future__ import annotations

import math
from pathlib import Path


def score_subfolder(distance: float, step_size: float, num_subfolders: int) -> str:
    """Compute the score-range subfolder name for a match distance.

    Args:
        distance: Cosine distance of the match.
        step_size: Width of each score bin.
        num_subfolders: Total number of bins.

    Returns:
        A name like ``Score_0.000_to_0.050``.
    """
    bin_index = 0 if distance == 0 else math.floor(distance / step_size)
    bin_index = min(bin_index, num_subfolders - 1)

    lower = bin_index * step_size
    upper = (bin_index + 1) * step_size
    return f"Score_{lower:.3f}_to_{upper:.3f}"


def unique_destination(
    dest_dir: Path,
    basename: str,
    used_names: dict[Path, int],
) -> Path:
    """Generate a unique destination path, appending ``_N`` when needed.

    Args:
        dest_dir: Target directory.
        basename: Original filename.
        used_names: Mutable dict tracking names already requested.

    Returns:
        A path within *dest_dir* that does not collide with planned or
        existing files.
    """
    candidate = dest_dir / basename
    if candidate not in used_names and not candidate.exists():
        used_names[candidate] = 1
        return candidate

    stem = Path(basename).stem
    suffix = Path(basename).suffix
    counter = used_names.get(candidate, 1)
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = dest_dir / new_name
        if new_path not in used_names and not new_path.exists():
            used_names[candidate] = counter + 1
            used_names[new_path] = 1
            return new_path
        counter += 1  # pragma: no cover
