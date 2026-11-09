"""Tests for the v6 EngineV6 pipeline."""

from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from imprint.domain.results import ImageStatus
from imprint.domain.settings import AnalysisSettings, PathSettings
from imprint.engine.pipeline import EngineOptions, EngineV6
from imprint.events.pipeline import (
    Finished,
    Halted,
    ImageProcessed,
    RunStarted,
    Stage,
    StageChanged,
    SummaryEvent,
)
from tests.engine.helpers import (
    MarkerAnalyser,
    make_engine_env,
    reference_mapping,
    snapshot,
    source_mapping,
)


def merged_mapping() -> dict:
    return {**reference_mapping(), **source_mapping()}


def make_engine(
    paths: PathSettings,
    analysis: AnalysisSettings,
    *,
    events: list,
    analyser: MarkerAnalyser | None = None,
    options: EngineOptions | None = None,
    pause: threading.Event | None = None,
    cancel: threading.Event | None = None,
) -> EngineV6:
    return EngineV6(
        paths=paths,
        analysis=analysis,
        emit=events.append,
        cancel_event=cancel or threading.Event(),
        face_analyser=analyser or MarkerAnalyser(merged_mapping()),
        options=options,
        pause_event=pause,
    )


class TestFullRun:
    def test_matches_expected_results_and_events(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        events: list = []
        summary = make_engine(paths, analysis, events=events).run()

        assert summary is not None
        assert summary.total == 8
        assert summary.processed == 8
        assert summary.matched == 4
        assert summary.skipped == 3
        assert summary.errors == 1
        assert summary.cancelled is False
        assert len(summary.matches) == 4
        assert "Analysis Complete!" in summary.message()
        assert "Matches found: 4" in summary.message()

        files = [name for name, _ in snapshot(Path(paths.destination_folder))]
        assert files == [
            "Score_0.000_to_0.050/duplicate.png",
            "Score_0.000_to_0.050/duplicate_1.png",
            "Score_0.000_to_0.050/exact.png",
            "Score_0.000_to_0.050/near.png",
        ]

        assert isinstance(events[0], RunStarted)
        stages = {event.stage for event in events if isinstance(event, StageChanged)}
        assert stages == {
            Stage.REFERENCES,
            Stage.DISCOVERY,
            Stage.PROCESSING,
            Stage.COMPLETE,
        }
        processed = [event for event in events if isinstance(event, ImageProcessed)]
        assert len(processed) == 8
        statuses = [event.status for event in processed]
        assert statuses.count(ImageStatus.MATCH) == 4
        assert statuses.count(ImageStatus.SKIP) == 3
        assert statuses.count(ImageStatus.ERROR) == 1
        assert any(isinstance(event, SummaryEvent) for event in events)
        assert isinstance(events[-1], Finished)
        assert not any(isinstance(event, Halted) for event in events)

    def test_cache_makes_repeat_run_reuse_embeddings(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        destination = Path(paths.destination_folder)
        cache_path = tmp_path / "cache.sqlite3"

        first_events: list = []
        first = make_engine(
            paths,
            analysis,
            events=first_events,
            options=EngineOptions(cache_path=cache_path),
        ).run()
        assert first is not None
        first_snapshot = snapshot(destination)

        shutil.rmtree(destination)
        destination.mkdir()
        second_events: list = []
        second = make_engine(
            paths,
            analysis,
            events=second_events,
            options=EngineOptions(cache_path=cache_path),
        ).run()

        assert second is not None
        assert second.matched == first.matched
        assert second.skipped == first.skipped
        assert second.errors == first.errors
        assert snapshot(destination) == first_snapshot

        second_processed = [event for event in second_events if isinstance(event, ImageProcessed)]
        assert sum(event.cached for event in second_processed) == 6

    def test_inference_errors_are_counted(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        events: list = []
        analyser = MarkerAnalyser(merged_mapping(), fail_markers={10, 15, 16})
        summary = make_engine(paths, analysis, events=events, analyser=analyser).run()

        assert summary is not None
        assert summary.matched == 1
        assert summary.errors == 4
        errors = [
            event
            for event in events
            if isinstance(event, ImageProcessed) and event.status is ImageStatus.ERROR
        ]
        assert any(event.error and "inference failed" in event.error for event in errors)

    def test_copy_errors_are_counted(self, tmp_path: Path, monkeypatch) -> None:
        paths, analysis = make_engine_env(tmp_path)
        events: list = []

        def fail_copy(source: str, destination: str) -> None:
            raise OSError("disk full")

        monkeypatch.setattr("imprint.engine.pipeline.shutil.copy2", fail_copy)
        summary = make_engine(paths, analysis, events=events).run()

        assert summary is not None
        assert summary.matched == 0
        assert summary.errors == 5
        error_events = [
            event
            for event in events
            if isinstance(event, ImageProcessed) and event.status is ImageStatus.ERROR
        ]
        assert any(event.error == "disk full" for event in error_events)


class TestCancellationAndPause:
    def test_cancelled_before_reference_scan(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        cancel = threading.Event()
        cancel.set()
        events: list = []

        summary = make_engine(
            paths,
            analysis,
            events=events,
            cancel=cancel,
        ).run()

        assert summary is None
        assert not any(isinstance(event, SummaryEvent) for event in events)
        assert isinstance(events[-1], Finished)
        assert events[-1].cancelled is True

    def test_cancelled_during_processing_emits_partial_summary(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        cancel = threading.Event()
        events: list = []

        class CancellingAnalyser(MarkerAnalyser):
            def __init__(self) -> None:
                super().__init__(merged_mapping())
                self.calls = 0

            def get(self, img):
                faces = super().get(img)
                self.calls += 1
                if self.calls == 4:
                    cancel.set()
                return faces

        summary = make_engine(
            paths,
            analysis,
            events=events,
            analyser=CancellingAnalyser(),
            cancel=cancel,
        ).run()

        assert summary is not None
        assert summary.cancelled is True
        assert summary.processed == 1
        assert summary.matched == 1
        assert "Analysis Cancelled." in summary.message()
        assert events[-1].cancelled is True

    def test_cancel_after_discovery_scan(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        cancel = threading.Event()
        events: list = []

        def emit(event: object) -> None:
            events.append(event)
            if isinstance(event, StageChanged) and event.stage is Stage.DISCOVERY:
                cancel.set()

        engine = EngineV6(
            paths=paths,
            analysis=analysis,
            emit=emit,
            cancel_event=cancel,
            face_analyser=MarkerAnalyser(merged_mapping()),
        )
        summary = engine.run()

        assert summary is None
        assert not any(isinstance(event, SummaryEvent) for event in events)
        assert isinstance(events[-1], Finished)
        assert events[-1].cancelled is True

    def test_cancel_between_batches(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        cancel = threading.Event()
        events: list = []
        image_count = [0]

        def emit(event: object) -> None:
            events.append(event)
            if isinstance(event, ImageProcessed):
                image_count[0] += 1
                if image_count[0] == 2:
                    cancel.set()

        engine = EngineV6(
            paths=paths,
            analysis=analysis,
            emit=emit,
            cancel_event=cancel,
            face_analyser=MarkerAnalyser(merged_mapping()),
        )
        summary = engine.run()

        assert summary is not None
        assert summary.cancelled is True
        assert summary.processed == 2
        assert summary.matched == 2
        assert events[-1].cancelled is True

    def test_pause_then_resume(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        pause = threading.Event()
        pause.set()
        events: list = []
        result: dict[str, object] = {}

        engine = make_engine(paths, analysis, events=events, pause=pause)

        def run() -> None:
            result["summary"] = engine.run()

        worker = threading.Thread(target=run)
        worker.start()
        deadline = time.time() + 5
        while not events and time.time() < deadline:
            time.sleep(0.01)

        assert events
        assert worker.is_alive()
        pause.clear()
        worker.join(5)
        assert not worker.is_alive()
        assert result["summary"] is not None
        assert isinstance(events[-1], Finished)
        assert events[-1].cancelled is False

    def test_cancel_while_paused(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        pause = threading.Event()
        pause.set()
        cancel = threading.Event()
        events: list = []
        result: dict[str, object] = {}

        engine = make_engine(
            paths,
            analysis,
            events=events,
            pause=pause,
            cancel=cancel,
        )

        def run() -> None:
            result["summary"] = engine.run()

        worker = threading.Thread(target=run)
        worker.start()
        deadline = time.time() + 5
        while not events and time.time() < deadline:
            time.sleep(0.01)

        cancel.set()
        worker.join(5)
        assert not worker.is_alive()
        assert result["summary"] is None
        assert not any(isinstance(event, SummaryEvent) for event in events)
        assert isinstance(events[-1], Finished)
        assert events[-1].cancelled is True


class TestHalts:
    def test_empty_source_folder(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        shutil.rmtree(paths.source_folder)
        Path(paths.source_folder).mkdir()
        events: list = []

        summary = make_engine(paths, analysis, events=events).run()

        assert summary is None
        halted = [event for event in events if isinstance(event, Halted)]
        assert len(halted) == 1
        assert "No supported images" in halted[0].message
        assert isinstance(events[-1], Finished)

    def test_insufficient_references(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        reference = Path(paths.reference_folder)
        (reference / "ref_similar.png").unlink()
        (reference / "ref_outlier.png").unlink()
        events: list = []

        summary = make_engine(paths, analysis, events=events).run()

        assert summary is None
        halted = [event for event in events if isinstance(event, Halted)]
        assert len(halted) == 1
        assert "Found only 1 reference face(s)" in halted[0].message

    def test_cache_open_failure_falls_back_to_no_cache(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        events: list = []

        summary = make_engine(
            paths,
            analysis,
            events=events,
            options=EngineOptions(cache_path=tmp_path),
        ).run()

        assert summary is not None
        assert summary.matched == 4
        assert isinstance(events[-1], Finished)


class TestModelLoading:
    def test_loads_antelope_with_rec_name(self) -> None:
        events: list = []
        engine = EngineV6(
            paths=PathSettings(),
            analysis=AnalysisSettings(model_name="antelopev2"),
            emit=events.append,
            cancel_event=threading.Event(),
        )

        with patch("insightface.app.FaceAnalysis") as face_analysis:
            app = MagicMock()
            face_analysis.return_value = app
            loaded = engine._load_analyser()

        assert loaded is app
        face_analysis.assert_called_once()
        assert face_analysis.call_args.kwargs["rec_name"] == "antelopev2"
        app.prepare.assert_called_once()

    def test_loads_buffalo_with_name(self) -> None:
        events: list = []
        engine = EngineV6(
            paths=PathSettings(),
            analysis=AnalysisSettings(model_name="buffalo_s"),
            emit=events.append,
            cancel_event=threading.Event(),
        )

        with patch("insightface.app.FaceAnalysis") as face_analysis:
            app = MagicMock()
            face_analysis.return_value = app
            loaded = engine._load_analyser()

        assert loaded is app
        assert face_analysis.call_args.kwargs["name"] == "buffalo_s"

    def test_model_load_failure_halts(self, tmp_path: Path) -> None:
        paths, analysis = make_engine_env(tmp_path)
        events: list = []
        engine = EngineV6(
            paths=paths,
            analysis=analysis,
            emit=events.append,
            cancel_event=threading.Event(),
        )

        with patch(
            "insightface.app.FaceAnalysis",
            side_effect=RuntimeError("CUDA out of memory"),
        ):
            summary = engine.run()

        assert summary is None
        halted = [event for event in events if isinstance(event, Halted)]
        assert len(halted) == 1
        assert "CUDA out of memory" in halted[0].message
        assert isinstance(events[-1], Finished)
