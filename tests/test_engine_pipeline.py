"""Pipeline tests for the SorterEngine."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from numpy.typing import NDArray

from imprint.config import AnalysisSettings, AppSettings, PathSettings
from imprint.engine import SorterEngine
from imprint.events import EventType


@pytest.fixture
def dummy_config(tmp_path: Path) -> AppSettings:
    """Provide a valid dummy configuration."""
    paths = PathSettings(
        source_folder=str(tmp_path / "source"),
        reference_folder=str(tmp_path / "ref"),
        destination_folder=str(tmp_path / "dest"),
    )
    Path(paths.source_folder).mkdir(parents=True)
    Path(paths.reference_folder).mkdir(parents=True)
    Path(paths.destination_folder).mkdir(parents=True)

    # Create fake images
    (Path(paths.source_folder) / "src1.jpg").touch()
    (Path(paths.source_folder) / "src2.jpg").touch()
    (Path(paths.reference_folder) / "ref1.jpg").touch()
    (Path(paths.reference_folder) / "ref2.jpg").touch()

    models = AnalysisSettings(
        model_name="buffalo_s",
        confidence_threshold=0.5,
        distance_threshold=0.6,
        batch_size=2,
        number_of_subfolders=3,
    )
    return AppSettings(paths=paths, analysis=models)


class DummyFace:
    """Mock insightface result object."""
    def __init__(self, normed_embedding: NDArray[Any], det_score: float = 0.9):
        self.embedding = normed_embedding
        self.det_score = det_score


def test_engine_successful_pipeline(dummy_config: AppSettings) -> None:
    """Verify the full success path of the engine run() method."""
    cancel = threading.Event()
    events = []
    engine = SorterEngine(
        paths=dummy_config.paths,
        analysis=dummy_config.analysis,
        emit=events.append,
        cancel_event=cancel
    )

    # Mock InsightFace FaceAnalysis
    with patch("insightface.app.FaceAnalysis") as mock_face_analysis:
        mock_app = MagicMock()
        mock_face_analysis.return_value = mock_app

        # Mock get_model_by_display_name to return a fake profile
        mock_profile = MagicMock()
        mock_profile.use_rec_name = False
        with patch.dict("imprint.constants.MODEL_REGISTRY", {"buffalo_s": mock_profile}):

            # Mock cv2.imread and insightface inference
            import numpy as np
            with patch("cv2.imread", return_value=np.zeros((100, 100, 3), dtype=np.uint8)):
                # Mock face detection to return 1 face per image
                mock_app.get.return_value = [DummyFace(np.array([1.0, 0.0]))]

                # Mock shutil.copy2 to prevent real file copies
                with patch("shutil.copy2") as mock_copy:
                    engine.run()

                    # Verify successful execution
                    assert mock_copy.call_count == 2  # 2 source images


                    event_types = [e.event_type for e in events]

                    assert EventType.PROGRESS in event_types
                    assert EventType.FINISHED in event_types
                    assert EventType.HALTED not in event_types


def test_engine_insufficient_references(dummy_config: AppSettings) -> None:
    """Verify pipeline halts if not enough references are found."""
    cancel = threading.Event()
    events = []
    engine = SorterEngine(
        paths=dummy_config.paths,
        analysis=dummy_config.analysis,
        emit=events.append,
        cancel_event=cancel
    )

    with patch("insightface.app.FaceAnalysis") as mock_face_analysis:
        mock_app = MagicMock()
        mock_face_analysis.return_value = mock_app

        mock_profile = MagicMock()
        mock_profile.use_rec_name = False
        with patch.dict("imprint.constants.MODEL_REGISTRY", {"buffalo_s": mock_profile}):

            import numpy as np
            with patch("cv2.imread", return_value=np.zeros((10, 10, 3), dtype=np.uint8)):
                # Mock get to return NO faces
                mock_app.get.return_value = []

                engine.run()


                error_events = [e for e in events if e.event_type == EventType.MESSAGE and e.level.value == "error"]
                assert len(error_events) > 0
                assert "Found only 0 reference face(s)" in error_events[0].message


def test_engine_load_model_exception(dummy_config: AppSettings) -> None:
    """Verify the pipeline gracefully handles unhandled exceptions during init."""
    cancel = threading.Event()
    events = []
    engine = SorterEngine(
        paths=dummy_config.paths,
        analysis=dummy_config.analysis,
        emit=events.append,
        cancel_event=cancel
    )

    # Patch FaceAnalysis to raise an unexpected error
    with patch("insightface.app.FaceAnalysis", side_effect=RuntimeError("CUDA out of memory")):
        mock_profile = MagicMock()
        mock_profile.use_rec_name = True
        with patch.dict("imprint.constants.MODEL_REGISTRY", {"buffalo_s": mock_profile}):

            engine.run()


            error_events = [e for e in events if e.event_type == EventType.MESSAGE and e.level.value == "error"]
            assert len(error_events) > 0
            assert "CUDA out of memory" in error_events[0].message


def test_engine_cancellation_during_run(dummy_config: AppSettings) -> None:
    """Verify cancellation event stops the pipeline early."""
    cancel = threading.Event()
    events = []
    engine = SorterEngine(
        paths=dummy_config.paths,
        analysis=dummy_config.analysis,
        emit=events.append,
        cancel_event=cancel
    )

    # Pre-set the cancel event so it exits immediately after load
    cancel.set()

    with patch("insightface.app.FaceAnalysis") as mock_face_analysis:
        mock_app = MagicMock()
        mock_face_analysis.return_value = mock_app

        mock_profile = MagicMock()
        with patch.dict("imprint.constants.MODEL_REGISTRY", {"buffalo_s": mock_profile}):

            engine.run()

            # The engine should exit after checking the cancel flag early on
            assert events[-1].event_type == EventType.FINISHED
