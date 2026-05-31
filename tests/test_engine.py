"""Unit tests for imprint.engine.

Covers the SorterEngine using mock face analysers to avoid GPU
and model dependencies.  Tests core logic: subfolder naming,
unique destination paths, event emission, and cancellation.
"""

from __future__ import annotations

import threading
from pathlib import Path

from imprint.config import AnalysisSettings, PathSettings
from imprint.engine import SorterEngine
from imprint.events import EngineEvent, EventType, MessageLevel

# Import fixtures from conftest
from tests.conftest import MockFaceAnalyser


class TestScoreSubfolder:
    """Tests for SorterEngine._score_subfolder()."""

    def test_zero_distance(self) -> None:
        """Distance of 0 should map to the first bin."""
        result = SorterEngine._score_subfolder(0.0, 0.1, 5)
        assert result == "Score_0.000_to_0.100"

    def test_mid_range_distance(self) -> None:
        """A mid-range distance should map to the correct bin."""
        result = SorterEngine._score_subfolder(0.25, 0.1, 5)
        assert result == "Score_0.200_to_0.300"

    def test_max_distance_clamps_to_last_bin(self) -> None:
        """Distance at the threshold should map to the last bin."""
        result = SorterEngine._score_subfolder(0.5, 0.1, 5)
        assert result == "Score_0.400_to_0.500"

    def test_exact_bin_boundary(self) -> None:
        """Distance exactly at a bin boundary should map correctly."""
        result = SorterEngine._score_subfolder(0.1, 0.1, 5)
        assert result == "Score_0.100_to_0.200"

    def test_single_subfolder(self) -> None:
        """With 1 subfolder, everything maps to the same bin."""
        result = SorterEngine._score_subfolder(0.3, 0.5, 1)
        assert result == "Score_0.000_to_0.500"

    def test_formatting_precision(self) -> None:
        """Output should always have 3 decimal places."""
        result = SorterEngine._score_subfolder(0.1, 0.05, 10)
        assert result == "Score_0.100_to_0.150"


class TestUniqueDestPath:
    """Tests for SorterEngine._unique_dest_path()."""

    def test_first_file_is_unchanged(self, tmp_path: Path) -> None:
        """First occurrence of a filename should be unchanged."""
        used: dict[Path, int] = {}
        result = SorterEngine._unique_dest_path(tmp_path, "photo.jpg", used)
        assert result == tmp_path / "photo.jpg"

    def test_duplicate_gets_suffix(self, tmp_path: Path) -> None:
        """Second occurrence should get a _1 suffix."""
        used: dict[Path, int] = {}
        SorterEngine._unique_dest_path(tmp_path, "photo.jpg", used)
        second = SorterEngine._unique_dest_path(tmp_path, "photo.jpg", used)
        assert second == tmp_path / "photo_1.jpg"

    def test_triple_duplicate_increments(self, tmp_path: Path) -> None:
        """Third occurrence should get a _2 suffix."""
        used: dict[Path, int] = {}
        SorterEngine._unique_dest_path(tmp_path, "photo.jpg", used)
        SorterEngine._unique_dest_path(tmp_path, "photo.jpg", used)
        third = SorterEngine._unique_dest_path(tmp_path, "photo.jpg", used)
        assert third == tmp_path / "photo_2.jpg"

    def test_existing_file_on_disk(self, tmp_path: Path) -> None:
        """Should skip names that already exist on disk."""
        (tmp_path / "photo.jpg").touch()
        used: dict[Path, int] = {}
        result = SorterEngine._unique_dest_path(tmp_path, "photo.jpg", used)
        assert result == tmp_path / "photo_1.jpg"

    def test_preserves_extension(self, tmp_path: Path) -> None:
        """The file extension should be preserved on renamed files."""
        used: dict[Path, int] = {}
        SorterEngine._unique_dest_path(tmp_path, "image.png", used)
        result = SorterEngine._unique_dest_path(tmp_path, "image.png", used)
        assert result.suffix == ".png"


class TestEngineEventEmission:
    """Tests for event emission during engine lifecycle."""

    def test_finished_event_always_emitted(
        self,
        default_path_settings: PathSettings,
        default_analysis_settings: AnalysisSettings,
        cancel_event: threading.Event,
    ) -> None:
        """The engine should always emit a FINISHED event, even on failure."""
        events: list[EngineEvent] = []

        # Create engine with mock analyser that will cause no refs to be found
        mock_analyser = MockFaceAnalyser(faces_per_image=[])
        engine = SorterEngine(
            paths=default_path_settings,
            analysis=default_analysis_settings,
            emit=events.append,
            cancel_event=cancel_event,
            face_analyser=mock_analyser,
        )
        engine.run()

        event_types = [e.event_type for e in events]
        assert EventType.FINISHED in event_types
        # FINISHED should be the last event
        assert events[-1].event_type == EventType.FINISHED

    def test_cancellation_emits_finished(
        self,
        default_path_settings: PathSettings,
        default_analysis_settings: AnalysisSettings,
    ) -> None:
        """Cancellation should still result in a FINISHED event."""
        events: list[EngineEvent] = []
        cancel = threading.Event()
        cancel.set()  # Pre-cancel

        mock_analyser = MockFaceAnalyser(faces_per_image=[])
        engine = SorterEngine(
            paths=default_path_settings,
            analysis=default_analysis_settings,
            emit=events.append,
            cancel_event=cancel,
            face_analyser=mock_analyser,
        )
        engine.run()

        event_types = [e.event_type for e in events]
        assert EventType.FINISHED in event_types

    def test_empty_reference_folder_shows_error(
        self,
        default_path_settings: PathSettings,
        default_analysis_settings: AnalysisSettings,
        cancel_event: threading.Event,
    ) -> None:
        """An empty reference folder should emit an error message and halt."""
        events: list[EngineEvent] = []
        mock_analyser = MockFaceAnalyser(faces_per_image=[])

        engine = SorterEngine(
            paths=default_path_settings,
            analysis=default_analysis_settings,
            emit=events.append,
            cancel_event=cancel_event,
            face_analyser=mock_analyser,
        )
        engine.run()

        message_events = [
            e for e in events if e.event_type == EventType.MESSAGE
        ]
        assert len(message_events) >= 1
        assert any(e.level == MessageLevel.ERROR for e in message_events)


class TestEngineDiscoverImages:
    """Tests for _discover_images (via public interface)."""

    def test_finds_supported_extensions(self, tmp_path: Path) -> None:
        """Should find images with supported extensions."""
        from imprint.constants import SUPPORTED_EXTENSIONS

        for ext in SUPPORTED_EXTENSIONS:
            (tmp_path / f"test{ext}").touch()
        (tmp_path / "readme.txt").touch()  # Should be ignored

        engine = SorterEngine(
            paths=PathSettings(),
            analysis=AnalysisSettings(),
            emit=lambda e: None,
            cancel_event=threading.Event(),
        )
        images = engine._discover_images(tmp_path)
        assert len(images) == len(SUPPORTED_EXTENSIONS)
        assert all(p.suffix.lower() in SUPPORTED_EXTENSIONS for p in images)

    def test_recursive_discovery(self, tmp_path: Path) -> None:
        """Should find images in subdirectories."""
        sub = tmp_path / "subdir"
        sub.mkdir()
        (tmp_path / "top.jpg").touch()
        (sub / "nested.jpg").touch()

        engine = SorterEngine(
            paths=PathSettings(),
            analysis=AnalysisSettings(),
            emit=lambda e: None,
            cancel_event=threading.Event(),
        )
        images = engine._discover_images(tmp_path)
        assert len(images) == 2

    def test_empty_folder(self, tmp_path: Path) -> None:
        """An empty folder should return no images."""
        engine = SorterEngine(
            paths=PathSettings(),
            analysis=AnalysisSettings(),
            emit=lambda e: None,
            cancel_event=threading.Event(),
        )
        images = engine._discover_images(tmp_path)
        assert images == []
