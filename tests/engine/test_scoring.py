"""Tests for score-tier naming and duplicate-safe destinations."""

from __future__ import annotations

from pathlib import Path

from imprint.engine.scoring import score_subfolder, unique_destination


class TestScoreSubfolder:
    def test_zero_distance(self) -> None:
        assert score_subfolder(0.0, 0.1, 5) == "Score_0.000_to_0.100"

    def test_mid_range(self) -> None:
        assert score_subfolder(0.25, 0.1, 5) == "Score_0.200_to_0.300"

    def test_threshold_clamps_to_last_bin(self) -> None:
        assert score_subfolder(0.5, 0.1, 5) == "Score_0.400_to_0.500"

    def test_exact_boundary(self) -> None:
        assert score_subfolder(0.1, 0.1, 5) == "Score_0.100_to_0.200"

    def test_single_bin(self) -> None:
        assert score_subfolder(0.3, 0.5, 1) == "Score_0.000_to_0.500"


class TestUniqueDestination:
    def test_first_name_is_unchanged(self, tmp_path: Path) -> None:
        used: dict[Path, int] = {}
        assert unique_destination(tmp_path, "photo.jpg", used) == tmp_path / "photo.jpg"

    def test_duplicate_gets_suffix(self, tmp_path: Path) -> None:
        used: dict[Path, int] = {}
        unique_destination(tmp_path, "photo.jpg", used)
        assert unique_destination(tmp_path, "photo.jpg", used) == tmp_path / "photo_1.jpg"

    def test_existing_file_is_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "photo.jpg").touch()
        used: dict[Path, int] = {}
        assert unique_destination(tmp_path, "photo.jpg", used) == tmp_path / "photo_1.jpg"
