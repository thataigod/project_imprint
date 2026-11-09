"""Tests for the Qt bridge and engine worker."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

from PySide6.QtCore import QSettings, QStandardPaths, QUrl

from imprint.domain.results import ImageStatus, RunSummary
from imprint.domain.settings import AnalysisSettings, PathSettings
from imprint.engine.pipeline import EngineOptions
from imprint.events.pipeline import (
    Finished,
    Halted,
    ImageProcessed,
    Progress,
    RunStarted,
    Stage,
    StageChanged,
    SummaryEvent,
)
from imprint.ui.bridge import AppBridge, EngineWorker


class FakeEngine:
    """Engine stub that streams one match and a summary."""

    instances: list[FakeEngine] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        FakeEngine.instances.append(self)

    def run(self) -> RunSummary:
        emit = self.kwargs["emit"]
        source = Path(self.kwargs["paths"].source_folder) / "match.png"
        emit(
            ImageProcessed(
                source=source,
                status=ImageStatus.MATCH,
                score=0.1,
                det_score=0.99,
                subfolder="Score_0.100_to_0.200",
                destination=Path(self.kwargs["paths"].destination_folder) / "match.png",
            )
        )
        summary = RunSummary(
            total=1,
            processed=1,
            matched=1,
            skipped=0,
            errors=0,
            cancelled=False,
            matches=(),
        )
        emit(SummaryEvent(summary))
        emit(Finished(cancelled=False))
        return summary


class BlockingEngine:
    """Engine stub that blocks until cancellation."""

    started = threading.Event()
    cancelled = threading.Event()

    def __init__(self, **kwargs) -> None:
        self._cancel = kwargs["cancel_event"]

    def run(self) -> None:
        BlockingEngine.started.set()
        while not self._cancel.is_set():
            time.sleep(0.005)
        BlockingEngine.cancelled.set()
        return None


def configure_valid_folders(bridge: AppBridge, tmp_path: Path) -> None:
    for folder in ("reference", "source", "destination"):
        (tmp_path / folder).mkdir(exist_ok=True)
    bridge.referenceFolder = str(tmp_path / "reference")
    bridge.sourceFolder = str(tmp_path / "source")
    bridge.destinationFolder = str(tmp_path / "destination")


def test_default_user_paths(tmp_path: Path, qapp, monkeypatch) -> None:
    def fake_location(location: QStandardPaths.StandardLocation) -> str:
        if location == QStandardPaths.StandardLocation.AppConfigLocation:
            return str(tmp_path / "config")
        return str(tmp_path / "data")

    monkeypatch.setattr(
        "imprint.ui.bridge.QStandardPaths.writableLocation",
        fake_location,
    )
    settings = QSettings(str(tmp_path / "ui.ini"), QSettings.Format.IniFormat)
    loaded = AppBridge(qsettings=settings)
    try:
        assert (tmp_path / "config" / "config.ini").exists()
        assert (tmp_path / "data" / "logs" / "imprint.log").exists()
    finally:
        loaded.shutdown()


class TestFoldersAndSettings:
    def test_folder_setters_and_urls(self, bridge: AppBridge, tmp_path: Path) -> None:
        reference = tmp_path / "reference"
        source = tmp_path / "source"
        destination = tmp_path / "destination"
        for folder in (reference, source, destination):
            folder.mkdir()

        bridge.referenceFolder = str(reference)
        bridge.referenceFolder = str(reference)
        bridge.sourceFolder = str(source)
        bridge.sourceFolder = str(source)
        bridge.destinationFolder = str(destination)
        bridge.destinationFolder = str(destination)
        assert bridge.referenceFolder == str(reference)
        assert bridge.sourceFolder == str(source)
        assert bridge.destinationFolder == str(destination)

        new_reference = tmp_path / "new_reference"
        bridge.setFolderFromUrl("reference", QUrl.fromLocalFile(str(new_reference)))
        assert Path(bridge.referenceFolder) == new_reference

        bridge.setFolderFromUrl("source", QUrl.fromLocalFile(str(source)))
        bridge.setFolderFromUrl("destination", QUrl.fromLocalFile(str(destination)))
        bridge.setFolderFromUrl("source", QUrl())
        bridge.setFolderFromUrl("unknown", QUrl.fromLocalFile(str(source)))
        assert Path(bridge.referenceFolder) == new_reference
        assert Path(bridge.sourceFolder) == source
        assert Path(bridge.destinationFolder) == destination

    def test_setting_properties_and_clamping(self, bridge: AppBridge) -> None:
        bridge.distanceThreshold = 0.0
        assert bridge.distanceThreshold == 0.01
        bridge.distanceThreshold = 0.42
        bridge.distanceThreshold = 0.42
        assert bridge.distanceThreshold == 0.42

        bridge.confidenceThreshold = -1.0
        assert bridge.confidenceThreshold == 0.0
        bridge.confidenceThreshold = 2.0
        assert bridge.confidenceThreshold == 1.0
        bridge.confidenceThreshold = 0.9
        bridge.confidenceThreshold = 0.9
        assert bridge.confidenceThreshold == 0.9

        bridge.batchSize = 0
        assert bridge.batchSize == 1
        bridge.batchSize = 12
        bridge.batchSize = 12
        assert bridge.batchSize == 12

        bridge.numberOfSubfolders = 0
        assert bridge.numberOfSubfolders == 1
        bridge.numberOfSubfolders = 8
        bridge.numberOfSubfolders = 8
        assert bridge.numberOfSubfolders == 8

        bridge.cacheEnabled = False
        bridge.cacheEnabled = False
        assert bridge.cacheEnabled is False
        bridge.cacheEnabled = True
        assert bridge.cacheEnabled is True

    def test_model_selection_and_reset(self, bridge: AppBridge) -> None:
        bridge.selectModel(1)
        assert bridge.modelIndex == 1
        assert bridge.modelDisplayNames[1] == "Buffalo L (Balanced)"
        assert bridge.distanceThreshold == 0.6
        assert bridge.batchSize == 16

        bridge.selectModel(99)
        bridge.selectModel(-1)
        assert bridge.modelIndex == 1

        bridge.distanceThreshold = 0.2
        bridge.resetRecommended()
        assert bridge.distanceThreshold == 0.6

        bridge._set_running(True)
        bridge.selectModel(0)
        assert bridge.modelIndex == 1
        bridge._set_running(False)

    def test_result_filter_property(self, bridge: AppBridge) -> None:
        bridge.resultFilter = "match"
        bridge.resultFilter = "match"
        assert bridge.resultFilter == "match"
        bridge.resultFilter = "all"
        assert bridge.resultFilter == "all"

    def test_loads_existing_v5_config(self, tmp_path: Path, qapp) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[Paths]\n"
            "reference_folder = C:/ref\n"
            "source_folder = C:/src\n"
            "destination_folder = C:/dst\n"
            "[Settings]\n"
            "model_name = buffalo_l\n"
            "distance_threshold = 0.33\n"
            "confidence_threshold = 0.91\n"
            "batch_size = 7\n"
            "number_of_subfolders = 4\n",
            encoding="utf-8",
        )
        settings = QSettings(str(tmp_path / "ui.ini"), QSettings.Format.IniFormat)
        loaded = AppBridge(
            config_path=config_path,
            log_dir=tmp_path,
            qsettings=settings,
        )
        try:
            assert loaded.referenceFolder == "C:/ref"
            assert loaded.sourceFolder == "C:/src"
            assert loaded.destinationFolder == "C:/dst"
            assert loaded.modelIndex == 1
            assert loaded.distanceThreshold == 0.33
            assert loaded.confidenceThreshold == 0.91
            assert loaded.batchSize == 7
            assert loaded.numberOfSubfolders == 4
            assert loaded.cacheEnabled is True
        finally:
            loaded.shutdown()

    def test_geometry_and_version(self, bridge: AppBridge, tmp_path: Path) -> None:
        assert bridge.version
        assert bridge.windowWidth > 0
        assert bridge.windowHeight > 0
        bridge.saveWindowGeometry(1000, 700, 20, 30)
        assert bridge._qsettings.value("window/width") == 1000
        assert bridge._qsettings.value("window/height") == 700
        assert bridge._qsettings.value("window/x") == 20
        assert bridge._qsettings.value("window/y") == 30


class TestAnalysisControl:
    def test_start_requires_valid_folders(self, bridge: AppBridge) -> None:
        errors: list[tuple[str, str]] = []
        bridge.errorOccurred.connect(lambda title, message: errors.append((title, message)))

        bridge.startAnalysis()

        assert bridge.running is False
        assert bridge.statusText == "Validation failed."
        assert errors and errors[0][0] == "Validation Error"
        assert "Reference folder is required" in errors[0][1]

    def test_start_saves_config_and_runs_fake_engine(
        self, bridge: AppBridge, tmp_path: Path, qtbot
    ) -> None:
        configure_valid_folders(bridge, tmp_path)
        FakeEngine.instances.clear()
        bridge._engine_factory = lambda **kwargs: FakeEngine(**kwargs)
        bridge.cacheEnabled = False

        bridge.startAnalysis()
        qtbot.waitUntil(lambda: not bridge.running, timeout=4000)
        qtbot.waitUntil(lambda: bridge.resultsProxy.rowCount() == 1, timeout=4000)

        assert FakeEngine.instances
        assert bridge.matchCount == 1
        assert bridge.processedCount == 1
        assert bridge.totalCount == 1
        assert "Analysis Complete!" in bridge.summaryText
        assert bridge.statusText == "Analysis complete."
        assert (tmp_path / "config.ini").exists()

    def test_start_while_running_is_ignored(self, bridge: AppBridge) -> None:
        bridge._set_running(True)
        bridge.startAnalysis()
        assert bridge.running is True
        bridge._set_running(False)

    def test_config_save_failure_reports_error(
        self, bridge: AppBridge, tmp_path: Path, monkeypatch
    ) -> None:
        configure_valid_folders(bridge, tmp_path)
        errors: list[tuple[str, str]] = []
        bridge.errorOccurred.connect(lambda title, message: errors.append((title, message)))
        monkeypatch.setattr(
            bridge._config_manager,
            "save",
            MagicMock(side_effect=OSError("disk full")),
        )

        bridge.startAnalysis()

        assert bridge.running is False
        assert errors
        assert errors[0][0] == "Configuration Error"

    def test_pause_resume_cancel(self, bridge: AppBridge) -> None:
        bridge.cancelAnalysis()
        bridge.pauseAnalysis()
        bridge.resumeAnalysis()
        bridge.togglePause()
        assert bridge.paused is False

        bridge._set_running(True)
        bridge.pauseAnalysis()
        bridge.pauseAnalysis()
        assert bridge.paused is True
        assert bridge._pause_event.is_set()

        bridge.resumeAnalysis()
        bridge.resumeAnalysis()
        assert bridge.paused is False
        assert not bridge._pause_event.is_set()

        bridge.togglePause()
        assert bridge.paused is True
        bridge.togglePause()
        assert bridge.paused is False

        bridge.cancelAnalysis()
        assert bridge._cancel_event.is_set()
        bridge._set_running(False)
        assert bridge.running is False

        bridge._set_running(True)
        bridge.pauseAnalysis()
        bridge._set_running(False)
        assert bridge.paused is False

    def test_shutdown_stops_running_engine(self, bridge: AppBridge, tmp_path: Path, qtbot) -> None:
        configure_valid_folders(bridge, tmp_path)
        BlockingEngine.started.clear()
        BlockingEngine.cancelled.clear()
        bridge._engine_factory = lambda **kwargs: BlockingEngine(**kwargs)

        bridge.startAnalysis()
        qtbot.waitUntil(BlockingEngine.started.is_set, timeout=4000)
        bridge.shutdown()
        assert BlockingEngine.cancelled.is_set()


class TestEventsAndLogs:
    def test_pipeline_event_updates_state(self, bridge: AppBridge, tmp_path: Path) -> None:
        errors: list[tuple[str, str]] = []
        bridge.errorOccurred.connect(lambda title, message: errors.append((title, message)))

        bridge._on_pipeline_event(
            RunStarted(
                model_name="buffalo_s",
                reference_folder=tmp_path,
                source_folder=tmp_path,
                destination_folder=tmp_path,
            )
        )
        assert "buffalo_s" in bridge.statusText

        bridge._on_pipeline_event(StageChanged(Stage.PROCESSING, "Processing images..."))
        assert bridge.statusText == "Processing images..."

        bridge._on_pipeline_event(Progress(5, 10, "Halfway"))
        assert bridge.progressValue == 0.5
        assert bridge.progressText == "5 / 10"
        assert bridge.statusText == "Halfway"

        source = tmp_path / "match.png"
        bridge._on_pipeline_event(
            ImageProcessed(
                source=source,
                status=ImageStatus.MATCH,
                score=0.1,
                det_score=0.99,
                subfolder="Score_0.100_to_0.200",
                destination=tmp_path / "match.png",
            )
        )
        bridge._on_pipeline_event(ImageProcessed(source=source, status=ImageStatus.SKIP))
        bridge._on_pipeline_event(
            ImageProcessed(source=source, status=ImageStatus.ERROR, error="bad")
        )
        assert bridge.matchCount == 1
        assert bridge.skipCount == 1
        assert bridge.errorCount == 1
        assert bridge.processedCount == 3
        assert bridge.resultsProxy.rowCount() == 3

        summary = RunSummary(3, 3, 1, 1, 1, False)
        bridge._on_pipeline_event(SummaryEvent(summary))
        assert "Analysis Complete!" in bridge.summaryText
        assert bridge.statusText == "Analysis complete."
        assert bridge.progressValue == 1.0

        bridge._on_pipeline_event(Halted("cannot continue"))
        assert errors[-1][0] == "Analysis Halted"
        assert bridge.statusText == "Analysis halted."

        bridge._set_running(True)
        bridge._on_pipeline_event(Finished(cancelled=False))
        assert bridge.running is False

    def test_cancelled_summary_and_finished_callback(self, bridge: AppBridge) -> None:
        summary = RunSummary(10, 4, 2, 1, 1, True)
        bridge._apply_summary(summary)
        assert bridge.statusText == "Analysis cancelled."
        assert bridge.progressValue == 0.4
        assert "Analysis Cancelled." in bridge.summaryText

        bridge._set_running(True)
        bridge._on_engine_finished(summary)
        assert bridge.running is False
        bridge._on_engine_finished(None)
        assert bridge._on_thread_finished() is None

    def test_progress_with_zero_total(self, bridge: AppBridge) -> None:
        bridge._set_progress(0, 0, "")
        assert bridge.progressValue == 0.0

    def test_log_polling(self, bridge: AppBridge) -> None:
        bridge._poll_logs()
        bridge.clearLog()
        bridge._log_queue.put("INFO: hello")
        bridge._log_queue.put("no level here")
        bridge._poll_logs()

        log = bridge.logModel
        assert log.rowCount() == 2
        assert log.data(log.index(0, 0), log.LevelRole) == "INFO"
        assert log.data(log.index(0, 0), log.MessageRole) == "hello"
        assert log.data(log.index(1, 0), log.LevelRole) == "INFO"
        assert log.data(log.index(1, 0), log.MessageRole) == "no level here"

        bridge.clearLog()
        assert log.rowCount() == 0
        bridge._poll_logs()

    def test_open_destination(self, bridge: AppBridge, tmp_path: Path, monkeypatch) -> None:
        errors: list[tuple[str, str]] = []
        bridge.errorOccurred.connect(lambda title, message: errors.append((title, message)))

        bridge.destinationFolder = str(tmp_path / "missing_destination")
        bridge.openDestination()
        assert errors and errors[-1][0] == "Destination Folder"

        destination = tmp_path / "destination"
        destination.mkdir()
        bridge.destinationFolder = str(destination)
        monkeypatch.setattr(
            "imprint.ui.bridge.QDesktopServices.openUrl",
            MagicMock(return_value=True),
        )
        bridge.openDestination()
        assert len(errors) == 1

        monkeypatch.setattr(
            "imprint.ui.bridge.QDesktopServices.openUrl",
            MagicMock(return_value=False),
        )
        bridge.openDestination()
        assert len(errors) == 2


class TestEngineWorker:
    def test_worker_reports_summary(self, tmp_path: Path) -> None:
        events: list[object] = []
        finished: list[object] = []
        expected = RunSummary(0, 0, 0, 0, 0, False)

        class SuccessfulEngine:
            def run(self) -> RunSummary:
                return expected

        worker = EngineWorker(
            paths=PathSettings(
                reference_folder=str(tmp_path),
                source_folder=str(tmp_path),
                destination_folder=str(tmp_path),
            ),
            analysis=AnalysisSettings(),
            cancel_event=threading.Event(),
            pause_event=threading.Event(),
            options=EngineOptions(),
            engine_factory=lambda **kwargs: SuccessfulEngine(),
        )
        worker.pipelineEvent.connect(events.append)
        worker.finished.connect(finished.append)

        worker.run()

        assert finished == [expected]
        assert events == []

    def test_worker_reports_exception(self, tmp_path: Path) -> None:
        events: list[object] = []
        finished: list[object] = []

        worker = EngineWorker(
            paths=PathSettings(
                reference_folder=str(tmp_path),
                source_folder=str(tmp_path),
                destination_folder=str(tmp_path),
            ),
            analysis=AnalysisSettings(),
            cancel_event=threading.Event(),
            pause_event=threading.Event(),
            options=EngineOptions(),
            engine_factory=MagicMock(side_effect=RuntimeError("boom")),
        )
        worker.pipelineEvent.connect(events.append)
        worker.finished.connect(finished.append)

        worker.run()

        assert finished == [None]
        assert any(isinstance(event, Halted) for event in events)
